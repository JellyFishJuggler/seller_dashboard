import base64
import logging

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage
from sarvamai import AsyncSarvamAI, SarvamAI, RealtimeAudioInput

from seller_dashboard.bot import (
    SarvamLLMUnavailable,
    classify_text_language,
    detect_session_language,
    graph,
)
from seller_dashboard.sarvam_credentials import get_sarvam_api_key
from seller_dashboard.voice_diagnostics import (
    EmptyAssistantResponseError,
    EmptyTTSInputError,
    EmptyTranscriptError,
    clean_transcript,
    extract_request_id,
    has_nonempty_text,
    log_text_boundary,
)

load_dotenv()

SAMPLE_RATE = 16000

# One fixed TTS persona for every assistant utterance. Language detection is
# only used to choose the pronunciation language code below; it must never
# switch the speaker. `ritu_hi_sales` is Sarvam's Ritu (Hindi, sales) persona.
TTS_SPEAKER = "ritu_hi_sales"
TTS_LANGUAGE_CODES = {
    "hindi": "hi-IN",
    "english": "en-IN",
    "hinglish": "hi-IN",
}

logger = logging.getLogger(__name__)


class VoiceAssistant:

    def __init__(self):
        api_key = get_sarvam_api_key()
        if not api_key:
            raise ValueError("SARVAM_API_KEY not found in .env or backend settings.")
        self._api_key = api_key
        self.stt_client = AsyncSarvamAI(
            api_subscription_key=api_key
        )

        self.tts_client = SarvamAI(
            api_subscription_key=api_key
        )

    def refresh_clients(self, api_key: str | None = None) -> None:
        """Recreate STT/TTS clients for the currently selected API key."""
        key = (api_key or get_sarvam_api_key() or "").strip()
        if not key:
            raise ValueError("No Sarvam API key is configured.")
        self.stt_client = AsyncSarvamAI(api_subscription_key=key)
        self.tts_client = SarvamAI(api_subscription_key=key)
        self._api_key = key

    def _ensure_current_key(self) -> None:
        """Pick up a key saved through the settings API without a restart."""
        if not hasattr(self, "_api_key"):
            # Manually constructed test doubles provide their own clients.
            return
        current_key = get_sarvam_api_key()
        if current_key and current_key != self._api_key:
            self.refresh_clients(current_key)

    def generate_response(self, transcript: str, session_id: str) -> str:
        """Send transcript to LangGraph and return its response."""
        clean_text = clean_transcript(transcript)
        log_text_boundary("LangGraph input / Sarvam LLM", session_id, transcript)
        if clean_text is None:
            raise EmptyTranscriptError("Speech transcript was empty; no LLM request was made.")

        try:
            result = graph.invoke(
                {"messages": [HumanMessage(content=clean_text)]},
                config={
                    "configurable": {
                        "thread_id": session_id
                    }
                },
            )
        except SarvamLLMUnavailable as error:
            logger.warning(
                "Using voice fallback session_id=%s failure_type=%s",
                session_id,
                error.failure_type,
            )
            language = classify_text_language(clean_text) or "hinglish"
            fallback = {
                "hindi": "माफ़ कीजिए, जवाब देने में थोड़ी तकनीकी दिक्कत आ रही है। मैं अभी जवाब नहीं दे पा रही हूँ। कृपया अपना सवाल फिर से बोलें।",
                "english": "Sorry, I'm having a temporary issue generating a response. Please ask your question again.",
                "hinglish": "Maaf kijiye, response generate karne mein thodi technical dikkat aa rahi hai. Main abhi jawab nahi de pa rahi hoon. Aap ek baar apna sawaal dobara bol sakte hain?",
            }[language]
            log_text_boundary("Sarvam LLM fallback response", session_id, fallback)
            return fallback

        messages = result.get("messages", []) if isinstance(result, dict) else []
        final_message = messages[-1] if messages else None
        response_text = (
            final_message.content
            if isinstance(final_message, AIMessage) and not final_message.tool_calls
            else None
        )
        request_id = extract_request_id(final_message)
        log_text_boundary(
            "LangGraph output / Sarvam LLM response",
            session_id,
            response_text,
            request_id,
        )
        if not has_nonempty_text(response_text):
            raise EmptyAssistantResponseError(
                "The assistant returned no text; text-to-speech was not called."
            )
        return response_text.strip()

    def retry_prompt(self, session_id: str, transcript: str | None = None) -> str:
        """Choose a concise retry message in the active session language."""
        language = classify_text_language(transcript or "")
        if language is None:
            try:
                state = graph.get_state({"configurable": {"thread_id": session_id}})
                language = detect_session_language(state.values.get("messages", []))
            except Exception:
                language = "hinglish"
        return {
            "hindi": "माफ़ कीजिए, मैं आपकी बात ठीक से समझ नहीं पाई। कृपया दोबारा बोलें।",
            "english": "Sorry, I didn't catch that. Please say it again.",
            "hinglish": "माफ़ कीजिए, मैं आपकी बात clear नहीं समझ पाई। कृपया फिर से बोलिए।",
        }.get(language, "माफ़ कीजिए, मैं समझ नहीं पाई। कृपया फिर से बोलिए।")

    def generate_audio(self, text: str, session_id: str = "unknown") -> bytes:
        """Speak the unchanged assistant response with the fixed Ritu sales voice."""
        self._ensure_current_key()
        log_text_boundary("Sarvam TTS input", session_id, text)
        if not has_nonempty_text(text):
            raise EmptyTTSInputError("Text-to-speech input was empty; no TTS request was made.")

        language = classify_text_language(text) or "hinglish"
        language_code = TTS_LANGUAGE_CODES.get(language, "hi-IN")

        try:
            audio = self.tts_client.text_to_speech.convert(
                text=text.strip(),
                model="bulbul:v4-flash",
                language_code=language_code,
                speaker=TTS_SPEAKER,
            )
        except Exception as error:
            log_text_boundary(
                "Sarvam TTS error",
                session_id,
                text,
                extract_request_id(error),
            )
            raise

        request_id = extract_request_id(audio)
        log_text_boundary("Sarvam TTS response", session_id, text, request_id)
        if not getattr(audio, "audios", None):
            raise RuntimeError("Sarvam TTS returned no audio data.")

        audio_bytes = base64.b64decode(
            "".join(audio.audios)
        )

        return audio_bytes

    def connect_stt(self, session_id: str = "unknown"):
        """Create a Sarvam realtime STT connection."""
        self._ensure_current_key()
        log_text_boundary("Sarvam Realtime STT connection", session_id, None)
        return self.stt_client.speech_to_text_realtime_streaming.connect(
            model="saaras:v4",
            language_code="auto",
            mode="transcribe",
            stream_type="fast",
            endpointing="vad",
            encoding="linear16",
            sample_rate=str(SAMPLE_RATE),
            silence_duration_ms="800",
        )
