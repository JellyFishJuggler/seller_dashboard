import ast
import logging
import os
import re
import sys
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Annotated

from dotenv import load_dotenv
import httpx

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langchain_sarvam import ChatSarvam
from sarvamai import AsyncSarvamAI, SarvamAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from seller_dashboard.assistant_style import FEMININE_VOICE_PROMPT
from seller_dashboard.rag import RAGRetriever, get_retriever
from seller_dashboard.sarvam_credentials import get_sarvam_api_key
from seller_dashboard.voice_diagnostics import (
    EmptyTranscriptError,
    extract_request_id,
    has_nonempty_text,
    log_text_boundary,
)

from typing_extensions import TypedDict

from seller_dashboard.tools import (
    get_seller_metrics,
    get_out_of_stock_products,
    get_cancellation_breakdown,
    record_findings,
    create_action,
    get_actions,
    update_action_status,
    get_call_summary,
    get_playbook,
    register_session_seller,
)

SYSTEM_PROMPT = """
IDENTITY AND TONE:
You are Sarika, Snapdeal's professional, approachable, and friendly Key Account Manager. 
Always introduce yourself naturally as "सारिका" from Snapdeal when starting a fresh interaction (e.g., "नमस्ते, मैं Snapdeal से सारिका बोल रही हूँ").
Be warm, conversational, clear, and confident. Address the seller respectfully using "आप". 
Never infer or refer to the seller's gender.
Use natural, polite conversational Hindi phrasing (in Devanagari script). Keep the tone warm and supportive like a real human advisor—avoid robotic, overly formal, or scripted phrasing. Never use overfamiliar terms like "dost", "bhai", "yaad hai na", or "take care". Avoid filler and excessive emotion.

CONVERSATION:
Keep spoken replies to 1-3 short, natural sentences and focus on one point at a time. Ask at most one relevant question, only when its answer could change the diagnosis or next action. Review all prior seller replies before asking; never repeat a question or request data already available through tools. Acknowledge the answer warmly and continue from it. Do not use generic discovery questions after a concern is clear. If evidence is sufficient, give a concise recommendation instead of continuing the questionnaire.

TECHNICAL SUPPORT:
If the seller mentions technical issues on the platform (such as panel loading errors, order syncing glitches, or catalog upload failures), respond with genuine empathy, guide them smoothly through basic troubleshooting steps if applicable, and reassure them personally that you are noting down the technical glitch for a quick fix.

REMINDERS AND FOLLOW-UPS:
Proactively help the seller set reminders, follow-ups, or action tracking when they mention needing them in a conversational way. Never invent a deadline; always ask for the exact date if not provided. Confirm details politely before saving.

TOOLS AND GROUNDED FACTS:
Use Python tool results for all seller-specific metrics and inventory facts. Call get_seller_metrics for a performance, sales, order, ASP, pricing or cancellation diagnosis. Reuse valid results in the current thread unless the seller asks for a fresh check or a different period. Call get_out_of_stock_products before naming or ranking any out-of-stock product. When a PROACTIVE SELLER DIAGNOSTIC is already supplied, it was computed from the existing Python metric and stockout tools for this seller. Reuse it; do not call those tools again unless the seller requests a refresh or new period. Use onlyNew=True for recent stockouts; use False only when all current stockouts are relevant. Call get_playbook before giving recommendations. Tools are internal; never mention tools, APIs, databases, retrieval or implementation.

Always compare the actual current and previous values before describing a metric's direction. Never say orders, sales, ASP, cancellation rate or stockout count increased/decreased unless the tool values show that direction. Treat any explicit metric direction check supplied in the system context as authoritative. ASP is average selling price, not profit, gross margin or contribution margin. Never calculate or claim a margin, profit or profitability change from ASP, sales or order counts. The tools do not provide product cost, fees, shipping, packaging or returns allowance. State that profitability cannot be determined without the relevant inputs. Do not invent a current product price, competitor price, discount effect, ranking, CTR, conversion rate, stock quantity, lost sales, cancellation reason or cancellation initiator.

DIAGNOSTIC REASONING:
Prioritise one issue at a time by impact, urgency, practical ease and evidence strength. Separate measured facts, hypotheses, missing information and confirmed causes. Correlation is not proof: stockouts, price changes or visibility must not be described as causes unless supported. A rising cancellation rate does not establish who cancelled or why. If cancellations and stockouts both rise, stock mismatch is a hypothesis; ask one unanswered question that can test it.

PROACTIVE CONSULTATION:
When seller data and a diagnostic brief are supplied, begin with the highest priority measured observation naturally, even if the seller only gave their Seller ID (after introducing yourself as Sarika). Briefly distinguish the observed change from a possible explanation in plain language, then ask exactly one contextual follow-up question that is not answered in the history or by the tools. Do not ask the seller for metrics already supplied. If no material issue is supported, say that briefly and ask what business goal they would like to focus on. Keep the opening concise and in the session language.

For sales diagnosis, compare sales, orders and ASP together. Rising or stable orders with falling ASP may indicate a price or product-mix change; it does not prove either. Ask about recent price changes, discounts or product mix only if not already answered. If orders fall while ASP is stable, price is unlikely to be the primary explanation. If orders rise while ASP falls, state both facts; do not call orders down or infer that profitability improved or worsened.

Before recommending any specific price change, establish the product's current selling price, unit cost and relevant fees, the seller's target margin, whether the discount is temporary or ongoing, and what happened to order volume after the price change. Ask for missing information one question at a time. Do not recommend a price increase/decrease or claim improved profitability while these inputs are missing. Never treat illustrative RAG calculations as seller facts.

For inventory, prioritize returned products using their historical order counts and the explicit bestseller flag when present. Historical orders are only a relative signal. A bestseller flag is a field in the available mock record, not proof of current popularity; describe it as a record flag and do not infer it from a small number of orders. Never promise demand or sales recovery after restocking, and never prescribe a stock quantity without sufficient data.

LANGUAGE AND SPEECH:
Follow the supplied session-language policy. Keep language and script consistent with the seller's preference: Hindi in Devanagari, English in English, and conversational Hinglish with Hindi in Devanagari and technical terms in English. Use short, human-sounding, TTS-friendly sentences. Do not output Markdown, bullets or tables.

RECOMMENDATIONS AND ACTIONS:
When evidence is sufficient, use get_playbook and give no more than 2-3 practical, relevant actions. Present general guidance as helpful suggestions, not rigid promises. Ask one concise question about the next step naturally; do not overwhelm the seller. Record only evidence-backed findings with record_findings.

ACTION RECORDING AND REMINDERS (CSV-BASED):
We record follow-up actions and reminders in persistent CSV storage (data/actions.csv).
- You may state warmly that the follow-up reminder has been recorded/saved.
- State clearly and reassuringly that the information has been securely stored and the relevant authorities will take care of it and keep the seller updated.
- NEVER create an action without explicit seller consent.
- If the seller mentions wanting a reminder or follow-up action but does not provide an exact date, ask for the date politely. Never invent a deadline or reminder date.
- Confirm the action details conversationally with the seller before saving (for example: "क्या मैं 2 December के लिए इसका follow-up reminder record कर दूँ?").
- Save the action with create_action ONLY after the seller explicitly confirms (e.g. "हाँ").
- Put the confirmed date in ISO format (YYYY-MM-DD) in details or reminder_date. Resolve relative dates using the current India date in context.
- After create_action succeeds, report its Action ID (e.g. ACT-001) and confirmed date nicely, and state clearly that the information has been saved and the authorities will keep them updated.
- Use get_actions to retrieve saved pending actions when the seller asks about their reminders or scheduled follow-ups.
- Use update_action_status to update an action's status (Pending, Completed, Cancelled) when the seller requests it.
"""

