import asyncio
import logging
import os
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import aiohttp
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
    utils,
)
from livekit.agents.llm import ChatContext, ChatMessage, ToolError
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


def _create_escalation_record(
    user_id: str,
    name: str,
    situation: str,
    checked: str,
    urgency: str,
    language: str,
    follow_up: str,
    consent_given: bool,
) -> tuple[str, str]:
    if not consent_given:
        return "", "Permission was not given. No human-help request was created."

    reference_id = f"AID-{uuid.uuid4().hex[:8].upper()}"
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    slack_summary = (
        f"*Human-help request {reference_id}*\n"
        f"*Who:* {name}\n*Situation:* {situation}\n*Already checked:* {checked}\n"
        f"*Urgency:* {urgency}\n*Language/follow-up:* {language}; {follow_up}"
    )
    with closing(_open_memory_db()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS escalations (
                reference_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                situation TEXT NOT NULL,
                checked TEXT NOT NULL,
                urgency TEXT NOT NULL,
                language TEXT NOT NULL,
                follow_up TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO escalations (
                reference_id, user_id, name, situation, checked, urgency,
                language, follow_up, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                reference_id,
                user_id,
                name.strip() or "Caller",
                situation.strip(),
                checked.strip(),
                urgency.strip(),
                language.strip(),
                follow_up.strip(),
                created_at,
            ),
        )
        connection.commit()

    return (
        f"Human-help request {reference_id} was created. It is open for review. "
        "The team will use the summary to decide the next follow-up; no immediate "
        "response time is guaranteed.",
        slack_summary,
    )


WEATHER_CODE_LABELS = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def _format_observation_time(value: str, timezone_name: str) -> str:
    observed_at = datetime.fromisoformat(value)
    date_text = observed_at.strftime("%d %B %Y").lstrip("0")
    time_text = observed_at.strftime("%I:%M %p").lstrip("0")
    readable_timezone = (
        "India Standard Time" if timezone_name == "Asia/Kolkata" else timezone_name.replace("_", " ")
    )
    return f"{date_text} at {time_text} {readable_timezone}"


async def _fetch_local_weather(district: str) -> str:
    try:
        async with asyncio.timeout(8):
            http_session = utils.http_context.http_session()
            async with http_session.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={
                    "name": district,
                    "count": 1,
                    "language": "en",
                    "format": "json",
                },
            ) as geocoding_response:
                if geocoding_response.status != 200:
                    raise ToolError("The live weather source is unavailable right now.")
                geocoding_data = await geocoding_response.json()

            results = geocoding_data.get("results") or []
            if not results:
                raise ToolError(
                    f"I could not find a location matching {district}. Please provide a district or city."
                )

            location = results[0]
            async with http_session.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "current": "temperature_2m,precipitation,rain,weather_code,wind_speed_10m",
                    "hourly": "precipitation_probability",
                    "forecast_days": 1,
                    "timezone": "auto",
                },
            ) as weather_response:
                if weather_response.status != 200:
                    raise ToolError("The live weather source is unavailable right now.")
                weather_data = await weather_response.json()

        current = weather_data["current"]
        hourly = weather_data.get("hourly", {})
        current_time = current["time"]
        timezone_name = weather_data.get("timezone", "local time")
        readable_observation_time = _format_observation_time(current_time, timezone_name)
        try:
            local_timezone = ZoneInfo(timezone_name)
            observed_at = datetime.fromisoformat(current_time).replace(tzinfo=local_timezone)
            retrieved_at = datetime.now(local_timezone)
            age_minutes = max(0, round((retrieved_at - observed_at).total_seconds() / 60))
            readable_retrieval_time = _format_observation_time(
                retrieved_at.isoformat(timespec="minutes"), timezone_name
            )
        except (ValueError, TypeError, KeyError):
            age_minutes = None
            readable_retrieval_time = "the current time"
        current_hour = current_time[:13]
        hourly_index = next(
            (
                index
                for index, hourly_time in enumerate(hourly.get("time", []))
                if hourly_time.startswith(current_hour)
            ),
            0,
        )
        rain_probability = hourly["precipitation_probability"][hourly_index]
        condition = WEATHER_CODE_LABELS.get(current["weather_code"], "unknown conditions")
        place = ", ".join(
            value for value in (location.get("name"), location.get("admin1"), location.get("country")) if value
        )

        return (
            f"Latest available model update for {place}: {readable_observation_time}. "
            f"Retrieved at {readable_retrieval_time}"
            f"{f' and approximately {age_minutes} minutes old' if age_minutes is not None else ''}: "
            f"{condition}; "
            f"temperature {current['temperature_2m']} °C; precipitation "
            f"{current['precipitation']} mm; rain {current['rain']} mm; "
            f"wind {current['wind_speed_10m']} km/h; precipitation probability "
            f"for this hour {rain_probability}%. Source: Open-Meteo forecast API. "
            "This is model-based weather data, not an official disaster alert, "
            "evacuation order, or all-clear."
        )
    except ToolError:
        raise
    except Exception as error:
        logger.warning("Local weather lookup failed: %s", error)
        raise ToolError(
            "The live weather source is unavailable right now. I cannot provide current conditions."
        ) from error


