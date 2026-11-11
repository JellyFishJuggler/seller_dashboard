import unittest
from unittest.mock import patch
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from seller_dashboard import bot
from seller_dashboard.assistant_style import HINDI_RESPONSE_FALLBACK, ensure_hindi_response
from seller_dashboard.call_closure import build_final_goodbye, generate_final_spoken_summary
from seller_dashboard.tools import (
    get_cancellation_breakdown,
    get_session_seller,
    is_known_seller,
    normalize_seller_id,
    register_session_seller,
)


class EmptyRetriever:
    def retrieve(self, _query, k):
        return []


class HindiSellerIdentificationTests(unittest.TestCase):
    def test_normalizes_digit_and_spoken_number_variants(self):
        variants = (
            "SD-12345",
            "12345",
            "one two three four five",
            "वन टू थ्री फोर फाइव",
            "एक दो तीन चार पाँच",
            "१ २ ३ ४ ५",
            "Seller ID is one two three four five",
        )
        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(normalize_seller_id(value), "SD-12345")
                self.assertTrue(is_known_seller(value))

    def test_extracts_spoken_ids_from_voice_and_text_message_shapes(self):
        voice_turn = HumanMessage(content="One two three four five.")
        text_turn = HumanMessage(
            content="The current seller ID is .\n"
            "The seller's message is: एक दो तीन चार पाँच"
        )

        self.assertEqual(bot.seller_id_from_messages([voice_turn]), "SD-12345")
        self.assertEqual(bot.seller_id_from_messages([text_turn]), "SD-12345")

    def test_unknown_seller_is_not_registered(self):
        session_id = f"unknown-seller-{uuid4()}"
        register_session_seller(session_id, "99999")
        self.assertIsNone(get_session_seller(session_id))

    def test_acceptance_conversation_loads_seller_and_discloses_mock_cancellation_data(self):
        class FakeModel:
            def bind_tools(self, _tools):
                return self

            def invoke(self, messages):
                latest_seller_message = next(
                    message.content
                    for message in reversed(messages)
                    if isinstance(message, HumanMessage)
                )
                if "which products" in latest_seller_message.lower():
                    if any(
                        isinstance(message, ToolMessage)
                        and message.name == get_cancellation_breakdown.name
                        for message in messages
                    ):
                        return AIMessage(
                            content=(
                                "इन product-level cancellation reasons को उपलब्ध "
                                "अनुमानित mock data समझें, इन्हें platform से सत्यापित "
                                "जानकारी न मानें। "
                                "सबसे अधिक cancellations वाले products की सूची यह है।"
                            )
                        )
                    return AIMessage(
                        content="",
                        tool_calls=[{
                            "name": get_cancellation_breakdown.name,
                            "args": {"seller_id": "SD-12345"},
                            "id": "cancellation-breakdown-call",
                            "type": "tool_call",
                        }],
                    )
                if "one two three four five" in latest_seller_message.lower():
                    return AIMessage(content="आपकी cancellation rate की जाँच कर रही हूँ।")
                return AIMessage(content="कृपया अपना Seller ID बताएँ।")

        thread_id = f"spoken-seller-{uuid4()}"
        config = {"configurable": {"thread_id": thread_id}}
        with (
            patch.object(bot, "llm", FakeModel()),
            patch.object(bot, "_rag_retriever", EmptyRetriever()),
        ):
            graph = bot.build_graph()
            opening = graph.invoke(
                {"messages": [HumanMessage(
                    content="My cancellation rate has increased. Why is this happening?"
                )]},
                config,
            )
            identified = graph.invoke(
                {"messages": [HumanMessage(content="One two three four five.")]},
                config,
            )
            cancellations = graph.invoke(
                {"messages": [HumanMessage(
                    content="Can you tell me which products have the most cancellations?"
                )]},
                config,
            )

        self.assertIn("Seller ID", opening["messages"][-1].content)
        self.assertEqual(identified["seller_id"], "SD-12345")
        self.assertEqual(identified["seller_metrics"]["seller_id"], "SD-12345")
        self.assertEqual(cancellations["seller_id"], "SD-12345")
        self.assertIn("अनुमानित mock data", cancellations["messages"][-1].content)
        self.assertIn("platform से सत्यापित", cancellations["messages"][-1].content)

    def test_invalid_spoken_id_gets_hindi_retry_without_loading_metrics(self):
        class UnusedModel:
            def bind_tools(self, _tools):
                return self

            def invoke(self, _messages):
                self.fail("Invalid seller IDs should be handled before calling the LLM.")

        with (
            patch.object(bot, "llm", UnusedModel()),
            patch.object(bot, "_rag_retriever", EmptyRetriever()),
        ):
            graph = bot.build_graph()
            result = graph.invoke(
                {"messages": [HumanMessage(content="nine nine nine nine nine")]},
                {"configurable": {"thread_id": f"invalid-seller-{uuid4()}"}},
            )

        self.assertIn("मेरे रिकॉर्ड में नहीं मिली", result["messages"][-1].content)
        self.assertIn("दोबारा", result["messages"][-1].content)

    def test_hindi_output_policy_and_call_fallbacks_ignore_input_language(self):
        for input_language in ("english", "hindi", "hinglish"):
            policy = bot.language_policy(input_language)
            self.assertIn("Hindi", policy)
            self.assertNotIn("Respond in natural, professional English", policy)
            self.assertNotIn("Respond in conversational Hinglish", policy)

        self.assertEqual(ensure_hindi_response("Your orders increased."), HINDI_RESPONSE_FALLBACK)
        self.assertIn("धन्यवाद", build_final_goodbye("english"))
        self.assertNotIn("Thank you", build_final_goodbye("english"))
        summary = generate_final_spoken_summary(
            "SD-12345",
            "hindi-summary",
            language="english",
        )
        self.assertIn("आज", summary)
        self.assertNotIn("Today", summary)

    def test_cancellation_tool_marks_product_reason_data_as_assumed(self):
        breakdown = get_cancellation_breakdown.invoke({"seller_id": "SD-12345"})
        self.assertEqual(breakdown["seller_id"], "SD-12345")
        self.assertEqual(breakdown["reason_source"], "assumed")
        self.assertIn("not verified", breakdown["note"])
        self.assertIn("assumed mock data", bot.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