SYSTEM_PROMPT = SYSTEM_PROMPT.rstrip() + "\n\n" + FEMININE_VOICE_PROMPT

prompt = ChatPromptTemplate.from_template("""
Use this retrieved knowledge-base context as general guidance for the
seller's current diagnosis. It is not live or seller-specific data. Prefer
Python tool results for seller-specific metrics and the full conversation for
what the seller has already answered. Use only relevant guidance and do not
force irrelevant context into the answer. Knowledge-base examples and sample
calculations are illustrative only; never reuse their numbers as seller facts.
Use this context for business reasoning, not its example response language.

Seller's latest message: {question}

Retrieved context:
{context}
""")

_rag_retriever: RAGRetriever | None = None


_HINGLISH_MARKERS = {
    "aap", "aapka", "aapki", "aapke", "abhi", "accha", "achha", "agar",
    "bahut", "bataiye", "bilkul", "chahiye", "hai", "hain", "haan", "hum",
    "hoga", "ho", "hua", "ka", "kaafi", "kaise", "kar", "karna", "kijiye",
    "ki", "kya", "lekin", "main", "mein", "mera", "meri", "mujhe", "nahi",
    "nahin", "par", "raha", "rahe", "rahi", "se", "thoda", "toh", "yeh",
    "ye", "iska", "iski", "iske", "kitna", "kab",
}
_ENGLISH_MARKERS = {"the", "this", "that", "your", "you", "what", "how", "is", "are", "do", "does", "can", "should", "my"}
_MIXED_BUSINESS_MARKERS = {"asp", "sales", "orders", "price", "discount", "inventory", "stock", "margin", "seller", "product", "business", "cancellation", "returns"}