async def _send_escalation_to_slack(summary: str) -> None:
    webhook_url = os.getenv("SLACK_ESCALATION_WEBHOOK_URL")
    if not webhook_url:
        return
    async with aiohttp.ClientSession() as session, session.post(
        webhook_url, json={"text": summary}, timeout=8
    ) as response:
            if response.status >= 300:
                raise RuntimeError(f"Slack returned HTTP {response.status}")

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

TOOLS
When the caller asks for current weather, rain, wind, or local conditions for a
named district or city, call lookup_local_weather_conditions. Always report the
observation time and Open-Meteo source returned by the tool. Read the observation
time naturally as a date, clock time, and local timezone; never read an ISO timestamp
or a timezone identifier character by character. This tool is not an official alert
service; never turn its result into an evacuation order or all-clear. If the tool
reports that data is unavailable, say so clearly and do not guess.

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

HUMAN HELP
Create a human-help request only when the caller is trapped or injured, or needs
urgent local help that you cannot provide. Before sharing anything, explain the
short summary you want to send: who needs help, what happened, what you checked,
urgency, language, and preferred follow-up. Ask for explicit yes or no permission.
Call create_escalation only after a clear yes in a later user turn. If permission is
denied, do not create a request. After success, read the reference ID and explain
that the request is open for human review without promising an immediate response.

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

OUTBOUND_GREETING_TEXT = (
    "Namaste, this is Aapda Sahaayak, an automated Disaster Response assistant "
    "calling for a scheduled household welfare check. If this is not a good time, "
    "say stop or hang up and I will end the call."
)


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

    @function_tool()
    async def lookup_local_weather_conditions(
        self,
        context: RunContext,
        district: str,
    ) -> str:
        """Fetch current weather conditions for a named Indian district or city.

        Call this when the caller asks about current rain, temperature, wind, or
        local weather conditions. Do not use it to issue official disaster alerts,
        evacuation orders, shelter instructions, or all-clears.

        Args:
            district: The district or city to look up, such as Surat or Ahmedabad.
        """
        return await _fetch_local_weather(district)

    @function_tool()
    async def create_escalation(
        self,
        context: RunContext,
        name: str,
        situation: str,
        checked: str,
        urgency: str,
        language: str,
        follow_up: str,
        consent_given: bool,
    ) -> str:
        """Create a concise human-help request for an urgent local situation.

        Use only when the caller is trapped or injured, or needs urgent local help
        the agent cannot provide. Ask for explicit permission in a previous user
        turn before calling this tool.

        Args:
            name: The person or household needing help.
            situation: What happened, without sensitive identifiers.
            checked: What the agent already checked or explained.
            urgency: Immediate, urgent, or non-urgent.
            language: The caller's language and preferred follow-up method.
            follow_up: How the caller prefers a human to follow up.
            consent_given: True only after explicit permission to share the summary.
        """
        if not consent_given:
            return "Permission was not given. No human-help request was created."

        result, summary = await asyncio.to_thread(
            _create_escalation_record,
            self.user_id,
            name,
            situation,
            checked,
            urgency,
            language,
            follow_up,
            consent_given,
        )
        try:
            await _send_escalation_to_slack(summary)
        except Exception as error:
            logger.exception("Slack escalation delivery failed: %s", error)
            return f"{result} However, Slack delivery failed, so tell the caller the request is saved locally with its reference ID."
        return f"{result} The summary was also sent to the human-help Slack channel."


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
    is_outbound_room = ctx.room.name.startswith("aapda-outbound-")

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
                sample_rate=16000 if is_outbound_room else 24000,
                tokenizer=tokenize.basic.SentenceTokenizer(
                    min_sentence_len=1 if is_outbound_room else 2
                ),
                text_pacing=not is_outbound_room,
                min_buffer_size=1 if is_outbound_room else 3,
                max_buffer_delay_in_ms=500 if is_outbound_room else 0,
            ),
        # VAD-only turn detection avoids a second local inference model competing
        # with Silero, while Deepgram still handles multilingual transcription.
        turn_detection="vad",
        vad=ctx.proc.userdata["vad"],
        min_endpointing_delay=0.25,
        max_endpointing_delay=1.0,
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=False,
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

    assistant = Assistant(ctx.room.name)

    # For outbound calls the SIP participant is already in the room waiting;
    # connect first so the signal does not time out during model warm-up.
    if is_outbound_room:
        await ctx.connect()

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

    # Join the room after the agent session is initialized for browser calls.
    if not is_outbound_room:
        await ctx.connect()
    is_sip_call = is_outbound_room
    room_prefix = "voice_assistant_room_"
    room_identity = ctx.room.name.removeprefix(room_prefix)
    assistant.user_id = room_identity.split("--", 1)[0]
    ctx.log_context_fields["user_id"] = assistant.user_id
    caller_memory = await asyncio.to_thread(_lookup_caller, assistant.user_id)

    # Establish the agent's role and limits before the caller speaks.
    if is_sip_call:
        # Wait for the SIP participant (phone callee) to join before greeting.
        try:
            await asyncio.wait_for(
                ctx.wait_for_participant(
                    kind=rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                ),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for SIP participant")
        await session.say(OUTBOUND_GREETING_TEXT)
    else:
        await session.generate_reply(instructions=_first_turn_instructions(caller_memory))


if __name__ == "__main__":
    cli.run_app(server)
