import csv
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from fastapi.testclient import TestClient

from seller_dashboard.action_store import (
    persist_action,
    set_actions_csv_path,
)
from seller_dashboard import api as api_module
from seller_dashboard.api import VoiceRequest, chat
from seller_dashboard.call_closure import (
    build_final_goodbye,
    complete_call_finalization,
    fail_call_finalization,
    finalize_call_session,
    generate_final_spoken_summary,
    get_session_lifecycle_state,
    has_unanswered_assistant_question,
    is_call_termination_intent,
    is_session_active,
    mark_session_state,
    reset_session_state,
    build_pending_question_offer,
)
from seller_dashboard.conversation_store import (
    get_conversation_history,
    read_all_messages,
    save_message,
    set_conversations_csv_path,
)
from seller_dashboard.summary_store import (
    get_call_summary_record,
    read_all_raw_summaries,
    set_summaries_csv_path,
)


class CallClosureTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="closure_test_")
        self.temp_summaries_csv = Path(self.test_dir) / "test_call_summaries.csv"
        self.temp_conversations_csv = Path(self.test_dir) / "test_conversations.csv"
        self.temp_actions_csv = Path(self.test_dir) / "test_actions.csv"

        set_summaries_csv_path(self.temp_summaries_csv)
        set_conversations_csv_path(self.temp_conversations_csv)
        set_actions_csv_path(self.temp_actions_csv)

        self.seller_id = "SD-48213"
        self.session_id = f"sess-close-{uuid4()}"
        self.future_date = (
            datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=7)
        ).isoformat()

    def tearDown(self):
        reset_session_state(self.session_id)
        set_summaries_csv_path(None)
        set_conversations_csv_path(None)
        set_actions_csv_path(None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_conversation(self, session_id: str | None = None, seller_id: str | None = None):
        sess = session_id or self.session_id
        sell = seller_id or self.seller_id
        save_message(sell, sess, "seller", "मेरी बिक्री इस महीने क्यों घटी?")
        save_message(sell, sess, "assistant", "आपके 13 मुख्य प्रोडक्ट्स आउट ऑफ स्टॉक हो गए हैं।")
        save_message(sell, sess, "seller", "समझ गया, मैं स्टॉक चेक करूँगा।")
        save_message(sell, sess, "assistant", f"सुझाव है कि 2026-11-20 तक restock कर लें।")

    # 1. Explicit seller termination request
    def test_01_explicit_seller_termination_request(self):
        explicit_phrases = [
            "बस आज के लिए इतना ही।",
            "धन्यवाद, अब कॉल खत्म कर सकते हैं।",
            "That's all for today.",
            "We can end the call now.",
            "Bye.",
            "Goodbye!",
            "अलविदा!",
            "call khatam kar sakte hain",
            "bas aaj ke liye itna hi",
            "we can finish the call",
        ]
        for phrase in explicit_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(
                    is_call_termination_intent(phrase),
                    f"Expected '{phrase}' to be detected as a termination intent.",
                )

    # 2. Non-termination phrases such as "ठीक है" and "हाँ"
    def test_02_non_termination_phrases(self):
        non_termination = [
            "ठीक है",
            "हाँ",
            "अच्छा",
            "ok",
            "okay",
            "sure",
            "yes",
            "बताइए",
            "ठीक है, 2 December को restock कर दूँगा",
            "हाँ, मुझे बताइए",
            "",
            "   ",
        ]
        for phrase in non_termination:
            with self.subTest(phrase=phrase):
                self.assertFalse(
                    is_call_termination_intent(phrase),
                    f"Expected '{phrase}' NOT to be detected as termination intent.",
                )

    def test_termination_offers_to_resolve_an_unanswered_assistant_question(self):
        history = [
            {"speaker": "seller", "message_text": "My orders are down."},
            {"speaker": "assistant", "message_text": "Did you change the product price recently?"},
            {"speaker": "seller", "message_text": "That's all for today."},
        ]
        self.assertTrue(has_unanswered_assistant_question(history))
        self.assertIn("सवाल", build_pending_question_offer("english"))
        answered_history = history[:-1] + [
            {"speaker": "seller", "message_text": "No, the price is unchanged."},
            {"speaker": "assistant", "message_text": "Understood. We can review the order trend next."},
            {"speaker": "seller", "message_text": "That's all for today."},
        ]
        self.assertFalse(has_unanswered_assistant_question(answered_history))

    # 3. Summary generation during finalization
    def test_03_summary_generation_during_finalization(self):
        self._seed_conversation()
        result = finalize_call_session(self.seller_id, self.session_id)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "completed")
        summary = result["summary"]
        self.assertIsNotNone(summary)
        self.assertEqual(summary["seller_id"], self.seller_id)
        self.assertEqual(summary["session_id"], self.session_id)
        self.assertEqual(summary["call_status"], "completed")
        self.assertIn("key_metrics", summary)
        self.assertIn("identified_issues", summary)

    # 4. Summary persistence verification
    def test_04_summary_persistence_verification(self):
        self._seed_conversation()
        finalize_call_session(self.seller_id, self.session_id)

        # Verify on disk via raw read and parse
        summaries = read_all_raw_summaries(self.temp_summaries_csv)
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["session_id"], self.session_id)
        self.assertEqual(summaries[0]["call_status"], "completed")

    # 5. Transcript persistence verification
    def test_05_transcript_persistence_verification(self):
        self._seed_conversation()
        res = finalize_call_session(self.seller_id, self.session_id)
        self.assertTrue(res["success"])

        # History should now include the final closing assistant message
        history = get_conversation_history(self.session_id, self.seller_id)
        self.assertEqual(len(history), 5)  # 4 seeded + 1 final closing
        last_msg = history[-1]
        self.assertEqual(last_msg["speaker"], "assistant")
        self.assertIn(res["final_message"], last_msg["message_text"])

    # 6. Action retrieval in the final summary
    def test_06_action_retrieval_in_the_final_summary(self):
        self._seed_conversation()
        persist_action(
            seller_id=self.seller_id,
            session_id=self.session_id,
            action_type="restock_reminder",
            action_description=f"Restock kurti on {self.future_date}",
            reminder_date=self.future_date,
            seller_consent="Yes",
            related_product="Printed Cotton Kurti",
        )

        res = finalize_call_session(self.seller_id, self.session_id)
        self.assertTrue(res["success"])

        # Final spoken message and summary must reference agreed action
        final_msg = res["final_message"]
        self.assertIn("ACT-001", final_msg)
        self.assertEqual(len(res["summary"]["agreed_actions"]), 1)

    # 7. Goodbye language stays Hindi regardless of transcript language.
    def test_07_goodbye_is_hindi_for_every_input_language(self):
        hi_goodbye = build_final_goodbye("hindi")
        en_goodbye = build_final_goodbye("english")
        hing_goodbye = build_final_goodbye("hinglish")

        self.assertIn("धन्यवाद", hi_goodbye)
        self.assertIn("अलविदा", hi_goodbye)

        self.assertIn("धन्यवाद", en_goodbye)
        self.assertIn("अलविदा", en_goodbye)
        self.assertIn("धन्यवाद", hing_goodbye)
        self.assertIn("अलविदा", hing_goodbye)

    # 8. TTS failure handling
    def test_08_tts_failure_handling(self):
        self._seed_conversation()
        res = finalize_call_session(self.seller_id, self.session_id, defer_completion=True)
        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "finalizing")

        # If audio generation raises an exception, the text and summary remain safe
        from seller_dashboard.voice import VoiceAssistant
        assistant = VoiceAssistant.__new__(VoiceAssistant)
        assistant.tts_client = Mock()
        assistant.tts_client.text_to_speech.convert.side_effect = RuntimeError("TTS Service Unavailable")

        with self.assertRaises(RuntimeError):
            assistant.generate_audio(res["final_message"], self.session_id)
        fail_call_finalization(self.seller_id, self.session_id, "TTS unavailable")

        # Summary and conversation records on disk are unaffected
        summary = get_call_summary_record(self.session_id, self.seller_id)
        self.assertIsNotNone(summary)
        self.assertEqual(summary["call_status"], "failed")
        self.assertNotEqual(get_session_lifecycle_state(self.session_id), "completed")

    # 9. WebSocket remains open until final audio playback completion
    def test_09_websocket_remains_open_until_final_audio_completion(self):
        # Staged closure remains incomplete until the browser acknowledges playback.
        self._seed_conversation()
        res = finalize_call_session(self.seller_id, self.session_id, defer_completion=True)
        self.assertTrue(res["success"])
        final_text = res["final_message"]
        self.assertTrue(len(final_text) > 30)
        self.assertIn("सुरक्षित", final_text)
        self.assertEqual(get_session_lifecycle_state(self.session_id), "finalizing")
        self.assertEqual(get_call_summary_record(self.session_id, self.seller_id)["call_status"], "finalizing")

        completed = complete_call_finalization(self.seller_id, self.session_id)
        self.assertTrue(completed["success"])
        self.assertEqual(get_session_lifecycle_state(self.session_id), "completed")
        self.assertEqual(completed["summary"]["call_status"], "completed")

    def test_voice_websocket_waits_for_browser_playback_ack_before_completion(self):
        self._seed_conversation()
        seller_id = self.seller_id
        session_id = self.session_id
        api_module.register_session_seller(session_id, seller_id)

        class FakeSarvamSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def send_realtime_end(self, _message):
                return None

            async def __aiter__(self):
                yield SimpleNamespace(
                    event="transcript.final",
                    text="That's all for today.",
                    request_id="test-request",
                )

        with patch.object(api_module.voiceAssistant, "connect_stt", return_value=FakeSarvamSession()), \
             patch.object(api_module.voiceAssistant, "generate_audio", return_value=b"final-audio"):
            client = TestClient(api_module.app)
            with client.websocket_connect(f"/voice/{session_id}") as socket:
                received_types = []
                while "assistant_end" not in received_types:
                    item = socket.receive()
                    if item.get("text"):
                        message = __import__("json").loads(item["text"])
                        received_types.append(message["type"])
                self.assertEqual(get_call_summary_record(session_id, seller_id)["call_status"], "finalizing")
                socket.send_json({"type": "playback_complete"})
                ended = socket.receive_json()
                self.assertEqual(ended["type"], "call_ended")
                self.assertEqual(ended["status"], "completed")
        self.assertEqual(get_call_summary_record(session_id, seller_id)["call_status"], "completed")

    def test_staged_finalization_does_not_complete_until_ack_and_is_idempotent(self):
        self._seed_conversation()
        prepared = finalize_call_session(self.seller_id, self.session_id, defer_completion=True)
        self.assertTrue(prepared["success"])
        self.assertEqual(prepared["status"], "finalizing")

        concurrent = finalize_call_session(self.seller_id, self.session_id, defer_completion=True)
        self.assertFalse(concurrent["success"])
        self.assertEqual(concurrent["error"], "finalization_in_progress")

        first = complete_call_finalization(self.seller_id, self.session_id)
        second = complete_call_finalization(self.seller_id, self.session_id)
        self.assertTrue(first["success"])
        self.assertTrue(second["success"])
        self.assertEqual(first["summary"]["summary_id"], second["summary"]["summary_id"])

    # 10. Preventing duplicate finalization
    def test_10_preventing_duplicate_finalization(self):
        self._seed_conversation()
        first_call = finalize_call_session(self.seller_id, self.session_id)
        self.assertTrue(first_call["success"])
        first_id = first_call["summary"]["summary_id"]

        # Duplicate finalization attempt
        second_call = finalize_call_session(self.seller_id, self.session_id)
        self.assertTrue(second_call["success"])
        self.assertEqual(second_call["status"], "completed")
        self.assertEqual(second_call["summary"]["summary_id"], first_id)

        # Only one summary row exists on disk
        summaries = read_all_raw_summaries(self.temp_summaries_csv)
        self.assertEqual(len(summaries), 1)

    # 11. Preventing new turns after termination starts
    def test_11_preventing_new_turns_after_termination_starts(self):
        self._seed_conversation()
        finalize_call_session(self.seller_id, self.session_id)

        # Session should not be active
        self.assertFalse(is_session_active(self.session_id))
        self.assertEqual(get_session_lifecycle_state(self.session_id), "completed")

        # Calling chat endpoint on closed session is rejected with HTTP 400
        req = VoiceRequest(
            session_id=self.session_id,
            seller_id=self.seller_id,
            message="Can I ask one more question?",
        )
        with self.assertRaises(HTTPException) as ctx:
            chat(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("already ended", ctx.exception.detail)

    # 12. Handling summary storage failure
    def test_12_handling_summary_storage_failure(self):
        self._seed_conversation()

        # Mock save_call_summary to simulate write error
        with patch("seller_dashboard.call_closure.generate_call_summary", return_value={"success": False, "error": "storage_write_error"}):
            res = finalize_call_session(self.seller_id, self.session_id)

        self.assertFalse(res["success"])
        self.assertEqual(res["status"], "failed")

        # Session must not be marked completed (allows safe retry)
        self.assertEqual(get_session_lifecycle_state(self.session_id), "failed")

        # Existing conversation messages must remain intact
        messages = get_conversation_history(self.session_id, self.seller_id)
        self.assertEqual(len(messages), 4)

    # 13. Seller/session isolation
    def test_13_seller_and_session_isolation(self):
        seller_a = "SD-48213"
        seller_b = "SD-52077"
        sess_a = f"sess-a-{uuid4()}"
        sess_b = f"sess-b-{uuid4()}"

        self._seed_conversation(sess_a, seller_a)
        self._seed_conversation(sess_b, seller_b)

        res_a = finalize_call_session(seller_a, sess_a)
        res_b = finalize_call_session(seller_b, sess_b)

        self.assertTrue(res_a["success"])
        self.assertTrue(res_b["success"])

        # Check Seller A summary
        sum_a = get_call_summary_record(sess_a, seller_id=seller_a)
        self.assertEqual(sum_a["seller_id"], seller_a)

        # Check Seller B summary
        sum_b = get_call_summary_record(sess_b, seller_id=seller_b)
        self.assertEqual(sum_b["seller_id"], seller_b)

        # Cross query isolation
        self.assertIsNone(get_call_summary_record(sess_a, seller_id=seller_b))

    # 14. Ensuring completed status is set only after successful finalization
    def test_14_completed_status_only_after_successful_finalization(self):
        sess = f"sess-status-{uuid4()}"
        # Empty conversation fails finalization
        res_fail = finalize_call_session(self.seller_id, sess)
        self.assertFalse(res_fail["success"])
        self.assertNotEqual(get_session_lifecycle_state(sess), "completed")

        # Seed and retry
        self._seed_conversation(sess, self.seller_id)
        mark_session_state(sess, "active")
        res_success = finalize_call_session(self.seller_id, sess)
        self.assertTrue(res_success["success"])
        self.assertEqual(get_session_lifecycle_state(sess), "completed")

    def test_voice_websocket_reports_final_playback_failure_and_keeps_session_retryable(self):
        self._seed_conversation()
        seller_id = self.seller_id
        session_id = self.session_id
        api_module.register_session_seller(session_id, seller_id)

        class FakeSarvamSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def send_realtime_end(self, _message):
                return None

            async def __aiter__(self):
                yield SimpleNamespace(
                    event="transcript.final",
                    text="That's all for today.",
                    request_id="playback-failure-test",
                )

        with patch.object(api_module.voiceAssistant, "connect_stt", return_value=FakeSarvamSession()), \
             patch.object(api_module.voiceAssistant, "generate_audio", return_value=b"final-audio"):
            client = TestClient(api_module.app)
            with client.websocket_connect(f"/voice/{session_id}") as socket:
                received_types = []
                while "assistant_end" not in received_types:
                    item = socket.receive()
                    if item.get("text"):
                        received_types.append(__import__("json").loads(item["text"])["type"])
                socket.send_json({"type": "playback_failed"})
                error = socket.receive_json()
                self.assertEqual(error["type"], "error")
                self.assertEqual(error["code"], "final_playback_failed")
                self.assertEqual(get_call_summary_record(session_id, seller_id)["call_status"], "failed")
                self.assertEqual(get_session_lifecycle_state(session_id), "failed")

    def test_voice_websocket_reports_final_playback_timeout(self):
        from unittest.mock import AsyncMock

        self._seed_conversation()
        seller_id = self.seller_id
        session_id = self.session_id
        api_module.register_session_seller(session_id, seller_id)

        class FakeSarvamSession:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def send_realtime_end(self, _message):
                return None

            async def __aiter__(self):
                yield SimpleNamespace(
                    event="transcript.final",
                    text="That's all for today.",
                    request_id="playback-timeout-test",
                )

        with patch.object(api_module.voiceAssistant, "connect_stt", return_value=FakeSarvamSession()), \
             patch.object(api_module.voiceAssistant, "generate_audio", return_value=b"final-audio"), \
             patch.object(api_module.asyncio, "wait", new=AsyncMock(return_value=(set(), set()))):
            client = TestClient(api_module.app)
            with client.websocket_connect(f"/voice/{session_id}") as socket:
                received_types = []
                while "assistant_end" not in received_types:
                    item = socket.receive()
                    if item.get("text"):
                        received_types.append(__import__("json").loads(item["text"])["type"])
                error = socket.receive_json()
                self.assertEqual(error["type"], "error")
                self.assertEqual(error["code"], "final_playback_timeout")
                self.assertEqual(get_call_summary_record(session_id, seller_id)["call_status"], "failed")



if __name__ == "__main__":
    unittest.main()
