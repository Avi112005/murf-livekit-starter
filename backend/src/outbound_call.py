"""Place a Day 6 Disaster Response welfare-check call through LiveKit SIP.

The LiveKit SIP outbound trunk must be connected to a telephony provider such as
Twilio before this script can place a real call.
"""

import argparse
import asyncio
import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from livekit import api

from agent import _record_call_outcome, _record_call_start

load_dotenv(".env.local")

CALL_LOCK = Path(__file__).resolve().parents[1] / "data" / "outbound_call.lock"


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _acquire_call_lock(destination: str) -> None:
    CALL_LOCK.parent.mkdir(parents=True, exist_ok=True)
    if CALL_LOCK.exists():
        age = time.time() - CALL_LOCK.stat().st_mtime
        if age < 120:
            raise RuntimeError("An outbound call is already being placed. Wait before retrying.")
        CALL_LOCK.unlink()
    CALL_LOCK.write_text(destination, encoding="utf-8")


async def place_call(destination: str) -> None:
    _acquire_call_lock(destination)
    try:
        await _place_call(destination)
    finally:
        CALL_LOCK.unlink(missing_ok=True)


async def _place_call(destination: str) -> None:
    livekit_url = _required("LIVEKIT_URL")
    api_key = _required("LIVEKIT_API_KEY")
    api_secret = _required("LIVEKIT_API_SECRET")
    trunk_id = _required("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")
    agent_name = os.getenv("LIVEKIT_AGENT_NAME", "my-agent")

    api_url = livekit_url.replace("wss://", "https://").replace("ws://", "http://")
    call_id = uuid.uuid4().hex[:12]
    room_name = f"aapda-outbound-{call_id}"
    participant_identity = f"outbound-sip-{call_id}"
    _record_call_start(call_id, participant_identity, "sip")

    async with api.LiveKitAPI(api_url, api_key, api_secret) as livekit_api:
        # Dispatch the agent FIRST so it starts warming up models while the
        # phone is still ringing. By the time the call is answered, the agent
        # is ready to greet immediately.
        await livekit_api.agent_dispatch.create_dispatch(
            api.CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
            )
        )
        print(f"Agent dispatched: {agent_name} -> {room_name}")
        print("Waiting 8 seconds for agent to warm up before calling...")

        await asyncio.sleep(8)

        request = api.CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=destination,
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name="Aapda Sahaayak welfare check",
            wait_until_answered=True,
            play_dialtone=True,
        )

        try:
            participant = await livekit_api.sip.create_sip_participant(request)
        except Exception as error:
            message = str(error).lower()
            if "480" in message or "temporarily unavailable" in message:
                category = "unavailable or declined"
            elif "408" in message:
                category = "no response"
            elif "486" in message or "busy" in message or "603" in message or "decline" in message:
                category = "user declined"
            else:
                category = "API error"
            _record_call_outcome(call_id, "failed", str(error), category)
            print(f"Outbound call failed ({category}): {error}")
            return

    print(f"Outbound call answered: {participant.sip_call_id}")
    print(f"Room: {room_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Place an Aapda Sahaayak welfare check call.")
    parser.add_argument(
        "phone_number",
        nargs="?",
        default=os.getenv("OUTBOUND_CALL_TO"),
        help="Destination number in E.164 format, for example +919876543210",
    )
    args = parser.parse_args()
    if not args.phone_number:
        parser.error("Provide a phone number or set OUTBOUND_CALL_TO")
    asyncio.run(place_call(args.phone_number))


if __name__ == "__main__":
    main()
