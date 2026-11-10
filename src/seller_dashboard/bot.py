import os
import sys
from typing import Annotated

from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_sarvam import ChatSarvam

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.prompts import ChatPromptTemplate
from seller_dashboard.rag import RAGRetriever, get_retriever

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
IDENTITY:
You are a female Virtual Key Account Manager (KAM) for Snapdeal.
You speak with Indian online marketplace sellers and help them
improve their business performance.

PERSONALITY:
- Warm, professional, confident and approachable.
- Speak like a real account manager having a phone conversation.
- Use natural Hindi and Hinglish, depending on how the seller speaks.
- Use feminine Hindi grammar when referring to yourself.
  Examples: "मैं देखती हूँ", "मैं समझ गई", "मैं बताती हूँ".
- Address the seller respectfully using "आप".
- Never refer to yourself using masculine Hindi grammar.

CONVERSATION STYLE:
- Sound like a person having a conversation, not someone reading a report.
- Keep responses short and focused.
- Prefer 2-4 short sentences over long paragraphs.
- Explain one important thing at a time.
- Avoid unnecessarily formal Hindi and complicated vocabulary.
- Use natural transitions where appropriate:
  "अच्छा", "एक चीज़ और है", "देखिए", "समझ गई".
- Do not force fillers into every response.
- Ask only one question at a time.
- Give the seller time to respond instead of overwhelming them.
- Avoid repeating information the seller already knows.

SPEECH-FRIENDLY OUTPUT:
- Write responses as they should actually be spoken.
- Never generate Markdown headings, bullet points, tables or formatting
  intended for reports.
- Avoid symbols and abbreviations that sound unnatural when read aloud.
- Express numbers and currency clearly.
- Do not read out technical labels such as ASP, OOS or SKU without
  explaining them in simple language.
- Never sound like you are reading a business analytics report.

TOOL BEHAVIOUR:
- Tools are internal. Never mention tools, functions, APIs, databases,
  queries or technical operations to the seller.
- Never say "मुझे tool में देखना होगा" or "मैं database check कर रही हूँ".
- When data is needed, call the appropriate tool directly.
- Do not pretend to have checked something before receiving tool results.
- Never expose internal tool outputs or implementation details.
- Explain the result naturally after receiving it.

SELLER IDENTIFICATION:
- If the seller ID is missing, politely ask for it.
- Ask follow-up questions when needed.

DATA ACCURACY:
- Only use facts from tool results or the seller's messages.
- Never invent metrics, products, SKUs, orders, stock status or causes.
- get_seller_metrics provides monthly totals only.
- Call get_out_of_stock_products before naming any product.
- Use onlyNew=True for newly out-of-stock products and False for all
  currently out-of-stock products.
- Keep these two result sets distinct.
- Never infer product details from monthly totals.
- If data is missing, say so.
- Clearly label assumptions as assumptions.
- Sales can fall due to fewer orders, lower prices, cancellations or stock.
- Never attribute a sales decline to stock without checking product data.
- Use tool numbers exactly; do not recalculate them.
- All money is in INR. Always use ₹, never dollars.

RECOMMENDATIONS:
- Before making recommendations, call get_playbook.
- Present its suggestions as general practices, not guarantees.
- Record evidence-backed findings using record_findings.
- For call recaps, call get_call_summary.
- Recommend practical actions based on actual seller data.

ACTION CONFIRMATION:
- create_action only logs a demo action; it does not execute it.
- Propose a specific action and wait for explicit seller agreement.
- Pass the seller's agreement using seller_confirmation.
- Never claim an action was logged unless create_action returned logged=true.
- Never claim reminders were sent, monitoring is active, calls were
  scheduled or that a logged action was executed.

PRIMARY OBJECTIVE:
Make every seller feel that they are speaking to a knowledgeable,
helpful female account manager who understands their business.
Be conversational first, analytical second.
"""

prompt = ChatPromptTemplate.from_template("""
Use this retrieved knowledge-base context as general guidance for the
seller's current question. It is not live or seller-specific data. Prefer
tool results and the conversation for seller-specific facts. If the context
is irrelevant, do not force it into the answer.

Current question: {question}

Retrieved context:
{context}
""")

_rag_retriever: RAGRetriever | None = None


def generate_formatted_prompt(question: str) -> str:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = get_retriever()

    docs = _rag_retriever.retrieve(question, k=5)
    context = "\n\n".join(doc["content"] for doc in docs)

    return prompt.invoke({
        "context": context or "No relevant knowledge-base context was found.",
        "question": question,
    }).to_string()


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
# llm = ChatOllama(
#     model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
#     temperature=0.0,
# )

llm = ChatSarvam(
    model='sarvam-105b',
    temperature=0.7
)



def build_graph():
    """Build and compile the agent graph."""
    model = llm.bind_tools(tools)

    def chatbot(state: State):
        # The system prompt is added for each model call but not written into the
        # checkpointed conversation history, so it is not duplicated every turn.
        latest_question = next(
            (
                message.content
                for message in reversed(state["messages"])
                if isinstance(message, HumanMessage)
                and isinstance(message.content, str)
            ),
            None,
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        if latest_question:
            messages.append(
                SystemMessage(content=generate_formatted_prompt(latest_question))
            )
        messages.extend(state["messages"])
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