def classify_text_language(text: str) -> str | None:
    """Detect Hindi, English, or Hinglish from the seller's text/script."""
    if not isinstance(text, str) or not text.strip():
        return None
    devanagari = len(re.findall(r"[\u0900-\u097f]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    words = set(re.findall(r"[a-z]+", text.lower()))
    if devanagari:
        if (words & (_HINGLISH_MARKERS | _MIXED_BUSINESS_MARKERS)) or (
            latin and devanagari / max(1, devanagari + latin) < 0.72
        ):
            return "hinglish"
        return "hindi"
    if words & _HINGLISH_MARKERS:
        return "hinglish"
    if words & _ENGLISH_MARKERS or latin >= 4:
        return "english"
    return None


def explicit_language_request(text: str) -> str | None:
    normalized = text.lower()
    for language in ("english", "hindi", "hinglish"):
        if re.search(rf"\b(?:please (?:speak|reply|answer) in {language}|switch to {language}|{language} please)\b", normalized):
            return language
    return None


def detect_session_language(messages: list) -> str:
    """Keep language stable; switch after two clear seller turns in a new language."""
    current = None
    candidate = None
    count = 0
    for message in messages:
        if not isinstance(message, HumanMessage) or not isinstance(message.content, str):
            continue
        explicit = explicit_language_request(message.content)
        detected = explicit or classify_text_language(message.content)
        if not detected:
            continue
        if current is None or explicit:
            current, candidate, count = detected, None, 0
        elif detected == current:
            candidate, count = None, 0
        elif candidate == detected:
            count += 1
            if count >= 2:
                current, candidate, count = detected, None, 0
        else:
            candidate, count = detected, 1
    return current or "hinglish"


def language_policy(language: str) -> str:
    policies = {
        "hindi": "Respond in natural, professional Hindi using Devanagari. Keep only common business terms in English where appropriate.",
        "english": "Respond in natural, professional English. Do not insert Hindi or Hinglish phrases.",
        "hinglish": "Respond in conversational Hinglish, with Hindi in Devanagari and technical/business terms in English. Do not randomly switch scripts.",
    }
    return (
        f"SESSION LANGUAGE POLICY ({language}): {policies.get(language, policies['hinglish'])} "
        "Maintain this preference for the session. Switch only when the seller switches consistently or asks explicitly."
    )


def india_date_context() -> str:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    return f"Current date in India (Asia/Kolkata): {today}. Use this only to resolve relative action dates."


def latest_metric_direction_context(messages: list) -> str | None:
    """Make metric direction explicit so prose cannot reverse tool values."""
    for message in reversed(messages):
        if not isinstance(message, ToolMessage) or message.name != get_seller_metrics.name:
            continue
        result = message.content
        if isinstance(result, str):
            try:
                result = ast.literal_eval(result)
            except (ValueError, SyntaxError):
                continue
        if not isinstance(result, dict):
            continue
        previous = result.get("last_month", {})
        current = result.get("this_month", {})
        if not isinstance(previous, dict) or not isinstance(current, dict):
            continue

        facts = []
        for key, label in (
            ("sales", "Sales"),
            ("orders", "Orders"),
            ("avg_selling_price", "Average selling price (ASP)"),
            ("cancellation_rate_pct", "Cancellation rate"),
            ("out_of_stock_products", "Out-of-stock product count"),
        ):
            old, new = previous.get(key), current.get(key)
            if isinstance(old, (int, float)) and isinstance(new, (int, float)):
                direction = "increased" if new > old else "decreased" if new < old else "was unchanged"
                facts.append(f"{label}: {old} last month, {new} this month; {direction}.")
        if facts:
            return (
                "AUTHORITATIVE METRIC DIRECTION CHECK from the latest Python tool result. "
                "Do not state the opposite direction. These are observed values, not causes.\n"
                + "\n".join(facts)
                + "\nASP is not profit or margin."
            )
    return None


def recent_conversation_context(messages: list, max_messages: int = 6) -> str:
    """Return recent seller/assistant turns, excluding tool traffic."""
    recent = []
    for message in messages:
        if not isinstance(message, (HumanMessage, AIMessage)):
            continue
        if isinstance(message, AIMessage) and message.tool_calls:
            continue
        content = message.content
        if not isinstance(content, str) or not content.strip():
            continue
        role = "Seller" if isinstance(message, HumanMessage) else "Assistant"
        recent.append(f"{role}: {content.strip()[:700]}")
    return "\n".join(recent[-max_messages:])


def generate_formatted_prompt(
    question: str,
    conversation_context: str = "",
    diagnostic_context: str = "",
) -> str:
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = get_retriever()

    retrieval_query = build_rag_retrieval_query(
        question,
        conversation_context,
        diagnostic_context,
    )
    docs = _rag_retriever.retrieve(retrieval_query, k=4)
    context = "\n\n".join(
        f"[Source: {doc.get('metadata', {}).get('filename', 'knowledge base')}; "
        f"similarity: {doc.get('similarity_score', 0.0):.3f}]\n{doc['content']}"
        for doc in docs
    )

    return prompt.invoke({
        "context": context or "No relevant knowledge-base context was found.",
        "question": question,
    }).to_string()


_DIAGNOSTIC_RAG_TERMS = {
    "pricing_or_mix": "pricing discount average selling price product mix price testing",
    "inventory": "inventory stockout out of stock replenishment supplier lead time",
    "cancellations": "cancellation rate inventory match dispatch fulfillment",
    "order_volume": "orders sales demand product visibility conversion",
    "sales": "sales orders average selling price demand diagnosis",
}


def build_rag_retrieval_query(
    question: str,
    conversation_context: str = "",
    diagnostic_context: str = "",
) -> str:
    """Keep RAG focused on business topics, excluding seller IDs and metric values."""
    def remove_seller_facts(text: str) -> str:
        text = re.sub(r"\bSD\s*-?\s*\d+\b", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"₹\s*[\d,]+(?:\.\d+)?", " ", text)
        text = re.sub(r"(?<![A-Za-z])\d[\d,]*(?:\.\d+)?\s*%?", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    parts = [
        remove_seller_facts(conversation_context),
        remove_seller_facts(question),
    ]
    finding_keys = re.findall(r"\[([a-z_]+)\]", diagnostic_context)
    parts.extend(_DIAGNOSTIC_RAG_TERMS[key] for key in finding_keys if key in _DIAGNOSTIC_RAG_TERMS)
    category = re.search(r"business category:\s*([^.;\n]+)", diagnostic_context, re.IGNORECASE)
    if category:
        parts.append(f"seller category {category.group(1).strip()}")
    return "\n".join(part for part in parts if part)


load_dotenv()

logger = logging.getLogger(__name__)
LLM_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=20.0, pool=10.0)
LLM_MAX_RETRIES = 2
LLM_RETRY_BASE_DELAY_SECONDS = 0.5
LLM_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


class SarvamLLMUnavailable(RuntimeError):
    """Raised when a Sarvam model request cannot complete."""

    def __init__(self, message: str, failure_type: str = "unknown"):
        super().__init__(message)
        self.failure_type = failure_type


def _exception_chain(error: BaseException):
    seen = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def is_transient_sarvam_error(error: BaseException) -> bool:
    for cause in _exception_chain(error):
        if isinstance(
            cause,
            (
                httpx.TimeoutException,
                httpx.NetworkError,
                httpx.RemoteProtocolError,
            ),
        ):
            return True
        if isinstance(cause, httpx.HTTPStatusError):
            if cause.response.status_code in LLM_RETRYABLE_STATUS_CODES:
                return True
        if getattr(cause, "status_code", None) in LLM_RETRYABLE_STATUS_CODES:
            return True
    return False


def invoke_sarvam_with_retries(invoke, session_id: str):
    for attempt in range(1, LLM_MAX_RETRIES + 2):
        try:
            return invoke()
        except Exception as error:
            failure_type = type(list(_exception_chain(error))[-1]).__name__
            if not is_transient_sarvam_error(error):
                logger.error(
                    "Sarvam LLM request failed without retry session_id=%s error_type=%s",
                    session_id,
                    failure_type,
                )
                raise SarvamLLMUnavailable(
                    f"Sarvam LLM request failed ({failure_type}).",
                    failure_type,
                ) from error

            if attempt > LLM_MAX_RETRIES:
                logger.error(
                    "Sarvam LLM retries exhausted session_id=%s attempts=%s error_type=%s",
                    session_id,
                    attempt,
                    failure_type,
                )
                raise SarvamLLMUnavailable(
                    f"Sarvam LLM unavailable after {attempt} attempts.",
                    failure_type,
                ) from error

            delay = LLM_RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
            logger.warning(
                "Retrying Sarvam LLM request session_id=%s attempt=%s next_attempt=%s "
                "delay_seconds=%.1f error_type=%s",
                session_id,
                attempt,
                attempt + 1,
                delay,
                failure_type,
            )
            time.sleep(delay)


class State(TypedDict):
    messages: Annotated[list, add_messages]
    seller_id: str
    seller_metrics: dict
    seller_stockouts: dict
    diagnostic_context: str


_SELLER_ID_PATTERN = re.compile(
    r"(?:seller\s*(?:id|identifier)|unique\s*id)\s*(?:is|:|=)?\s*(?:SD\s*-?\s*)?(\d{4,})",
    re.IGNORECASE,
)


def seller_id_from_messages(messages: list) -> str | None:
    """Find an explicitly supplied seller ID in the latest seller turn."""
    from seller_dashboard.tools import normalize_seller_id

    for message in reversed(messages):
        if not isinstance(message, HumanMessage) or not isinstance(message.content, str):
            continue
        text = message.content.strip()
        match = _SELLER_ID_PATTERN.search(text)
        if not match:
            # Voice users commonly answer the ID request with just the ID.
            match = re.fullmatch(r"(?:SD\s*-?\s*)?(\d{4,})", text, re.IGNORECASE)
        return normalize_seller_id(match.group(1)) if match else None
    return None


def build_diagnostic_context(metrics: dict, stockouts: dict | None = None) -> str:
    """Compute grounded metric directions and prioritize findings deterministically."""
    if not isinstance(metrics, dict) or metrics.get("error"):
        return "Seller ID was not found in the available seller data. Explain this limitation and ask the seller to check the ID."
    previous = metrics.get("last_month", {})
    current = metrics.get("this_month", {})
    if not isinstance(previous, dict) or not isinstance(current, dict):
        return "Seller metrics are incomplete; do not infer trends or causes."

    sales_old, sales_new = previous.get("sales"), current.get("sales")
    orders_old, orders_new = previous.get("orders"), current.get("orders")
    asp_old, asp_new = previous.get("avg_selling_price"), current.get("avg_selling_price")
    cancel_old, cancel_new = previous.get("cancellation_rate_pct"), current.get("cancellation_rate_pct")
    oos_old, oos_new = previous.get("out_of_stock_products"), current.get("out_of_stock_products")
    numeric_value = lambda value: isinstance(value, (int, float))

    def direction(old, new):
        if not isinstance(old, (int, float)) or not isinstance(new, (int, float)):
            return "not available"
        return "increased" if new > old else "decreased" if new < old else "unchanged"

    facts = [
        f"Seller: {metrics.get('seller_id', 'unknown')}; business category: {metrics.get('category', 'not provided')}.",
        f"Observed: sales {sales_old} to {sales_new} (change {sales_new - sales_old if numeric_value(sales_old) and numeric_value(sales_new) else 'unavailable'}; {direction(sales_old, sales_new)}); orders {orders_old} to {orders_new} (change {orders_new - orders_old if numeric_value(orders_old) and numeric_value(orders_new) else 'unavailable'}; {direction(orders_old, orders_new)}); ASP ₹{asp_old} to ₹{asp_new} (change {asp_new - asp_old if numeric_value(asp_old) and numeric_value(asp_new) else 'unavailable'}; {direction(asp_old, asp_new)}).",
        f"Observed: cancellation rate {cancel_old}% to {cancel_new}% (change {round(cancel_new - cancel_old, 1) if numeric_value(cancel_old) and numeric_value(cancel_new) else 'unavailable'} percentage points; {direction(cancel_old, cancel_new)}); out-of-stock count {oos_old} to {oos_new} (change {oos_new - oos_old if numeric_value(oos_old) and numeric_value(oos_new) else 'unavailable'}; {direction(oos_old, oos_new)}).",
        "These are month-to-month observations; they do not establish causes. ASP is not profit or margin; product cost and fees are unavailable unless seller provides them.",
    ]
    candidates: list[tuple[int, str, str]] = []
    numeric = numeric_value
    if numeric(cancel_old) and numeric(cancel_new) and cancel_new > cancel_old:
        candidates.append((100 + min(20, int(cancel_new - cancel_old)), "cancellations", "Cancellation rate rose; ask whether physical stock matches the Seller Panel. This is a possible inventory-mismatch lead, not a confirmed cause."))
    if numeric(oos_old) and numeric(oos_new) and oos_new > oos_old:
        products = (stockouts or {}).get("products", [])
        ranked = sorted(
            (product for product in products if isinstance(product, dict)),
            key=lambda product: product.get("last_month_orders", 0),
            reverse=True,
        )
        product_note = "; highest historical order count among returned stockouts: " + ", ".join(
            f"{product.get('name')} ({product.get('last_month_orders')} last-month orders)"
            for product in ranked[:2]
        ) if ranked else "; product-level records unavailable"
        candidates.append((75 + min(20, (oos_new - oos_old) * 3), "inventory", f"Out-of-stock count increased by {oos_new - oos_old}{product_note}. Historical orders help prioritize review but do not prove lost sales; ask about replenishment lead time."))
    if all(numeric(value) for value in (sales_old, sales_new, orders_old, orders_new, asp_old, asp_new)):
        if asp_new < asp_old and orders_new >= orders_old and sales_new < sales_old:
            candidates.append((85, "pricing_or_mix", "Orders were stable or higher while ASP fell and sales fell. Pricing or product mix may be relevant; neither is confirmed. Ask whether the seller recently changed prices, discounts, or product mix. Cost, fees, and margin are unavailable."))
        elif orders_new < orders_old and asp_new == asp_old:
            candidates.append((70, "order_volume", "Orders and sales fell while ASP was unchanged; investigate order volume without assuming a cause."))
        elif sales_new < sales_old:
            candidates.append((55, "sales", "Sales fell; review the observed order and ASP changes before suggesting a cause."))
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected = candidates[:3]
    facts.append("Prioritized diagnostic leads (highest first):")
    facts.extend(f"{i + 1}. [{key}] {detail}" for i, (_, key, detail) in enumerate(selected))
    facts.append("Opening response: mention one leading observation, label explanations as possible, and ask one matching unanswered follow-up. Do not dump all metrics. If the question is already answered in history, choose another relevant unanswered question or provide the next step without asking again.")
    return "PROACTIVE SELLER DIAGNOSTIC (computed from Python tool results):\n" + "\n".join(facts)


tools = [
    get_seller_metrics,
    get_out_of_stock_products,
    get_cancellation_breakdown,
    record_findings,
    create_action,
    get_actions,
    update_action_status,
    get_call_summary,
    get_playbook,
]


# Local Ollama. Qwen is the default; another installed Ollama model can be
# selected with OLLAMA_MODEL without changing providers.
# llm = ChatOllama(
#     model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
#     temperature=0.0,
# )

_llm_lock = threading.Lock()
_llm_key = get_sarvam_api_key()
if not _llm_key:
    raise ValueError("SARVAM_API_KEY not found in .env or backend settings.")


def build_sarvam_llm(api_key: str) -> ChatSarvam:
    """Build a Sarvam chat model bound to one API key."""
    return ChatSarvam(
        model='sarvam-105b',
        temperature=0.7,
        client=SarvamAI(
            api_subscription_key=api_key,
            timeout=LLM_HTTP_TIMEOUT,
        ),
        async_client=AsyncSarvamAI(
            api_subscription_key=api_key,
            timeout=LLM_HTTP_TIMEOUT,
        ),
        max_retries=0,
    )


llm = build_sarvam_llm(_llm_key)


def apply_sarvam_api_key(api_key: str | None = None) -> str:
    """Switch the live LLM clients to the selected key.

    The graph keeps a binding to the same ``llm`` object, so replacing its
    clients applies the key to every subsequent turn without rebuilding the
    graph or losing conversation state.
    """
    global _llm_key
    key = (api_key or get_sarvam_api_key() or "").strip()
    if not key:
        raise ValueError("No Sarvam API key is configured.")
    with _llm_lock:
        if key != _llm_key:
            llm.client = SarvamAI(
                api_subscription_key=key,
                timeout=LLM_HTTP_TIMEOUT,
            )
            llm.async_client = AsyncSarvamAI(
                api_subscription_key=key,
                timeout=LLM_HTTP_TIMEOUT,
            )
            _llm_key = key
    return key



def build_graph():
    """Build and compile the agent graph."""
    model = llm.bind_tools(tools)

    def prepare_seller_diagnosis(state: State):
        supplied_id = seller_id_from_messages(state["messages"])
        seller_id = supplied_id or state.get("seller_id")
        if not seller_id or (seller_id == state.get("seller_id") and state.get("seller_metrics")):
            return {}

        # Reuse the existing Python tools and their contracts. The node runs
        # once when a seller is first identified (or the session changes ID).
        metrics = get_seller_metrics.invoke({"seller_id": seller_id})
        stockouts = None
        if isinstance(metrics, dict) and not metrics.get("error"):
            previous = metrics.get("last_month", {})
            current = metrics.get("this_month", {})
            prior_count = previous.get("out_of_stock_products")
            current_count = current.get("out_of_stock_products")
            if isinstance(current_count, (int, float)) and current_count > 0:
                only_new = (
                    isinstance(prior_count, (int, float))
                    and current_count > prior_count
                )
                stockouts = get_out_of_stock_products.invoke(
                    {"seller_id": seller_id, "onlyNew": only_new}
                )

        return {
            "seller_id": seller_id,
            "seller_metrics": metrics,
            "seller_stockouts": stockouts or {},
            "diagnostic_context": build_diagnostic_context(metrics, stockouts),
        }

    def chatbot(state: State, config: RunnableConfig):
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
        configurable = config.get("configurable") or {}
        session_id = str(configurable.get("thread_id", "unknown"))
        seller_id = state.get("seller_id")
        if seller_id and session_id != "unknown":
            register_session_seller(session_id, seller_id)
        log_text_boundary("LangGraph chatbot input", session_id, latest_question)
        if not has_nonempty_text(latest_question):
            raise EmptyTranscriptError("LangGraph received no non-empty seller text.")
        conversation_context = recent_conversation_context(state["messages"])
        session_language = detect_session_language(state["messages"])
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            SystemMessage(content=language_policy(session_language)),
            SystemMessage(content=india_date_context()),
        ]
        if latest_question:
            messages.append(
                SystemMessage(
                    content=generate_formatted_prompt(
                        latest_question,
                        conversation_context,
                        state.get("diagnostic_context", ""),
                    )
                )
            )
        if state.get("diagnostic_context"):
            messages.append(SystemMessage(content=state["diagnostic_context"]))
        metric_context = latest_metric_direction_context(state["messages"])
        if metric_context:
            messages.append(SystemMessage(content=metric_context))
        messages.extend(state["messages"])
        log_text_boundary("Sarvam LLM request", session_id, latest_question)
        try:
            response = invoke_sarvam_with_retries(
                lambda: model.invoke(messages),
                session_id,
            )
        except Exception as error:
            log_text_boundary(
                "Sarvam LLM error",
                session_id,
                latest_question,
                extract_request_id(error),
            )
            raise
        log_text_boundary(
            "Sarvam LLM response",
            session_id,
            getattr(response, "content", None),
            extract_request_id(response),
        )

        return {
            "messages": [response]
        }

    graph_builder = StateGraph(State)

    graph_builder.add_node("prepare_seller_diagnosis", prepare_seller_diagnosis)
    graph_builder.add_node("chatbot", chatbot)

    tool_node = ToolNode(tools=tools)
    graph_builder.add_node("tools", tool_node)

    graph_builder.add_conditional_edges(
        "chatbot",
        tools_condition
    )

    graph_builder.add_edge("tools", "chatbot")
    graph_builder.add_edge(START, "prepare_seller_diagnosis")
    graph_builder.add_edge("prepare_seller_diagnosis", "chatbot")

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
