import csv
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo

from seller_dashboard.action_store import get_actions_by_session
from seller_dashboard.assistant_style import FEMININE_VOICE_PROMPT
from seller_dashboard.conversation_store import get_conversation_history
from seller_dashboard.tools import (
    _SESSION_FINDINGS,
    get_seller_metrics,
    normalize_seller_id,
)

logger = logging.getLogger("seller_dashboard.summary")

MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = MODULE_PATH.parents[2]
DEFAULT_SUMMARIES_CSV = PROJECT_ROOT / "data" / "call_summaries.csv"

_CUSTOM_SUMMARIES_PATH: Path | None = None
_SUMMARY_LOCK = Lock()

CSV_FIELDS = [
    "summary_id",
    "seller_id",
    "session_id",
    "created_at",
    "call_status",
    "business_overview",
    "key_metrics",
    "identified_issues",
    "recommendations",
    "agreed_actions",
    "unresolved_questions",
    "seller_commitments",
    "overall_summary",
    "source_message_count",
    "source_action_count",
]

JSON_FIELDS = [
    "business_overview",
    "key_metrics",
    "identified_issues",
    "recommendations",
    "agreed_actions",
    "unresolved_questions",
    "seller_commitments",
]


def get_summaries_csv_path() -> Path:
    """Return the active summaries CSV path, respecting overrides."""
    if _CUSTOM_SUMMARIES_PATH is not None:
        return _CUSTOM_SUMMARIES_PATH
    env_path = os.getenv("SUMMARIES_CSV_PATH")
    if env_path:
        return Path(env_path).resolve()
    return DEFAULT_SUMMARIES_CSV


def set_summaries_csv_path(path: Path | str | None) -> None:
    """Override the summaries CSV path for isolated tests."""
    global _CUSTOM_SUMMARIES_PATH
    if path is None:
        _CUSTOM_SUMMARIES_PATH = None
    else:
        _CUSTOM_SUMMARIES_PATH = Path(path).resolve()


def ensure_csv_file(path: Path | None = None) -> Path:
    """Ensure the summaries CSV exists with UTF-8 BOM headers."""
    csv_path = path or get_summaries_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
    return csv_path


def read_all_raw_summaries(path: Path | None = None) -> list[dict]:
    """Read all summary rows as raw string dictionaries from CSV."""
    csv_path = ensure_csv_file(path)
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def parse_summary_record(raw: dict) -> dict:
    """Deserialize JSON fields in a raw summary record into Python objects."""
    parsed = dict(raw)
    for field in JSON_FIELDS:
        val = raw.get(field, "")
        if isinstance(val, str) and val.strip():
            try:
                parsed[field] = json.loads(val)
            except Exception:
                parsed[field] = val
        elif not val:
            parsed[field] = [] if field in {
                "identified_issues",
                "recommendations",
                "agreed_actions",
                "unresolved_questions",
                "seller_commitments",
            } else {}
    try:
        parsed["source_message_count"] = int(raw.get("source_message_count", 0))
    except (ValueError, TypeError):
        parsed["source_message_count"] = 0
    try:
        parsed["source_action_count"] = int(raw.get("source_action_count", 0))
    except (ValueError, TypeError):
        parsed["source_action_count"] = 0
    return parsed


