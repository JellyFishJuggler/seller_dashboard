import asyncio
import json
import os
import time
import unittest
from threading import Event as ThreadEvent
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from langchain_sarvam.chat_models import ChatSarvamError
from websockets.exceptions import ConnectionClosedError

os.environ.setdefault("SARVAM_API_KEY", "test-key-for-voice-resilience")

from seller_dashboard import api as api_module
from seller_dashboard.api import send_realtime_audio_if_open
from seller_dashboard.bot import (
    LLM_HTTP_TIMEOUT,
    LLM_MAX_RETRIES,
    SarvamLLMUnavailable,
    invoke_sarvam_with_retries,
    llm,
)
from seller_dashboard.sarvam_credentials import (
    get_client_sarvam_api_key,
)
from seller_dashboard import sarvam_credentials
from seller_dashboard.voice import VoiceAssistant
from seller_dashboard.voice_diagnostics import EmptyAssistantResponseError


class VoiceResilienceTests(unittest.TestCase):
    def run_fake_voice_turn(
        self,
        events,
        *,
        grace=0.04,
        max_utterance=0.12,
        watch_interval=0.01,
        response_delay=0.0,
    ):
        class FakeSTT:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def __aiter__(self):
                async def messages():
                    for event in events:
                        delay = getattr(event, "delay", 0.0)
                        if delay:
                            await asyncio.sleep(delay)
                        yield event
                    await asyncio.Future()

                return messages()

            async def send_realtime_audio_input(self, _audio):
                return None

            async def send_realtime_end(self, _message):
                return None

        def generate_response(transcript, *_args):
            if response_delay:
                time.sleep(response_delay)
            return "नमस्ते, मैं आपकी मदद कर सकती हूँ।"

        with (
            patch.object(
                api_module.voiceAssistant, "connect_stt", return_value=FakeSTT()
            ),
            patch.object(
                api_module.voiceAssistant,
                "generate_response",
                side_effect=generate_response,
            ) as generate,
            patch.object(
                api_module.voiceAssistant, "generate_audio", return_value=b"audio"
            ),
            patch.object(
                api_module,
                "save_message",
                return_value={"saved": True, "duplicate": False},
            ),
            patch.object(api_module, "_resolve_seller_id", return_value="SD-12345"),
            patch.object(api_module, "VOICE_PARTIAL_FINAL_GRACE_SECONDS", grace),
            patch.object(api_module, "VOICE_PARTIAL_MAX_UTTERANCE_SECONDS", max_utterance),
            patch.object(api_module, "VOICE_FINAL_WATCH_INTERVAL_SECONDS", watch_interval),
        ):
            with TestClient(api_module.app) as client:
                with client.websocket_connect("/voice/resilience-test") as websocket:
                    received = []
                    while "assistant_end" not in [
                        message.get("type") for message in received
                    ]:
                        item = websocket.receive()
                        if item.get("text"):
                            payload = json.loads(item["text"])
                            received.append(payload)
                        elif item.get("bytes"):
                            websocket.send_json({"type": "turn_playback_complete"})

        return received, generate

    def test_timeout_retries_then_succeeds(self):
        timeout_error = ChatSarvamError("request failed")
        timeout_error.__cause__ = httpx.ReadTimeout("read timed out")
        invoke = Mock(side_effect=[timeout_error, "model response"])

        with patch("seller_dashboard.bot.time.sleep") as sleep:
            result = invoke_sarvam_with_retries(invoke, "retry-session")

        self.assertEqual(result, "model response")
        self.assertEqual(invoke.call_count, 2)
        sleep.assert_called_once_with(0.5)

    def test_retry_exhaustion_raises_fallback_signal(self):
        invoke = Mock(side_effect=httpx.ReadTimeout("read timed out"))

        with patch("seller_dashboard.bot.time.sleep"):
            with self.assertRaises(SarvamLLMUnavailable):
                invoke_sarvam_with_retries(invoke, "timeout-session")

        self.assertEqual(invoke.call_count, LLM_MAX_RETRIES + 1)

    def test_authentication_and_invalid_request_errors_are_not_retried(self):
        for status_code in (400, 401):
            with self.subTest(status_code=status_code):
                request = httpx.Request(
                    "POST",
                    "https://api.sarvam.ai/v1/chat/completions",
                )
                response = httpx.Response(status_code, request=request)
                api_error = httpx.HTTPStatusError(
                    "request rejected",
                    request=request,
                    response=response,
                )
                wrapped_error = ChatSarvamError("request failed")
                wrapped_error.__cause__ = api_error
                invoke = Mock(side_effect=wrapped_error)

                with patch("seller_dashboard.bot.time.sleep") as sleep:
                    with self.assertRaises(SarvamLLMUnavailable):
                        invoke_sarvam_with_retries(invoke, "permanent-error-session")

                invoke.assert_called_once()
                sleep.assert_not_called()

    def test_sarvam_http_client_has_explicit_read_timeout(self):
        self.assertEqual(LLM_HTTP_TIMEOUT.read, 90.0)
        self.assertEqual(
            llm.client._client_wrapper.get_timeout().read,
            90.0,
        )

    def test_exhausted_llm_failure_returns_spoken_fallback(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        with patch(
            "seller_dashboard.voice.graph.invoke",
            side_effect=SarvamLLMUnavailable("unavailable"),
        ):
            response = assistant.generate_response(
                "Could you check my sales?",
                "fallback-session",
            )

        self.assertTrue(response.strip())
        self.assertIn("तकनीकी परेशानी", response)
        self.assertIn("पा रही हूँ", response)

    def test_empty_llm_response_is_rejected_before_tts(self):
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.tts_client = Mock()
        with patch(
            "seller_dashboard.voice.graph.invoke",
            return_value={"messages": [AIMessage(content="")]},
        ):
            with self.assertRaises(EmptyAssistantResponseError):
                assistant.generate_response("Hello", "empty-session")

        assistant.tts_client.text_to_speech.convert.assert_not_called()

    def test_api_does_not_send_empty_llm_text_to_tts(self):
        class FakeSTT:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def __aiter__(self):
                async def messages():
                    yield SimpleNamespace(
                        event="transcript.final",
                        text="Hello",
                        request_id="empty-response-request",
                    )
                    await asyncio.Future()

                return messages()

            async def send_realtime_audio_input(self, _audio):
                return None

            async def send_realtime_end(self, _message):
                return None

        with (
            patch.object(api_module.voiceAssistant, "connect_stt", return_value=FakeSTT()),
            patch.object(api_module.voiceAssistant, "generate_response", return_value=""),
            patch.object(api_module.voiceAssistant, "generate_audio") as generate_audio,
            patch.object(api_module.voiceAssistant, "retry_prompt", return_value="Try again."),
            patch.object(api_module, "_resolve_seller_id", return_value="seller-test"),
            patch.object(api_module, "save_message", return_value={"saved": True}),
        ):
            with TestClient(api_module.app) as client:
                with client.websocket_connect("/voice/empty-llm-response") as websocket:
                    received_types = []
                    while "assistant_end" not in received_types:
                        message = websocket.receive()
                        if message.get("text"):
                            received_types.append(
                                json.loads(message["text"])["type"]
                            )

        generate_audio.assert_not_called()

    def test_closed_stt_connection_does_not_receive_more_audio(self):
        class FakeSTT:
            def __init__(self):
                self.sent = []

            async def send_realtime_audio_input(self, audio):
                self.sent.append(audio)

        stt = FakeSTT()
        closed = asyncio.Event()
        closed.set()

        sent = asyncio.run(
            send_realtime_audio_if_open(stt, "audio", closed, "closed-session")
        )

        self.assertFalse(sent)
        self.assertEqual(stt.sent, [])

    def test_stt_send_closure_marks_socket_closed_and_stops_future_audio(self):
        class FakeSTT:
            def __init__(self):
                self.send_attempts = 0

            async def send_realtime_audio_input(self, _audio):
                self.send_attempts += 1
                raise ConnectionClosedError(None, None)

        stt = FakeSTT()
        closed = asyncio.Event()

        first_result = asyncio.run(
            send_realtime_audio_if_open(stt, "audio", closed, "send-closed-session")
        )
        second_result = asyncio.run(
            send_realtime_audio_if_open(stt, "audio", closed, "send-closed-session")
        )

        self.assertFalse(first_result)
        self.assertFalse(second_result)
        self.assertTrue(closed.is_set())
        self.assertEqual(stt.send_attempts, 1)

    def test_fatal_stt_inactivity_closes_voice_with_recoverable_error(self):
        class FakeSTT:
            def __init__(self):
                self.sent_audio = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def __aiter__(self):
                async def messages():
                    yield SimpleNamespace(
                        event="transcript.final",
                        text=" ",
                        request_id="silence-request",
                    )
                    yield SimpleNamespace(
                        event="error",
                        code="inactivity_timeout",
                        is_fatal=True,
                        request_id="stt-request",
                    )

                return messages()

            async def send_realtime_audio_input(self, audio):
                self.sent_audio.append(audio)

            async def send_realtime_end(self, _message):
                return None

        fake_stt = FakeSTT()
        with patch.object(api_module.voiceAssistant, "connect_stt", return_value=fake_stt):
            with TestClient(api_module.app) as client:
                with client.websocket_connect("/voice/inactivity-test") as websocket:
                    message = websocket.receive_json()
                    while message.get("type") == "stt_ready":
                        message = websocket.receive_json()

        self.assertEqual(message["code"], "stt_connection_closed")
        self.assertTrue(message["recoverable"])
        self.assertEqual(fake_stt.sent_audio, [])

    def test_websocket_disconnect_cancels_stt_event_pump(self):
        iterator_cancelled = ThreadEvent()

        class FakeSTT:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def __aiter__(self):
                async def messages():
                    try:
                        yield SimpleNamespace(event="session.begin")
                        await asyncio.Future()
                    finally:
                        iterator_cancelled.set()

                return messages()

            async def send_realtime_audio_input(self, _audio):
                return None

            async def send_realtime_end(self, _message):
                return None

        with patch.object(
            api_module.voiceAssistant, "connect_stt", return_value=FakeSTT()
        ):
            with TestClient(api_module.app) as client:
                with client.websocket_connect("/voice/disconnect-cleanup-test") as websocket:
                    self.assertEqual(websocket.receive_json()["type"], "stt_ready")

        self.assertTrue(iterator_cancelled.wait(timeout=1))

    def test_fatal_stt_quota_error_reports_billing_not_microphone(self):
        class FakeSTT:
            def __init__(self):
                self.enter_count = 0

            async def __aenter__(self):
                self.enter_count += 1
                return self

            async def __aexit__(self, *_args):
                return False

            def __aiter__(self):
                async def messages():
                    yield SimpleNamespace(
                        event="error",
                        code="quota_exceeded",
                        is_fatal=True,
                        message="Sarvam quota exhausted",
                        request_id="quota-request",
                    )

                return messages()

            async def send_realtime_audio_input(self, _audio):
                return None

            async def send_realtime_end(self, _message):
                return None

        fake_stt = FakeSTT()
        with patch.object(api_module.voiceAssistant, "connect_stt", return_value=fake_stt):
            with TestClient(api_module.app) as client:
                with client.websocket_connect("/voice/quota-test") as websocket:
                    message = websocket.receive_json()
                    while message.get("type") == "stt_ready":
                        message = websocket.receive_json()

        self.assertEqual(message["type"], "error")
        self.assertEqual(message["code"], "stt_quota_exceeded")
        self.assertTrue(message["recoverable"])
        self.assertIn("सीमा पूरी हो गई है", message["message"])
        self.assertEqual(fake_stt.enter_count, 1)

    def test_stt_auth_failure_selects_second_env_key_for_reconnect(self):
        client_id = f"stt-key-fallback-{id(self)}"

        class FakeSTT:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def __aiter__(self):
                async def messages():
                    yield SimpleNamespace(
                        event="error",
                        code="invalid_subscription_key",
                        message="Invalid subscription key",
                        is_fatal=True,
                    )

                return messages()

            async def send_realtime_audio_input(self, _audio):
                return None

            async def send_realtime_end(self, _message):
                return None

        with (
            patch.dict(
                os.environ,
                {
                    "SARVAM_API_KEY": "",
                    "SARVAM_API_KEY_1": "first-stt-test-key",
                    "SARVAM_API_KEY_2": "second-stt-test-key",
                },
                clear=True,
            ),
            patch.object(
                api_module.voiceAssistant,
                "connect_stt",
                return_value=FakeSTT(),
            ),
        ):
            with TestClient(api_module.app) as client:
                with client.websocket_connect(
                    f"/voice/stt-key-rotation?client_id={client_id}"
                ) as websocket:
                    message = websocket.receive_json()
                    while message.get("type") == "stt_ready":
                        message = websocket.receive_json()

            self.assertEqual(message["code"], "stt_auth_failed")
            self.assertIn("दूसरी configured API key", message["message"])
            self.assertEqual(
                get_client_sarvam_api_key(client_id),
                "second-stt-test-key",
            )
        sarvam_credentials._CLIENT_KEY_INDEX.pop(client_id, None)

    def test_stt_connection_failure_reports_quota_without_starting_stream(self):
        class FakeSTT:
            async def __aenter__(self):
                raise RuntimeError("quota exceeded while opening STT")

            async def __aexit__(self, *_args):
                return False

        with patch.object(
            api_module.voiceAssistant,
            "connect_stt",
            return_value=FakeSTT(),
        ):
            with TestClient(api_module.app) as client:
                with client.websocket_connect("/voice/quota-connect-test") as websocket:
                    message = websocket.receive_json()

        self.assertEqual(message["type"], "error")
        self.assertEqual(message["code"], "stt_quota_exceeded")
        self.assertTrue(message["recoverable"])
        self.assertIn("सीमा पूरी हो गई है", message["message"])

    def test_stale_partial_is_finalized_when_no_final_transcript_arrives(self):
        received, generate_response = self.run_fake_voice_turn(
            [
                SimpleNamespace(
                    event="transcript.partial",
                    text="हेलो",
                    utterance_idx=None,
                    request_id="partial-request",
                ),
            ],
            grace=0.02,
            max_utterance=0.03,
        )

        received_types = [message["type"] for message in received]
        assistant_start = next(
            message for message in received if message["type"] == "assistant_start"
        )
        self.assertEqual(assistant_start["transcript"], "हेलो")
        self.assertEqual(received_types.count("assistant_start"), 1)
        self.assertEqual(received_types.count("assistant_reply"), 1)
        self.assertIn("assistant_end", received_types)
        reply = next(
            message for message in received if message["type"] == "assistant_reply"
        )
        self.assertIn("नमस्ते", reply["text"])
        generate_response.assert_called_once()

    def test_vad_speech_end_allows_stable_partial_fallback(self):
        received, generate_response = self.run_fake_voice_turn(
            [
                SimpleNamespace(
                    event="transcript.partial",
                    text="मेरी बिक्री",
                    utterance_idx=7,
                ),
                SimpleNamespace(
                    event="vad.speech_end",
                    utterance_idx=7,
                ),
            ],
            grace=0.02,
            max_utterance=10.0,
        )

        self.assertEqual(
            [message["type"] for message in received].count("assistant_start"), 1
        )
        self.assertEqual(generate_response.call_args.args[0], "मेरी बिक्री")

    def test_partial_then_real_final_uses_final_once(self):
        received, generate_response = self.run_fake_voice_turn(
            [
                SimpleNamespace(
                    event="transcript.partial",
                    text="हेलो",
                    utterance_idx=4,
                    request_id="partial-request",
                ),
                SimpleNamespace(
                    event="transcript.final",
                    text="हेलो, मेरी मदद कीजिए।",
                    utterance_idx=4,
                    request_id="final-request",
                ),
            ]
        )

        self.assertEqual(
            [message["type"] for message in received].count("assistant_start"), 1
        )
        self.assertEqual(
            generate_response.call_args.args[0],
            "हेलो, मेरी मदद कीजिए।",
        )

    def test_empty_final_uses_correlated_partial_once(self):
        received, generate_response = self.run_fake_voice_turn(
            [
                SimpleNamespace(
                    event="transcript.partial",
                    text="हेलो",
                    utterance_idx=None,
                    request_id="same-request",
                ),
                SimpleNamespace(
                    event="transcript.final",
                    text="",
                    utterance_idx=None,
                    request_id="same-request",
                ),
            ]
        )

        self.assertEqual(
            [message["type"] for message in received].count("assistant_start"), 1
        )
        self.assertEqual(generate_response.call_args.args[0], "हेलो")

    def test_late_final_after_indexless_watchdog_fallback_is_ignored(self):
        received, generate_response = self.run_fake_voice_turn(
            [
                SimpleNamespace(
                    event="transcript.partial",
                    text="हेलो",
                    utterance_idx=None,
                    request_id="same-request",
                ),
                SimpleNamespace(
                    event="transcript.final",
                    text="हेलो",
                    utterance_idx=None,
                    request_id="same-request",
                    delay=0.06,
                ),
            ],
            grace=0.01,
            max_utterance=0.02,
            response_delay=0.15,
        )

        self.assertEqual(
            [message["type"] for message in received].count("assistant_start"), 1
        )
        generate_response.assert_called_once()

    def test_long_paused_partial_is_not_cut_at_age_limit_until_stable(self):
        received, generate_response = self.run_fake_voice_turn(
            [
                SimpleNamespace(
                    event="transcript.partial",
                    text="हेलो",
                    utterance_idx=8,
                ),
                SimpleNamespace(
                    event="transcript.partial",
                    text="हेलो, मेरी बात सुनिए",
                    utterance_idx=8,
                    delay=0.06,
                ),
                SimpleNamespace(
                    event="vad.speech_end",
                    utterance_idx=8,
                    delay=0.01,
                ),
            ],
            grace=0.08,
            max_utterance=0.03,
        )

        start = next(
            message for message in received if message["type"] == "assistant_start"
        )
        self.assertEqual(start["transcript"], "हेलो, मेरी बात सुनिए")
        generate_response.assert_called_once()


if __name__ == "__main__":
    unittest.main()
