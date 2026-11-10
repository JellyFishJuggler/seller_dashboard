import os
import sys
from typing import Annotated

from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from typing_extensions import TypedDict

from seller_dashboard.tools import (
    get_seller_metrics,
    get_out_of_stock_products,
    record_findings,
    create_action,
    get_call_summary,
    get_playbook,
)

SYSTEM_PROMPT = """
You are a Virtual KAM for a Snapdeal seller demo. Be conversational, concise and
helpful.

RULES:
- If the seller ID is missing, ask for it. Ask follow-up questions when needed.
- Call tools to get data. Reading data needs no permission: never ask "should I
  check?" - call the tool now.
- NEVER say you will call a tool. Either call it in this response or give the
  answer.
- Only use facts from tool results or the seller's messages. Never invent
  metrics, products, SKUs, orders, stock status or causes.
- get_seller_metrics is monthly totals only; it has no product details. Call
  get_out_of_stock_products (onlyNew=True for new stock-outs, False for all)
  before naming any product.
- Keep onlyNew=True and onlyNew=False results distinct. Never infer product
  details from totals.
- If data is missing, say so. Label assumptions as assumptions.
- Sales can fall due to fewer orders, lower price, cancellations or stock. A
  higher out-of-stock total is not product evidence: call
  get_out_of_stock_products before linking the sales drop to stock.
- Use tool numbers exactly; do not recalculate them.
- Money is INR: always show ₹ (for example ₹1,35,000), never dollars, never
  convert.
- Before recommendations, use get_playbook and present its tips as general
  practices, not guarantees.
- Record evidence-backed findings with record_findings.
- Recaps: call get_call_summary.
- create_action only logs a demo action; it never executes anything. Propose a
  specific action and wait for explicit seller agreement. Then pass their
  agreement in seller_confirmation.
- Never say an action was logged unless create_action returned logged=true.
  Never claim reminders were sent, monitoring is active, calls were scheduled,
  or that a logged action can be executed. Never claim a tool performed an
  operation it only logged.
"""


load_dotenv()


class State(TypedDict):
    messages: Annotated[list, add_messages]


tools = [
    get_seller_metrics,
    get_out_of_stock_products,
    record_findings,
    create_action,
    get_call_summary,
    get_playbook,
]


# Local Ollama. Qwen is the default; another installed Ollama model can be
# selected with OLLAMA_MODEL without changing providers.
llm = ChatOllama(
    model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
    temperature=0.0,
)


def build_graph():
    """Build and compile the agent graph."""
    model = llm.bind_tools(tools)

    def chatbot(state: State):
        # The system prompt is added for each model call but not written into the
        # checkpointed conversation history, so it is not duplicated every turn.
        messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        response = model.invoke(messages)

        return {
            "messages": [response]
        }

    graph_builder = StateGraph(State)

    graph_builder.add_node("chatbot", chatbot)

    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition
    )

    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "chatbot")

    return graph_builder.compile(checkpointer=MemorySaver())


graph = build_graph()


def main() -> None:
    # The rupee symbol is not representable in some Windows console code pages.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    thread_id = os.getenv("THREAD_ID", "demo-session-1")
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    print("Snapdeal Virtual KAM (demo). Type 'q' to quit.")

    while True:
        try:
            user_input = input("\nYou: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input.strip().lower() in {"q", "quit", "exit"}:
            break

        if not user_input.strip():
            continue

        events = graph.stream(
            {
                "messages": [
                    HumanMessage(content=user_input)
                ]
            },
            config,
            stream_mode="values"
        )

        for event in events:
            messages = event.get("messages", [])

            if not messages:
                continue

            last_message = messages[-1]

            if (
                isinstance(last_message, AIMessage)
                and not last_message.tool_calls
                and last_message.content
            ):
                print(f"\nKAM: {last_message.content}")


if __name__ == "__main__":
    main()
