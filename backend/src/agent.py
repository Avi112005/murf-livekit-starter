import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

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

LANGUAGE
Mirror the caller's language and level of formality. If they use Hindi mixed with
English, reply naturally in the same Hinglish register. If they speak Hindi, reply
primarily in Hindi and do not default to English. If they switch to another
language, respond in that language when you can; otherwise explain briefly and ask
whether English or Hindi is preferred. Keep sentences short and ask one question
at a time. Use feminine Hindi grammar for yourself because the voice is female:
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

FIRST_TURN_GREETING = """
नमस्ते। मैं Aapda Sahaayak हूँ, आपकी Disaster Response voice assistant। Flood,
drought या relief support में मैं आपकी मदद कर सकती हूँ। आपको किस emergency का
सामना है?
"""


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

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
        # Recommended Indian voices: Anisha, Samar, and Pooja. Day 1 uses Anisha.
        tts=murf.TTS(
                voice="Anisha",
                locale="hi-IN",
                style="Conversation",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
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
    await session.start(
        agent=Assistant(),
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

    # Join the room and connect to the user
    await ctx.connect()

    # Establish the agent's role and limits before the caller speaks.
    await session.generate_reply(instructions=FIRST_TURN_GREETING)


if __name__ == "__main__":
    cli.run_app(server)
