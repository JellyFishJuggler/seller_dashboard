import csv
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
from zoneinfo import ZoneInfo

from seller_dashboard.assistant_style import FEMININE_VOICE_PROMPT

from seller_dashboard.action_store import (
    persist_action,
    set_actions_csv_path,
    update_action_status_record,
)
from seller_dashboard.conversation_store import (
    save_message,
    set_conversations_csv_path,
)
from seller_dashboard.summary_store import (
    CSV_FIELDS,
    generate_call_summary,
    get_call_summary_record,
    get_seller_call_summaries,
    get_summaries_csv_path,
    read_all_raw_summaries,
    save_call_summary,
    set_summaries_csv_path,
)


class SummaryStorageTests(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="summary_test_")
        self.temp_summaries_csv = Path(self.test_dir) / "test_call_summaries.csv"
        self.temp_conversations_csv = Path(self.test_dir) / "test_conversations.csv"
        self.temp_actions_csv = Path(self.test_dir) / "test_actions.csv"

        set_summaries_csv_path(self.temp_summaries_csv)
        set_conversations_csv_path(self.temp_conversations_csv)
        set_actions_csv_path(self.temp_actions_csv)

        self.seller_id = "SD-48213"
        self.session_id = f"test-sess-{uuid4()}"
        self.future_date = (
            datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=7)
        ).isoformat()

    def tearDown(self):
        set_summaries_csv_path(None)
        set_conversations_csv_path(None)
        set_actions_csv_path(None)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _seed_basic_conversation(self, session_id: str | None = None, seller_id: str | None = None):
        sess = session_id or self.session_id
        sell = seller_id or self.seller_id
        save_message(sell, sess, "seller", "मेरी बिक्री इस महीने कम क्यों हुई?")
        save_message(sell, sess, "assistant", "आपके 13 मुख्य प्रोडक्ट्स आउट ऑफ स्टॉक हो गए हैं, जिससे सेल्स घटी है।")
        save_message(sell, sess, "seller", "हाँ, मैं समझ गया। क्या सुझाव है?")
        save_message(sell, sess, "assistant", "हम सुझाव देते हैं कि आप Printed Cotton Kurti का स्टॉक 2026-11-20 तक restock कर लें।")
        save_message(sell, sess, "seller", "हाँ, मैं 2026-11-20 तक restock कर दूँगा।")

    # 1. Generating a summary from a valid conversation
    def test_01_generate_summary_from_valid_conversation(self):
        self._seed_basic_conversation()
        result = generate_call_summary(self.seller_id, self.session_id)

        self.assertTrue(result["success"])
        summary = result["summary"]
        self.assertTrue(summary["summary_id"].startswith("SUM-"))
        self.assertEqual(summary["seller_id"], self.seller_id)
        self.assertEqual(summary["session_id"], self.session_id)
        self.assertEqual(summary["call_status"], "completed")
        self.assertEqual(summary["source_message_count"], 5)
        self.assertTrue(summary["overall_summary"])
        self.assertIsInstance(summary["business_overview"], dict)
        self.assertIsInstance(summary["key_metrics"], dict)
        self.assertIsInstance(summary["identified_issues"], list)

    # 2. Including only actions belonging to the requested session
    def test_02_include_only_actions_belonging_to_requested_session(self):
        self._seed_basic_conversation()
        other_session = f"other-sess-{uuid4()}"

        # Action for this session
        persist_action(
            seller_id=self.seller_id,
            session_id=self.session_id,
            action_type="restock_reminder",
            action_description=f"Restock kurti on {self.future_date}",
            reminder_date=self.future_date,
            seller_consent="Yes",
            related_product="Printed Cotton Kurti",
        )

        # Action for a different session
        persist_action(
            seller_id=self.seller_id,
            session_id=other_session,
            action_type="stock_sync_check",
            action_description=f"Sync check on {self.future_date}",
            reminder_date=self.future_date,
            seller_consent="Yes",
        )

        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        agreed = res["summary"]["agreed_actions"]
        self.assertEqual(len(agreed), 1)
        self.assertEqual(agreed[0]["action_type"], "restock_reminder")
        self.assertEqual(agreed[0]["related_product"], "Printed Cotton Kurti")

    # 3. Including verified seller metrics
    def test_03_include_verified_seller_metrics(self):
        self._seed_basic_conversation()
        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        metrics = res["summary"]["key_metrics"]

        # SD-48213 metrics from Python tools
        self.assertEqual(metrics["sales"]["last_month"], 200000)
        self.assertEqual(metrics["sales"]["this_month"], 135000)
        self.assertEqual(metrics["sales"]["change_pct"], -32.5)

        self.assertEqual(metrics["orders"]["last_month"], 400)
        self.assertEqual(metrics["orders"]["this_month"], 270)

        self.assertEqual(metrics["avg_selling_price"]["last_month"], 500)
        self.assertEqual(metrics["avg_selling_price"]["this_month"], 500)

        self.assertEqual(metrics["cancellation_rate_pct"]["last_month"], 8.0)
        self.assertEqual(metrics["cancellation_rate_pct"]["this_month"], 14.0)

        self.assertEqual(metrics["out_of_stock_products"]["last_month"], 5)
        self.assertEqual(metrics["out_of_stock_products"]["this_month"], 18)

    # 4. Distinguishing facts from hypotheses
    def test_04_distinguish_facts_from_hypotheses(self):
        self._seed_basic_conversation()
        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        issues = res["summary"]["identified_issues"]

        types = {i["type"] for i in issues}
        self.assertIn("fact", types)
        self.assertIn("hypothesis", types)

        # Verified facts must be labeled 'fact'
        facts = [i for i in issues if i["type"] == "fact"]
        self.assertTrue(any("out-of-stock" in f["summary"].lower() or "cancellation" in f["summary"].lower() for f in facts))

        # Unproven explanations must be labeled 'hypothesis'
        hypotheses = [i for i in issues if i["type"] == "hypothesis"]
        self.assertTrue(any("mismatch" in h["summary"].lower() or "hypothesis" in h["issue"].lower() for h in hypotheses))

    # 5. Correctly representing pending, completed and cancelled actions
    def test_05_represent_pending_completed_cancelled_actions(self):
        self._seed_basic_conversation()
        d1 = (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=2)).isoformat()
        d2 = (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=4)).isoformat()
        d3 = (datetime.now(ZoneInfo("Asia/Kolkata")).date() + timedelta(days=6)).isoformat()

        a1 = persist_action(self.seller_id, self.session_id, "restock_reminder", f"Kurti restock {d1}", d1, "Yes")
        a2 = persist_action(self.seller_id, self.session_id, "stock_sync_check", f"Sync check {d2}", d2, "Yes")
        a3 = persist_action(self.seller_id, self.session_id, "followup_call", f"Follow up {d3}", d3, "Yes")

        update_action_status_record(a2["action_id"], "Completed", seller_id=self.seller_id)
        update_action_status_record(a3["action_id"], "Cancelled", seller_id=self.seller_id)

        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        actions = res["summary"]["agreed_actions"]
        self.assertEqual(len(actions), 3)

        status_by_id = {act["action_id"]: act["status"] for act in actions}
        self.assertEqual(status_by_id[a1["action_id"]], "Pending")
        self.assertEqual(status_by_id[a2["action_id"]], "Completed")
        self.assertEqual(status_by_id[a3["action_id"]], "Cancelled")

    # 6. Preserving Hindi and Hinglish text
    def test_06_preserve_hindi_and_hinglish(self):
        self._seed_basic_conversation()
        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])

        # Verify in raw CSV bytes that Devanagari Hindi characters are intact
        with open(self.temp_summaries_csv, "r", encoding="utf-8-sig") as f:
            content = f.read()

        self.assertIn("हम सुझाव देते हैं", content)
        self.assertIn("restock कर दूँगा", content)
        self.assertIn("Printed Cotton Kurti", content)

    # 7. Handling missing product cost or other unavailable information
    def test_07_handle_missing_product_cost_information(self):
        self._seed_basic_conversation()
        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        unresolved = res["summary"]["unresolved_questions"]

        # Must explicitly note that unit costs and profit margins were unavailable
        self.assertTrue(any("cost" in u.lower() or "margin" in u.lower() for u in unresolved))

    # 8. Preventing unsupported discount-causality claims
    def test_08_prevent_unsupported_discount_causality_claims(self):
        self._seed_basic_conversation()
        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        issues = res["summary"]["identified_issues"]

        # If discount or ASP is mentioned, it must not be labeled as a confirmed fact
        for item in issues:
            if "discount" in item["summary"].lower() or "asp" in item["summary"].lower():
                self.assertNotEqual(item["type"], "fact")

    # 9. Preventing duplicate summaries for the same session (updating existing instead)
    def test_09_prevent_duplicate_summaries_same_session(self):
        self._seed_basic_conversation()
        res1 = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res1["success"])
        id1 = res1["summary"]["summary_id"]

        # Regenerate summary for the exact same session
        res2 = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res2["success"])
        id2 = res2["summary"]["summary_id"]

        self.assertEqual(id1, id2, "Regenerated summary must reuse existing summary_id.")

        # Verify CSV has exactly 1 summary row
        raw = read_all_raw_summaries(self.temp_summaries_csv)
        self.assertEqual(len(raw), 1)

    # 10. Retrieving summaries after storage reload
    def test_10_retrieve_summaries_after_storage_reload(self):
        self._seed_basic_conversation()
        res = generate_call_summary(self.seller_id, self.session_id)
        self.assertTrue(res["success"])
        summary_id = res["summary"]["summary_id"]

        # Query using get_call_summary_record
        retrieved = get_call_summary_record(self.session_id, self.seller_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["summary_id"], summary_id)
        self.assertEqual(retrieved["seller_id"], self.seller_id)
        self.assertIsInstance(retrieved["key_metrics"], dict)
        self.assertIsInstance(retrieved["identified_issues"], list)

    # 11. Seller and session isolation
    def test_11_seller_and_session_isolation(self):
        seller_a = "SD-48213"
        seller_b = "SD-52077"
        sess_a = f"sess-a-{uuid4()}"
        sess_b = f"sess-b-{uuid4()}"

        self._seed_basic_conversation(sess_a, seller_a)
        self._seed_basic_conversation(sess_b, seller_b)

        generate_call_summary(seller_a, sess_a)
        generate_call_summary(seller_b, sess_b)

        # Seller A list
        sums_a = get_seller_call_summaries(seller_a)
        self.assertEqual(len(sums_a), 1)
        self.assertEqual(sums_a[0]["session_id"], sess_a)
        self.assertNotIn(sess_b, [s["session_id"] for s in sums_a])

        # Seller B list
        sums_b = get_seller_call_summaries(seller_b)
        self.assertEqual(len(sums_b), 1)
        self.assertEqual(sums_b[0]["session_id"], sess_b)
        self.assertNotIn(sess_a, [s["session_id"] for s in sums_b])

        # Unauthorized session query
        unauth = get_call_summary_record(sess_a, seller_id=seller_b)
        self.assertIsNone(unauth)

    # 12. UTF-8 BOM encoding
    def test_12_utf8_bom_encoding(self):
        self._seed_basic_conversation()
        generate_call_summary(self.seller_id, self.session_id)

        with open(self.temp_summaries_csv, "rb") as f:
            raw = f.read()

        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), "Summary CSV must start with UTF-8 BOM.")
        with open(self.temp_summaries_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            self.assertEqual(reader.fieldnames, CSV_FIELDS)

    # 13. Handling malformed LLM output gracefully
    def test_13_handle_malformed_llm_output(self):
        self._seed_basic_conversation()

        # Mock LLM that raises an exception
        bad_llm = Mock()
        bad_llm.invoke.side_effect = RuntimeError("Sarvam LLM connection timeout")

        res = generate_call_summary(self.seller_id, self.session_id, llm=bad_llm)
        self.assertTrue(res["success"])
        # Should gracefully fall back to grounded summary without crashing
        self.assertTrue(res["summary"]["overall_summary"])

    # 14. Handling empty conversation history without inventing a summary
    def test_14_handle_empty_conversation_history(self):
        empty_session = f"empty-sess-{uuid4()}"
        res = generate_call_summary(self.seller_id, empty_session)

        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "empty_conversation")

        # CSV must not have any rows written
        raw = read_all_raw_summaries(self.temp_summaries_csv)
        self.assertEqual(len(raw), 0)

    # 15. Summary prose must use the assistant's feminine voice
    def test_15_summary_prompt_requires_feminine_voice(self):
        self._seed_basic_conversation()
        fake_llm = Mock()
        fake_llm.invoke.return_value = SimpleNamespace(content="Call summary generated.")

        result = generate_call_summary(
            self.seller_id,
            self.session_id,
            llm=fake_llm,
            language="hindi",
        )

        self.assertTrue(result["success"])
        prompt = fake_llm.invoke.call_args.args[0]
        self.assertIn(FEMININE_VOICE_PROMPT, prompt)
        self.assertIn("मैं जाँच कर रही हूँ", prompt)
        self.assertIn("मैं समझ सकती हूँ", prompt)


if __name__ == "__main__":
    unittest.main()
