import base64
from pathlib import Path
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage

from seller_dashboard.assistant_style import ENGLISH_RESPONSE_PROMPT, ensure_hindi_response

from seller_dashboard.action_store import set_actions_csv_path
from seller_dashboard.bot import language_policy
from seller_dashboard.call_closure import build_final_goodbye
from seller_dashboard.tools import create_action, get_call_summary
from seller_dashboard.voice import TTS_SPEAKER, VoiceAssistant
from seller_dashboard.voice_diagnostics import (
    EmptyAssistantResponseError,
    EmptyTTSInputError,
    EmptyTranscriptError,
    clean_transcript,
)


class VoiceLanguageAndActionTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="voice_action_test_")
        self.temp_csv = Path(self.test_dir) / "actions.csv"
        set_actions_csv_path(self.temp_csv)

    def tearDown(self):
        set_actions_csv_path(None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_language_policy_is_hindi_for_voice_and_english_for_text(self):
        expected_policy = language_policy("hindi", voice_mode=True)
        for requested_language in ("hindi", "english", "hinglish"):
            with self.subTest(requested_language=requested_language):
                self.assertEqual(
                    language_policy(requested_language, voice_mode=True),
                    expected_policy,
                )
                self.assertIn("Always answer in natural", expected_policy)
                self.assertEqual(language_policy(requested_language), ENGLISH_RESPONSE_PROMPT)

    def test_tts_uses_hindi_response_and_language_for_every_input(self):
        samples = [
            (
                "मेरा एएसपी गिर रहा है, क्या मुझे डिस्काउंट बंद कर देना चाहिए?",
                "आपकी बिक्री इस महीने कम हुई है।",
                "hi-IN",
            ),
            (
                "My ASP is falling; should I stop discounts?",
                "Your sales are declining this month.",
                "en-IN",
            ),
            (
                "मेरा ASP गिर रहा है, should I stop discounts?",
                "आपकी sales इस महीने कम हुई हैं।",
                "hi-IN",
            ),
        ]
        for transcript, text, language_code in samples:
            with self.subTest(language=language_code):
                assistant = VoiceAssistant.__new__(VoiceAssistant)
                response_audio = base64.b64encode(b"mock-audio").decode("ascii")
                assistant.tts_client = SimpleNamespace(
                    text_to_speech=SimpleNamespace(
                        convert=Mock(return_value=SimpleNamespace(
                            audios=[response_audio], request_id="tts-test-id"
                        ))
                    )
                )
                with unittest.mock.patch(
                    "seller_dashboard.voice.graph.invoke",
                    return_value={"messages": [AIMessage(content=text)]},
                ) as graph_invoke:
                    response_text = assistant.generate_response(transcript, "language-test")
                sent_message = graph_invoke.call_args.args[0]["messages"][0]
                self.assertIsInstance(sent_message, HumanMessage)
                self.assertEqual(sent_message.content, transcript)
                result = assistant.generate_audio(response_text, "language-test")
                request = assistant.tts_client.text_to_speech.convert.call_args.kwargs
                self.assertEqual(request["text"], ensure_hindi_response(text))
                self.assertEqual(request["language_code"], "hi-IN")
                self.assertEqual(request["speaker"], TTS_SPEAKER)
                self.assertEqual(result, b"mock-audio")

    def test_tts_speaker_is_fixed_for_every_language_and_message_type(self):
        self.assertEqual(TTS_SPEAKER, "ritu_hi_sales")

        samples = [
            ("Hindi response", "आपकी बिक्री इस महीने कम हुई है।"),
            ("English response", "Your sales are declining this month."),
            ("Hinglish response", "आपकी sales इस महीने कम हुई हैं।"),
            (
                "LLM fallback",
                "Maaf kijiye, response generate karne mein thodi technical dikkat aa rahi hai. "
                "Aap ek baar apna sawaal dobara bol sakte hain?",
            ),
            (
                "Voice error",
                "I couldn't complete that response. Please try speaking again.",
            ),
            ("Hindi goodbye", build_final_goodbye("hindi")),
            ("English goodbye", build_final_goodbye("english")),
            ("Hinglish goodbye", build_final_goodbye("hinglish")),
            (
                "Call summary",
                "Call summary: sales fell 32 percent this month and stockouts increased.",
            ),
        ]
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        response_audio = base64.b64encode(b"mock-audio").decode("ascii")
        convert = Mock(return_value=SimpleNamespace(
            audios=[response_audio], request_id="tts-test-id"
        ))
        assistant.tts_client = SimpleNamespace(
            text_to_speech=SimpleNamespace(convert=convert)
        )

        selected_speakers = set()
        for label, text in samples:
            with self.subTest(message=label):
                convert.reset_mock()
                assistant.generate_audio(text, "fixed-speaker-test")
                request = convert.call_args.kwargs
                self.assertEqual(request["speaker"], TTS_SPEAKER)
                self.assertEqual(request["language_code"], "hi-IN")
                self.assertEqual(request["text"], ensure_hindi_response(text))
                selected_speakers.add(request["speaker"])

        self.assertEqual(selected_speakers, {TTS_SPEAKER})

    def test_empty_and_whitespace_stt_transcripts_do_not_invoke_graph(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        with unittest.mock.patch("seller_dashboard.voice.graph.invoke") as graph_invoke:
            for transcript in (None, "", "   \t\n"):
                with self.subTest(transcript=repr(transcript)):
                    self.assertIsNone(clean_transcript(transcript))
                    with self.assertRaises(EmptyTranscriptError):
                        assistant.generate_response(transcript, "empty-stt-test")
            graph_invoke.assert_not_called()
        self.assertEqual(clean_transcript("  नमस्ते  "), "नमस्ते")

    def test_empty_llm_response_does_not_reach_tts(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.tts_client = SimpleNamespace(
            text_to_speech=SimpleNamespace(convert=Mock())
        )
        with unittest.mock.patch(
            "seller_dashboard.voice.graph.invoke",
            return_value={"messages": [AIMessage(content="   ")]},
        ):
            with self.assertRaises(EmptyAssistantResponseError):
                reply = assistant.generate_response("valid question", "empty-llm-test")
                assistant.generate_audio(reply, "empty-llm-test")
        assistant.tts_client.text_to_speech.convert.assert_not_called()

    def test_empty_or_whitespace_tts_input_never_calls_sarvam(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.tts_client = SimpleNamespace(
            text_to_speech=SimpleNamespace(convert=Mock())
        )
        for text in (None, "", " \t\n"):
            with self.subTest(text=repr(text)):
                with self.assertRaises(EmptyTTSInputError):
                    assistant.generate_audio(text, "empty-tts-test")
        assistant.tts_client.text_to_speech.convert.assert_not_called()

    def test_realtime_stt_uses_automatic_language_detection(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        connect = Mock(return_value="fake-stt-session")
        assistant.stt_client = SimpleNamespace(
            speech_to_text_realtime_streaming=SimpleNamespace(connect=connect)
        )

        self.assertEqual(assistant.connect_stt(), "fake-stt-session")
        self.assertEqual(connect.call_args.kwargs["language_code"], "auto")
        self.assertEqual(connect.call_args.kwargs["model"], "saaras:v4")

    def test_action_requires_explicit_consent_and_one_valid_date(self):
        thread_id = f"action-test-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        requested_date = (
            datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=5)
        ).isoformat()
        details = f"Follow up with seller about the stock sync check. Agreed date: {requested_date}."

        no_consent = create_action.invoke(
            {
                "action": "stock_sync_check",
                "details": details,
                "seller_confirmation": "",
            },
            config=config,
        )
        self.assertFalse(no_consent["logged"])

        no_date = create_action.invoke(
            {
                "action": "stock_sync_check",
                "details": "Follow up about the stock sync check next Friday.",
                "seller_confirmation": "Yes, please.",
            },
            config=config,
        )
        self.assertFalse(no_date["logged"])

        ambiguous_date = create_action.invoke(
            {
                "action": "stock_sync_check",
                "details": f"Move from {requested_date} to {requested_date}.",
                "seller_confirmation": "Yes, please.",
            },
            config=config,
        )
        self.assertFalse(ambiguous_date["logged"])

        logged = create_action.invoke(
            {
                "action": "stock_sync_check",
                "details": details,
                "seller_confirmation": f"Yes, log it for {requested_date}.",
            },
            config=config,
        )
        self.assertTrue(logged["logged"])
        self.assertFalse(logged["executed"])
        self.assertEqual(logged["requested_date"], requested_date)
        self.assertIn("NOT been executed", logged["message"])

        summary = get_call_summary.invoke({}, config=config)
        self.assertEqual(len(summary["actions"]), 1)
        self.assertEqual(summary["actions"][0]["requested_date"], requested_date)


if __name__ == "__main__":
    unittest.main()