def write_all_raw_summaries(summaries: list[dict], path: Path | None = None) -> bool:
    """Write raw summary rows atomically using temp file and utf-8-sig."""
    csv_path = path or get_summaries_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = csv_path.with_name(f"{csv_path.name}.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for summary in summaries:
                row = {field: str(summary.get(field, "") or "") for field in CSV_FIELDS}
                writer.writerow(row)
        temp_path.replace(csv_path)
        return True
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise


def next_summary_id(summaries: list[dict]) -> str:
    """Generate next unique summary ID (e.g. SUM-001)."""
    max_id = 0
    for s in summaries:
        sid = str(s.get("summary_id", ""))
        match = re.search(r"SUM-(\d+)", sid, re.IGNORECASE)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"SUM-{max_id + 1:03d}"


def save_call_summary(summary_data: dict, path: Path | None = None) -> dict:
    """Save or update a structured call summary in CSV, ensuring one record per session."""
    norm_seller = normalize_seller_id(summary_data.get("seller_id"))
    if not norm_seller:
        raise ValueError("A valid seller_id is required to save a call summary.")

    norm_session = str(summary_data.get("session_id", "")).strip()
    if not norm_session:
        raise ValueError("A valid session_id is required to save a call summary.")

    csv_path = path or get_summaries_csv_path()

    with _SUMMARY_LOCK:
        raw_summaries = read_all_raw_summaries(csv_path)

        # Look for existing summary for this session & seller (to update rather than duplicate)
        existing_idx = None
        existing_id = None
        for idx, row in enumerate(raw_summaries):
            if (
                row.get("session_id", "").strip() == norm_session
                and row.get("seller_id", "").strip().upper() == norm_seller
            ):
                existing_idx = idx
                existing_id = row.get("summary_id")
                break

        summary_id = existing_id or next_summary_id(raw_summaries)
        ts = summary_data.get("created_at") or datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

        # Serialize structured fields to JSON strings for CSV storage
        def serialize_field(val: Any) -> str:
            if isinstance(val, (dict, list)):
                return json.dumps(val, ensure_ascii=False)
            return str(val or "")

        raw_record = {
            "summary_id": summary_id,
            "seller_id": norm_seller,
            "session_id": norm_session,
            "created_at": ts,
            "call_status": str(summary_data.get("call_status", "completed")),
            "business_overview": serialize_field(summary_data.get("business_overview", {})),
            "key_metrics": serialize_field(summary_data.get("key_metrics", {})),
            "identified_issues": serialize_field(summary_data.get("identified_issues", [])),
            "recommendations": serialize_field(summary_data.get("recommendations", [])),
            "agreed_actions": serialize_field(summary_data.get("agreed_actions", [])),
            "unresolved_questions": serialize_field(summary_data.get("unresolved_questions", [])),
            "seller_commitments": serialize_field(summary_data.get("seller_commitments", [])),
            "overall_summary": str(summary_data.get("overall_summary", "")),
            "source_message_count": str(summary_data.get("source_message_count", 0)),
            "source_action_count": str(summary_data.get("source_action_count", 0)),
        }

        if existing_idx is not None:
            raw_summaries[existing_idx] = raw_record
        else:
            raw_summaries.append(raw_record)

        write_all_raw_summaries(raw_summaries, csv_path)

        # Verification step: read back from disk
        verified_raw = read_all_raw_summaries(csv_path)
        matching = [r for r in verified_raw if r.get("summary_id") == summary_id]
        if not matching:
            raise IOError(f"Verification failed: summary {summary_id} not found in CSV after write.")

        return parse_summary_record(matching[0])


def get_call_summary_record(
    session_id: str,
    seller_id: str | None = None,
    path: Path | None = None,
) -> dict | None:
    """Retrieve a call summary for a specific session with seller isolation."""
    csv_path = path or get_summaries_csv_path()
    norm_session = str(session_id or "").strip()
    norm_seller = normalize_seller_id(seller_id) if seller_id else None

    raw_summaries = read_all_raw_summaries(csv_path)
    for row in raw_summaries:
        if row.get("session_id", "").strip() == norm_session:
            if norm_seller and row.get("seller_id", "").strip().upper() != norm_seller:
                return None
            return parse_summary_record(row)
    return None


def get_seller_call_summaries(
    seller_id: str,
    path: Path | None = None,
) -> list[dict]:
    """Retrieve all call summaries for a seller in reverse chronological order."""
    csv_path = path or get_summaries_csv_path()
    norm_seller = normalize_seller_id(seller_id)
    if not norm_seller:
        return []

    raw_summaries = read_all_raw_summaries(csv_path)
    results = []
    for row in raw_summaries:
        if row.get("seller_id", "").strip().upper() == norm_seller:
            results.append(parse_summary_record(row))

    results.sort(key=lambda s: s.get("created_at", ""), reverse=True)
    return results


def _extract_conversation_elements(messages: list[dict]) -> tuple[list[str], list[str], list[str]]:
    """Extract assistant recommendations, seller commitments, and unresolved questions."""
    recommendations = []
    commitments = []
    unresolved = []

    for msg in messages:
        text = msg.get("message_text", "")
        speaker = msg.get("speaker", "")

        if speaker == "assistant":
            # Identify recommendations
            if any(term in text.lower() for term in [
                "recommend", "suggest", "restock", "सलाह", "सुझाव",
                "स्टॉक चेक", "playbook", "check your listing", "update physical stock"
            ]):
                recommendations.append(text)
            # Identify questions asked about missing data
            if any(term in text.lower() for term in [
                "cost", "margin", "profit", "purchase price", "लागत",
                "मार्जिन", "लीड टाइम", "lead time", "when will you restock"
            ]):
                unresolved.append(text)

        elif speaker == "seller":
            # Identify seller explicit commitments
            if any(term in text.lower() for term in [
                "हाँ", "कर दूँगा", "कर दूंगा", "i will", "we will",
                "restock will be done", "yes, please record", "पक्का"
            ]):
                commitments.append(text)

    # Deduplicate while preserving order
    def dedup(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    return dedup(recommendations), dedup(commitments), dedup(unresolved)


def generate_call_summary(
    seller_id: str,
    session_id: str,
    llm: Any = None,
    path: Path | None = None,
    call_status: str = "completed",
) -> dict:
    """Generate a structured, evidence-grounded call summary and persist it to CSV."""
    norm_seller = normalize_seller_id(seller_id)
    if not norm_seller:
        return {
            "success": False,
            "error": "seller_id_required",
            "message": "A valid seller ID is required to generate a call summary.",
        }

    norm_session = str(session_id or "").strip()
    if not norm_session:
        return {
            "success": False,
            "error": "session_id_required",
            "message": "A valid session ID is required to generate a call summary.",
        }

    # 1. Retrieve actual conversation history
    messages = get_conversation_history(session_id=norm_session, seller_id=norm_seller)
    if not messages:
        return {
            "success": False,
            "error": "empty_conversation",
            "message": f"No conversation messages found for seller {norm_seller} and session {norm_session}.",
        }

    # 2. Retrieve actual actions for this session
    session_actions = get_actions_by_session(session_id=norm_session, seller_id=norm_seller)
    agreed_actions = []
    for act in session_actions:
        agreed_actions.append({
            "action_id": act.get("action_id"),
            "action_type": act.get("action_type"),
            "description": act.get("action_description"),
            "related_product": act.get("related_product", ""),
            "deadline": act.get("reminder_date"),
            "status": act.get("status", "Pending"),
            "seller_consent": act.get("seller_consent", ""),
        })

    # 3. Retrieve verified seller metrics directly from Python tools
    raw_metrics = get_seller_metrics.invoke({"seller_id": norm_seller})
    key_metrics = {}
    business_overview = {
        "seller_id": norm_seller,
        "business_name": "Unknown",
        "category": "Unknown",
        "status": "active",
        "observations": "",
    }

    if isinstance(raw_metrics, dict) and not raw_metrics.get("error"):
        business_overview["business_name"] = raw_metrics.get("business", "Unknown")
        business_overview["category"] = raw_metrics.get("category", "Unknown")

        last_m = raw_metrics.get("last_month", {})
        this_m = raw_metrics.get("this_month", {})
        changes = raw_metrics.get("changes", {})

        oos_old = last_m.get("out_of_stock_products")
        oos_new = this_m.get("out_of_stock_products")
        oos_diff = changes.get("out_of_stock_products")
        if oos_diff is None and isinstance(oos_old, (int, float)) and isinstance(oos_new, (int, float)):
            oos_diff = oos_new - oos_old

        c_old = last_m.get("cancellation_rate_pct")
        c_new = this_m.get("cancellation_rate_pct")
        c_diff = changes.get("cancellation_rate_pp")
        if c_diff is None and isinstance(c_old, (int, float)) and isinstance(c_new, (int, float)):
            c_diff = round(c_new - c_old, 1)

        key_metrics = {
            "sales": {
                "last_month": last_m.get("sales"),
                "this_month": this_m.get("sales"),
                "change_pct": changes.get("sales_pct"),
                "display": f"{last_m.get('sales_display', '')} -> {this_m.get('sales_display', '')}",
            },
            "orders": {
                "last_month": last_m.get("orders"),
                "this_month": this_m.get("orders"),
                "change_pct": changes.get("orders_pct"),
            },
            "avg_selling_price": {
                "last_month": last_m.get("avg_selling_price"),
                "this_month": this_m.get("avg_selling_price"),
                "change_pct": changes.get("avg_selling_price_pct"),
                "note": "ASP is average selling price, not profit or margin.",
            },
            "cancellation_rate_pct": {
                "last_month": c_old,
                "this_month": c_new,
                "diff_points": c_diff,
            },
            "out_of_stock_products": {
                "last_month": oos_old,
                "this_month": oos_new,
                "diff_count": oos_diff,
            },
        }

        # Compose factual business overview
        sales_chg = changes.get("sales_pct")
        direction = "decreased" if sales_chg and sales_chg < 0 else "increased" if sales_chg and sales_chg > 0 else "stable"
        business_overview["observations"] = (
            f"Seller {business_overview['business_name']} ({business_overview['category']}): "
            f"Sales {direction} by {abs(sales_chg) if sales_chg is not None else 'N/A'}% month-over-month. "
            f"Orders changed by {changes.get('orders_pct')}%, ASP change {changes.get('avg_selling_price_pct')}%, "
            f"and out-of-stock products changed by {oos_diff}."
        )
    else:
        key_metrics = {"status": "unavailable", "note": "Verified seller metrics could not be retrieved from tools."}
        business_overview["observations"] = "Seller metrics unavailable."

    # 4. Formulate identified issues, strictly separating facts from hypotheses
    identified_issues = []

    # Check diagnostic findings from session
    session_findings = _SESSION_FINDINGS.get(norm_session, [])
    for f in session_findings:
        identified_issues.append({
            "issue": f.get("issue"),
            "summary": f.get("summary"),
            "evidence": f.get("evidence"),
            "type": "fact",
            "confidence": f.get("confidence", "high"),
        })

    # Grounded metrics facts vs hypotheses
    oos_count = key_metrics.get("out_of_stock_products", {}).get("diff_count")
    if isinstance(oos_count, (int, float)) and oos_count > 0:
        identified_issues.append({
            "issue": "out_of_stock_increase",
            "summary": f"Out-of-stock product count increased by {oos_count}.",
            "evidence": f"OOS rose from {key_metrics['out_of_stock_products']['last_month']} to {key_metrics['out_of_stock_products']['this_month']}.",
            "type": "fact",
            "confidence": "high",
        })

    cancel_points = key_metrics.get("cancellation_rate_pct", {}).get("diff_points")
    if isinstance(cancel_points, (int, float)) and cancel_points > 0:
        identified_issues.append({
            "issue": "cancellation_rate_increase",
            "summary": f"Cancellation rate increased by {cancel_points} percentage points.",
            "evidence": f"Cancellation rate changed from {key_metrics['cancellation_rate_pct']['last_month']}% to {key_metrics['cancellation_rate_pct']['this_month']}%.",
            "type": "fact",
            "confidence": "high",
        })
        # Add hypothesis explicitly labeled as hypothesis
        identified_issues.append({
            "issue": "inventory_mismatch_hypothesis",
            "summary": "Physical stock may not match listed stock, contributing to cancellations.",
            "evidence": "Observed correlation between higher stockouts and rising cancellations; unconfirmed by warehouse check.",
            "type": "hypothesis",
            "confidence": "medium",
        })

    asp_chg = key_metrics.get("avg_selling_price", {}).get("change_pct")
    if isinstance(asp_chg, (int, float)) and asp_chg < 0:
        identified_issues.append({
            "issue": "asp_decline_hypothesis",
            "summary": "ASP fell; discounts or product mix changes may be relevant but are unconfirmed causes.",
            "evidence": f"ASP fell by {abs(asp_chg)}%; unit costs and discounts not provided.",
            "type": "hypothesis",
            "confidence": "low",
        })

    # 5. Extract recommendations, commitments, and unresolved questions from conversation
    recs, commits, unres = _extract_conversation_elements(messages)

    # Always ensure missing financial data is explicitly marked unresolved
    unresolved_questions = list(unres)
    unresolved_questions.append("Unit product cost and profit margins were not provided; profitability cannot be determined.")
    unresolved_questions = list(dict.fromkeys(unresolved_questions))

    # 6. Overall summary prose
    overall_summary = (
        f"Call summary for seller {norm_seller} ({business_overview.get('business_name', 'Snapdeal Seller')}, "
        f"{business_overview.get('category', 'Category')}). The discussion covered {len(messages)} conversation turns "
        f"addressing performance changes. The seller has {len(agreed_actions)} recorded action(s). "
        f"{business_overview.get('observations', '')}"
    )

    # 7. LLM integration (if an LLM instance is provided and healthy)
    if llm is not None:
        try:
            prompt = (
                f"You are the Snapdeal Virtual KAM assistant. Write a concise, professional 2-3 sentence overall summary of this call.\n"
                f"Seller: {norm_seller} ({business_overview.get('business_name')})\n"
                f"Metrics: {json.dumps(key_metrics, ensure_ascii=False)}\n"
                f"Actions: {json.dumps(agreed_actions, ensure_ascii=False)}\n"
                f"Conversation turns: {len(messages)}\n"
                f"Rules: Do not invent metrics or margin figures. Do not claim emails were sent.\n"
                f"{FEMININE_VOICE_PROMPT}"
            )
            llm_response = llm.invoke(prompt)
            content = getattr(llm_response, "content", None)
            if content and isinstance(content, str) and content.strip():
                # Validate that LLM did not invent fake margin/profit
                if "profit margin is" not in content.lower():
                    overall_summary = content.strip()
        except Exception as exc:
            logger.warning("LLM call summary generation failed; using grounded fallback. Error: %s", exc)

    summary_payload = {
        "seller_id": norm_seller,
        "session_id": norm_session,
        "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "call_status": call_status,
        "business_overview": business_overview,
        "key_metrics": key_metrics,
        "identified_issues": identified_issues,
        "recommendations": recs,
        "agreed_actions": agreed_actions,
        "unresolved_questions": unresolved_questions,
        "seller_commitments": commits,
        "overall_summary": overall_summary,
        "source_message_count": len(messages),
        "source_action_count": len(agreed_actions),
    }

    # Persist to CSV
    saved = save_call_summary(summary_payload, path=path)
    return {
        "success": True,
        "summary": saved,
    }
