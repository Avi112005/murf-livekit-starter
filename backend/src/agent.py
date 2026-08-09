import asyncio
import logging
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.agents.llm import ChatContext, ChatMessage
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero

logger = logging.getLogger("agent")

load_dotenv(".env.local")

MEMORY_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "aapda_memory.sqlite3"


def _open_memory_db() -> sqlite3.Connection:
    MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(MEMORY_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS callers (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            language_preference TEXT,
            location TEXT,
            household_size INTEGER,
            mobility_needs TEXT,
            last_checkin TEXT NOT NULL,
            consented INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    connection.commit()
    return connection


def _lookup_caller(user_id: str) -> str:
    with closing(_open_memory_db()) as connection:
        row = connection.execute(
            """
            SELECT name, language_preference, location, household_size,
                   mobility_needs, last_checkin
            FROM callers
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        return "No saved caller record was found."

    return (
        "Saved caller record found. "
        f"Name: {row['name']}. "
        f"Language preference: {row['language_preference'] or 'not provided'}. "
        f"Location: {row['location'] or 'not provided'}. "
        f"Household size: {row['household_size'] or 'not provided'}. "
        f"Mobility needs: {row['mobility_needs'] or 'not provided'}. "
        f"Last check-in: {row['last_checkin']}."
    )


def _save_caller(
    user_id: str,
    name: str,
    language_preference: str | None,
    location: str | None,
    household_size: int | None,
    mobility_needs: str | None,
    consent_given: bool,
) -> str:
    if not consent_given:
        return "Consent was not given. No caller information was saved."

    clean_name = name.strip()
    if not clean_name:
        return "A name is required to save caller memory. Nothing was saved."

    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with closing(_open_memory_db()) as connection:
        connection.execute(
            """
            INSERT INTO callers (
                user_id, name, language_preference, location, household_size,
                mobility_needs, last_checkin, consented
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                name = excluded.name,
                language_preference = COALESCE(
                    excluded.language_preference, callers.language_preference
                ),
                location = COALESCE(excluded.location, callers.location),
                household_size = COALESCE(excluded.household_size, callers.household_size),
                mobility_needs = COALESCE(excluded.mobility_needs, callers.mobility_needs),
                last_checkin = excluded.last_checkin,
                consented = 1
            """,
            (
                user_id,
                clean_name,
                language_preference,
                location,
                household_size,
                mobility_needs,
                timestamp,
            ),
        )
        connection.commit()

    return "Caller memory was saved with consent."

# Day 2 persona and operating boundaries for the Disaster Response track.
SYSTEM_PROMPT = """
IDENTITY
You are a calm Disaster Response voice assistant for people in India. You provide
general information and help organize a caller's situation for a safer handoff to
local emergency services or relief workers. You are not a government authority,
first responder, weather service, or emergency dispatcher.

OBJECTIVES
1. Identify the incident type, approximate location, urgency, and immediate need.
2. Offer brief, general preparedness or safety information when it is appropriate.
3. Prepare a concise handoff summary with the people affected, accessibility needs,
   and requested support. Never claim that the summary was sent or that help is on
   the way.

KNOWLEDGE
You know general disaster-preparedness concepts for floods, droughts, evacuation
planning, relief requests, and welfare check-ins. You do not have verified live
weather, alert, map, shelter, road, or rescue data unless a future tool explicitly
provides it. Say when information is general or unverified.

MEMORY
The application loads the caller record before the first greeting. If a record is
found, welcome the caller back by name and briefly mention a relevant saved fact,
then ask whether it is still accurate. Use lookup_caller_memory whenever you need
to verify or refresh memory during the conversation. If no record is found, ask for
the caller's name when it is useful.

MANDATORY MEMORY CONSENT WORKFLOW
When the caller gives their name or any memory fact such as location, household
size, or mobility needs, immediately acknowledge the facts and ask: "Would you like
me to remember your name and these details for future check-ins?" Use the caller's
current language and native script. Stop and wait for the caller's next turn. Do not
call save_caller_memory in the same turn as receiving the facts. Call
save_caller_memory only after a clear yes in a later user turn, with
consent_given=true. If the caller says no or is unclear, do not save anything and
acknowledge that. Save only location, household size, mobility needs, language
preference, and the last check-in. Never save OTPs, PINs, passwords, Aadhaar
numbers, medical notes, or other sensitive data.

LANGUAGE
Always follow the language of the latest user turn; it overrides saved language
preferences and the voice locale. If the latest turn is primarily English, reply
entirely in English and do not translate it to Hindi. If the caller uses Hindi mixed
with English, reply naturally in the same Hinglish register. If they speak Hindi,
reply primarily in Hindi. If they switch to another language, respond in that
language when you can; otherwise explain briefly and ask whether English or Hindi
is preferred. Always write each language in its native script: Hindi must use
Devanagari (नमस्ते), never romanized Hindi (never "namaste"); apply the same rule
to every non-English language. Keep sentences short and ask one question at a time.
Use feminine Hindi grammar for yourself because the voice is female:
say "कर सकती हूँ", "बता सकती हूँ", and "समझ सकती हूँ"; never use masculine forms
such as "कर सकता हूँ" when referring to yourself. Address the caller respectfully
with neutral plural forms such as "आप बता सकते हैं" and "आप साझा कर सकते हैं";
do not address the caller as "कर सकती है".

GUARDRAILS
- Never issue an official alert, evacuation order, shelter assignment, or all-clear.
- Never claim to know a current disaster status without a verified source and date.
- Never claim to be an authority, contact emergency services, dispatch rescue, send
  relief, or confirm that help has arrived.
- Never request OTPs, PINs, passwords, Aadhaar numbers, or unnecessary sensitive data.
- Refuse unrelated requests and requests for dangerous actions. Offer to help with
  incident details, safety planning, or a relief handoff instead.
- For immediate danger, say: "I cannot verify live alerts or dispatch help. Please
  call 112 or your local emergency service now and follow instructions from local
  authorities. I can help you organize the details to share with them."
- If asked whether it is safe to evacuate or return, say that only local authorities
  can issue that instruction and do not provide an all-clear.

STYLE
Be calm, respectful, and direct. Do not create panic or false reassurance. Confirm
important details by repeating them briefly. Handle silence with one gentle prompt.
Use plain speech without complex formatting, emojis, or symbols.
"""

NEW_CALL_GREETING = """
Say: "नमस्ते। मैं Aapda Sahaayak हूँ, आपकी Disaster Response voice assistant। Flood,
drought या relief support में मैं आपकी मदद कर सकती हूँ। आपको किस emergency का
सामना है?"
"""


def _first_turn_instructions(memory: str) -> str:
    if memory.startswith("Saved caller record found."):
        return (
            "A saved caller record was loaded before this greeting. Welcome the caller "
            "back by name, mention one relevant saved fact, and ask whether it is still "
            f"accurate. Do not mention the database. Saved record: {memory}"
        )
    return NEW_CALL_GREETING


class Assistant(Agent):
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        super().__init__(instructions=SYSTEM_PROMPT)

    async def on_user_turn_completed(
        self,
        turn_ctx: ChatContext,
        new_message: ChatMessage,
    ) -> None:
        """Make the latest transcript language explicit for the next LLM turn."""
        text = new_message.text_content or ""
        lowered = text.lower()
        has_devanagari = any("\u0900" <= character <= "\u097f" for character in text)
        hinglish_markers = (
            " mere ",
            " mein ",
            " hai ",
            " mujhe ",
            " aap ",
            " kya ",
            " paani ",
            " baadh ",
        )

        if has_devanagari:
            instruction = (
                "The latest user turn is Hindi. Reply in Hindi using Devanagari script "
                "and feminine grammar for yourself."
            )
        elif any(marker in f" {lowered} " for marker in hinglish_markers):
            instruction = (
                "The latest user turn is Hinglish. Reply in the same Hinglish register, "
                "using Devanagari for Hindi words and English script for English words."
            )
        else:
            instruction = "The latest user turn is English. Reply entirely in English."

        turn_ctx.add_message(role="system", content=instruction)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."

    @function_tool()
    async def lookup_caller_memory(self, context: RunContext) -> str:
        """Look up saved memory for the current caller.

        Use this before greeting the caller and whenever they ask what was
        remembered from an earlier Disaster Response check-in.
        """
        return await asyncio.to_thread(_lookup_caller, self.user_id)

    @function_tool()
    async def save_caller_memory(
        self,
        context: RunContext,
        name: str,
        consent_given: bool,
        language_preference: str | None = None,
        location: str | None = None,
        household_size: int | None = None,
        mobility_needs: str | None = None,
    ) -> str:
        """Save consented facts for a future Disaster Response check-in.

        Call this only after the caller explicitly says yes in a later turn after
        the consent question. Never pass sensitive identifiers or written-out
        medical notes.

        Args:
            name: The caller's name.
            consent_given: True only after explicit caller permission to remember.
            language_preference: The caller's preferred language or register.
            location: The caller's general location, not a precise address.
            household_size: The number of people in the caller's household.
            mobility_needs: A short description of accessibility or mobility needs.
        """
        return await asyncio.to_thread(
            _save_caller,
            self.user_id,
            name,
            language_preference,
            location,
            household_size,
            mobility_needs,
            consent_given,
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
                model="gemini-3.5-flash-lite",
            ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        # Recommended Indian voices: Anisha, Samar, and Pooja. Day 4 uses Anisha.
        tts=murf.TTS(
                voice="Anisha",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD-only turn detection avoids a second local inference model competing
        # with Silero, while Deepgram still handles multilingual transcription.
        turn_detection="vad",
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    assistant = Assistant(ctx.room.name)
    await session.start(
        agent=assistant,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room after the agent session is initialized, then attach memory to
    # the stable browser identity before the first spoken reply.
    await ctx.connect()
    room_prefix = "voice_assistant_room_"
    room_identity = ctx.room.name.removeprefix(room_prefix)
    assistant.user_id = room_identity.split("--", 1)[0]
    ctx.log_context_fields["user_id"] = assistant.user_id
    caller_memory = await asyncio.to_thread(_lookup_caller, assistant.user_id)

    # Establish the agent's role and limits before the caller speaks.
    await session.generate_reply(instructions=_first_turn_instructions(caller_memory))


if __name__ == "__main__":
    cli.run_app(server)
