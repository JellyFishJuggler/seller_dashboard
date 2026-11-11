import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from seller_dashboard import bot
from seller_dashboard.rag import expand_retrieval_query


class FakeRetriever:
    def __init__(self):
        self.query = None
        self.k = None

    def retrieve(self, query, k):
        self.query = query
        self.k = k
        return [{"content": "Prioritise stockouts using historical orders."}]


class DiagnosticContextTests(unittest.TestCase):
    def test_graph_loads_seller_data_once_and_supplies_it_to_the_first_reply(self):
        class FakeModel:
            seen_messages = []

            def bind_tools(self, _tools):
                return self

            def invoke(self, messages):
                self.seen_messages.append(messages)
                return AIMessage(content="Observed change. Did you recently change pricing?")

        model = FakeModel()
        retriever = FakeRetriever()
        metrics_call = Mock(wraps=bot.get_seller_metrics.invoke)
        stockout_call = Mock(wraps=bot.get_out_of_stock_products.invoke)
        with (
            patch.object(bot, "llm", model),
            patch.object(bot, "_llm_key", "unit-test-key"),
            patch.object(
                bot,
                "get_client_sarvam_api_key",
                return_value="unit-test-key",
            ),
            patch.object(
                bot,
                "get_client_sarvam_api_keys",
                return_value=["unit-test-key"],
            ),
            patch.object(bot, "_rag_retriever", retriever),
            patch.object(bot, "get_seller_metrics", SimpleNamespace(invoke=metrics_call)),
            patch.object(bot, "get_out_of_stock_products", SimpleNamespace(invoke=stockout_call)),
        ):
            graph = bot.build_graph()
            config = {"configurable": {"thread_id": "proactive-diagnostic-test"}}
            first = graph.invoke(
                {"messages": [HumanMessage(content="Seller ID: SD-12345")]},
                config,
            )
            second = graph.invoke(
                {"messages": [HumanMessage(content="Orders are up this month.")]},
                config,
            )

        self.assertEqual(first["seller_id"], "SD-12345")
        self.assertIn("[pricing_or_mix]", first["diagnostic_context"])
        self.assertEqual(metrics_call.call_count, 1)
        self.assertEqual(stockout_call.call_count, 1)
        system_context = "\n".join(
            str(message.content)
            for message in model.seen_messages[0]
            if getattr(message, "type", None) == "system"
        )
        self.assertIn("[pricing_or_mix]", system_context)
        self.assertIn("Prioritise stockouts using historical orders.", system_context)
        self.assertIn("pricing discount average selling price product mix", retriever.query)
        self.assertNotIn("SD-12345", retriever.query)
        self.assertEqual(second["seller_metrics"], first["seller_metrics"])

    def test_proactive_context_prioritizes_three_seller_scenarios(self):
        from seller_dashboard.tools import get_seller_metrics, get_out_of_stock_products

        def diagnose(seller_id):
            metrics = get_seller_metrics.invoke({"seller_id": seller_id})
            current = metrics["this_month"]["out_of_stock_products"]
            previous = metrics["last_month"]["out_of_stock_products"]
            stockouts = get_out_of_stock_products.invoke({
                "seller_id": seller_id,
                "onlyNew": current > previous,
            }) if current else None
            return bot.build_diagnostic_context(metrics, stockouts)

        pricing = diagnose("SD-12345")
        self.assertIn("orders 300 to 310 (change 10; increased)", pricing)
        self.assertIn("ASP ₹500 to ₹400 (change -100; decreased)", pricing)
        self.assertLess(pricing.index("[pricing_or_mix]"), pricing.index("[inventory]"))
        self.assertIn("Cost, fees, and margin are unavailable", pricing)

        inventory = diagnose("SD-48213")
        self.assertIn("[cancellations]", inventory)
        self.assertIn("[inventory]", inventory)
        self.assertIn("Printed Cotton Kurti", inventory)
        self.assertIn("do not prove lost sales", inventory)

        cancellations = diagnose("SD-63190")
        self.assertIn("cancellation rate 6.0% to 19.0% (change 13.0 percentage points; increased)", cancellations)
        self.assertIn("[cancellations]", cancellations)
        self.assertIn("physical stock matches the Seller Panel", cancellations)

    def test_seller_id_resolution_only_accepts_explicit_or_bare_id(self):
        self.assertEqual(
            bot.seller_id_from_messages([
                HumanMessage(content="The current seller ID is SD-11111. What's the issue?")
            ]),
            "SD-11111",
        )
        self.assertEqual(
            bot.seller_id_from_messages([HumanMessage(content="52077")]),
            "SD-52077",
        )
        self.assertIsNone(
            bot.seller_id_from_messages([HumanMessage(content="Sales were 124000 this month")])
        )

    def test_recent_context_keeps_answers_and_omits_tool_traffic(self):
        messages = [
            HumanMessage(content="My cancellations increased."),
            AIMessage(content="Does your physical stock match the Seller Panel?"),
            HumanMessage(content="Mostly, but size variants can be wrong."),
            AIMessage(content="I will focus on the variant mismatch."),
            ToolMessage(content="internal tool result", tool_call_id="call-1"),
            AIMessage(
                content="",
                tool_calls=[{
                    "name": "get_seller_metrics",
                    "args": {},
                    "id": "call-1",
                    "type": "tool_call",
                }],
            ),
        ]

        context = bot.recent_conversation_context(messages)

        self.assertIn("Seller: My cancellations increased.", context)
        self.assertIn("Seller: Mostly, but size variants can be wrong.", context)
        self.assertIn("Assistant: I will focus on the variant mismatch.", context)
        self.assertNotIn("internal tool result", context)
        self.assertNotIn("get_seller_metrics", context)

    def test_rag_query_uses_recent_conversation_and_four_chunks(self):
        retriever = FakeRetriever()
        context = "Seller: Physical stock matches except two size variants."

        with patch.object(bot, "_rag_retriever", retriever):
            formatted = bot.generate_formatted_prompt(
                "Cancellations are still high.", context
            )

        self.assertIn("Physical stock matches except two size variants", retriever.query)
        self.assertIn("Cancellations are still high", retriever.query)
        self.assertEqual(retriever.k, 4)
        self.assertIn("Prioritise stockouts using historical orders", formatted)

    def test_rag_query_includes_prioritized_findings(self):
        retriever = FakeRetriever()
        diagnostic = "Seller ID: SD-12345. Sales ₹124000. [pricing_or_mix] ASP fell while orders increased."
        with patch.object(bot, "_rag_retriever", retriever):
            bot.generate_formatted_prompt("My price changed from ₹500 to ₹400", diagnostic_context=diagnostic)
        self.assertIn("pricing discount average selling price product mix", retriever.query)
        self.assertNotIn("SD-12345", retriever.query)
        self.assertNotIn("124000", retriever.query)
        self.assertNotIn("500", retriever.query)

    def test_rag_query_uses_sanitized_dialogue_and_topic_only(self):
        query = bot.build_rag_retrieval_query(
            "SD-12345 की sales ₹124000 हुईं और ASP ₹400 है",
            "Seller: price ₹500 से ₹400 की; orders 310 रहे।",
            "Seller: SD-12345; business category: Apparel. Observed: sales 150000 to 124000. [pricing_or_mix]",
        )
        self.assertIn("pricing discount average selling price product mix", query)
        self.assertIn("Apparel", query)
        self.assertNotIn("SD-12345", query)
        self.assertNotIn("124000", query)
        self.assertNotIn("₹500", query)

    def test_hindi_rag_query_expands_to_english_corpus_terms(self):
        query = expand_retrieval_query("इन्वेंटरी रीस्टॉक कब करूँ?")
        self.assertIn("inventory", query)
        self.assertIn("replenishment", query)
        self.assertIn("supplier lead time", query)

    def test_session_language_supports_hindi_english_and_hinglish(self):
        self.assertEqual(
            bot.detect_session_language([HumanMessage(content="मेरी बिक्री कम हुई है।")]),
            "hindi",
        )
        self.assertEqual(
            bot.detect_session_language([HumanMessage(content="My sales are declining.")]),
            "english",
        )
        self.assertEqual(
            bot.detect_session_language([HumanMessage(content="मेरी sales कम हो रही हैं")]),
            "hinglish",
        )

    def test_metric_direction_context_uses_latest_tool_values(self):
        metrics = {
            "last_month": {
                "sales": 150000,
                "orders": 300,
                "avg_selling_price": 500,
                "cancellation_rate_pct": 5.0,
            },
            "this_month": {
                "sales": 124000,
                "orders": 310,
                "avg_selling_price": 400,
                "cancellation_rate_pct": 19.0,
            },
        }
        message = ToolMessage(
            content=str(metrics),
            tool_call_id="metrics-1",
            name="get_seller_metrics",
        )

        context = bot.latest_metric_direction_context([message])

        self.assertIn("Orders: 300 last month, 310 this month; increased.", context)
        self.assertIn("Average selling price (ASP): 500 last month, 400 this month; decreased.", context)
        self.assertIn("Cancellation rate: 5.0 last month, 19.0 this month; increased.", context)
        self.assertIn("ASP is not profit or margin", context)

    def test_current_apparel_fixture_has_orders_up_and_asp_down(self):
        from seller_dashboard.tools import get_seller_metrics

        metrics = get_seller_metrics.invoke({"seller_id": "SD-12345"})
        message = ToolMessage(
            content=str(metrics),
            tool_call_id="sd11111-metrics",
            name="get_seller_metrics",
        )

        context = bot.latest_metric_direction_context([message])

        self.assertEqual(metrics["last_month"]["orders"], 300)
        self.assertEqual(metrics["this_month"]["orders"], 310)
        self.assertEqual(metrics["last_month"]["avg_selling_price"], 500)
        self.assertEqual(metrics["this_month"]["avg_selling_price"], 400)
        self.assertIn("Orders: 300 last month, 310 this month; increased.", context)
        self.assertIn("Average selling price (ASP): 500 last month, 400 this month; decreased.", context)

    def test_increasing_cancellation_fixture_is_grounded(self):
        from seller_dashboard.tools import get_seller_metrics

        metrics = get_seller_metrics.invoke({"seller_id": "SD-63190"})
        message = ToolMessage(
            content=str(metrics),
            tool_call_id="cancellation-metrics",
            name="get_seller_metrics",
        )
        context = bot.latest_metric_direction_context([message])

        self.assertIn("Cancellation rate: 6.0 last month, 19.0 this month; increased.", context)
        self.assertIn("Out-of-stock product count: 2 last month, 3 this month; increased.", context)

    def test_diagnostic_prompt_blocks_unsupported_margin_and_casual_address(self):
        self.assertIn("Never calculate or claim a margin", bot.SYSTEM_PROMPT)
        self.assertIn("Never assume or invent the seller's name or gender", bot.SYSTEM_PROMPT)
        self.assertIn("overfamiliar terms", bot.SYSTEM_PROMPT)
        self.assertIn("Before recommending any specific price change", bot.SYSTEM_PROMPT)
        self.assertIn("PROACTIVE CONSULTATION", bot.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
