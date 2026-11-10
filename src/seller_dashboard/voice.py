
import base64
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from sarvamai import AsyncSarvamAI, SarvamAI, RealtimeAudioInput

from seller_dashboard.bot import graph

load_dotenv()

API_KEY = os.getenv("SARVAM_API_KEY")

SAMPLE_RATE = 16000


class VoiceAssistant:

    def __init__(self):
        if not API_KEY:
            raise ValueError("SARVAM_API_KEY not found in .env")

        self.stt_client = AsyncSarvamAI(
            api_subscription_key=API_KEY
        )

        self.tts_client = SarvamAI(
            api_subscription_key=API_KEY
        )

    def generate_response(self, transcript: str, session_id: str) -> str:
        """Send transcript to LangGraph and return its response."""

        result = graph.invoke(
            {"messages": [HumanMessage(content=transcript)]},
            config={
                "configurable": {
                    "thread_id": session_id
                }
            },
        )

        return result["messages"][-1].content

    def generate_audio(self, text: str) -> bytes:
        """Convert assistant response into audio bytes."""

        audio = self.tts_client.text_to_speech.convert(
            text=text,
            model="bulbul:v4-flash",
            language_code="hi-IN",
            speaker="ritu_hi_sales",
        )

        audio_bytes = base64.b64decode(
            "".join(audio.audios)
        )

        return audio_bytes

    def connect_stt(self):
        """Create a Sarvam realtime STT connection."""

        return self.stt_client.speech_to_text_realtime_streaming.connect(
            model="saaras:v4",
            language_code="hi-IN",
            mode="transcribe",
            stream_type="fast",
            endpointing="vad",
            encoding="linear16",
            sample_rate=str(SAMPLE_RATE),
            silence_duration_ms="800",
        )
