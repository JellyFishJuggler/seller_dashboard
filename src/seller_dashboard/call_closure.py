import logging
import re
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo

from seller_dashboard.action_store import get_actions_by_session
from seller_dashboard.assistant_style import ensure_hindi_response

from seller_dashboard.conversation_store import (
    get_conversation_history,
    save_message,
)
from seller_dashboard.summary_store import (
    generate_call_summary,
    get_call_summary_record,
    save_call_summary,
)
from seller_dashboard.tools import (
    _resolve_seller_id,
    normalize_seller_id,
)

logger = logging.getLogger("seller_dashboard.call_closure")

_CLOSURE_LOCK = Lock()
_SESSION_STATES: dict[str, str] = {}  # session_id -> "active" | "finalizing" | "completed" | "failed"


TERMINATION_PATTERNS = [
    r"(?:^|\s)(?:बस\s*(?:आज\s*के\s*लिए\s*)?इतना\s*ही)(?:\s|$)",
    r"(?:^|\s)(?:कॉल\s*(?:खत्म|समाप्त|बंद|काट|end)\s*(?:कर\s*(?:सकते\s*हैं|सकते|दीजिए|दें|दो)|करें)?)(?:\s|$)",
    r"\b(?:call\s*(?:khatam|samapt|band|end)\s*(?:kar\s*(?:sakte|sakte\s*hain|dijiye|do))?)\b",
    r"\b(?:bas\s*(?:aaj\s*ke\s*liye\s*)?itna\s*hi)\b",
    r"\b(?:that(?:'s|\s+is)\s+all(?:\s+for\s+today)?)\b",
    r"\b(?:(?:we\s+can\s+)?end\s+(?:the\s+)?call(?:\s+now)?)\b",
    r"\b(?:finish\s+(?:the\s+)?call)\b",
    r"(?:^|\s|\b)(?:bye(?:\s+bye)?|goodbye|alvida|अलविदा)(?:\s|\b|$)",
    r"\b(?:nothing\s+(?:more|else)\s+for\s+today)\b",
    r"\b(?:done\s+for\s+(?:today|now))\b",
    r"(?:^|\s)(?:और\s*कुछ\s*नहीं(?:\s*चाहिए|\s*पूछना)?\s*(?:अब\s*)?कॉल\s*(?:रख|काट|खत्म|बंद))(?:\s|$)",
]

NON_TERMINATION_PHRASES = {
    "ठीक है", "हाँ", "अच्छा", "ok", "okay", "sure", "yes",
    "theek hai", "haan", "achha", "bataiye", "बताइए",
}


def is_call_termination_intent(text: str) -> bool:
    """Detect if the seller explicitly requested to end the call."""
    if not text or not isinstance(text, str):
        return False

    clean = text.strip().lower().replace("’", "'")
    # Strip punctuation while preserving internal apostrophes
    clean_no_punct = re.sub(r"[\u0964\u0965.,!?;:\"()\-–—]", " ", clean)
    clean_no_punct = re.sub(r"\s+", " ", clean_no_punct).strip()

    if not clean_no_punct or clean_no_punct in NON_TERMINATION_PHRASES:
        return False

    # If starts with affirmative word (e.g. "हाँ" / "ठीक है"), examine the remaining message
    rest = re.sub(r"^(?:ठीक\s*है|हाँ|अच्छा|ok|okay|sure|yes|theek\s*hai|haan|achha)\s*", "", clean_no_punct).strip()
    target = rest if rest else clean_no_punct

    for pat in TERMINATION_PATTERNS:
        if re.search(pat, target, re.IGNORECASE):
            return True

    return False


def has_unanswered_assistant_question(history: list[dict]) -> bool:
    """True when the latest seller turn is an end request after an assistant question."""
    if not history or history[-1].get("speaker") != "seller":
        return False
    prior = history[:-1]
    if not prior or prior[-1].get("speaker") != "assistant":
        return False
    text = str(prior[-1].get("message_text", "")).rstrip()
    if text in {
        build_pending_question_offer("hindi"),
        build_pending_question_offer("english"),
        build_pending_question_offer("hinglish"),
    }:
        return False
    return text.endswith(("?", "？"))


def build_pending_question_offer(language: str | None) -> str:
    """Offer to address the open question in the session's language."""
    if language == "hindi":
        return "कॉल समाप्त करने से पहले, क्या आप चाहेंगे कि मैं आपके पिछले सवाल का जवाब दे दूँ?"
    return "Before we end the call, would you like me to answer your previous question?"


def is_session_active(session_id: str) -> bool:
    """Check if session is currently active (not finalizing or completed)."""
    with _CLOSURE_LOCK:
        state = _SESSION_STATES.get(str(session_id), "active")
        return state == "active"


def get_session_lifecycle_state(session_id: str) -> str:
    """Get the lifecycle state of a session."""
    with _CLOSURE_LOCK:
        return _SESSION_STATES.get(str(session_id), "active")


def mark_session_state(session_id: str, state: str) -> None:
    """Set the lifecycle state of a session."""
    with _CLOSURE_LOCK:
        _SESSION_STATES[str(session_id)] = state


def reset_session_state(session_id: str) -> None:
    """Reset a session's state (useful for cleanup and tests)."""
    with _CLOSURE_LOCK:
        _SESSION_STATES.pop(str(session_id), None)


def build_final_goodbye(language: str = "english") -> str:
    """Return the fixed closing goodbye in the conversation language."""
    if language == "hindi":
        return "धन्यवाद! Snapdeal पर आपके business की प्रगति के लिए शुभकामनाएँ। आपका दिन अच्छा रहे। अलविदा!"
    return "Thank you for speaking with Snapdeal. We wish you continued success. Goodbye!"


def generate_final_spoken_summary(
    seller_id: str,
    session_id: str,
    language: str = "english",
    summary_record: dict | None = None,
    storage_status: dict | None = None,
) -> str:
    """Generate a concise, spoken final summary and honest save confirmation."""
    norm_lang = "hindi" if language == "hindi" else "english"
    summary = summary_record or {}
    storage = storage_status or {"summary_saved": True, "transcript_saved": True}

    # Extract verified actions from summary
    actions = summary.get("agreed_actions", [])
    metrics = summary.get("key_metrics", {})

    # Keep only stable action identifiers and dates in the spoken summary.
    action_texts = []
    for a in actions:
        date = a.get("deadline") or a.get("reminder_date") or ""
        aid = a.get("action_id", "")
        if aid and date:
            action_texts.append(
                f"Action ID {aid}, date {date}"
                if norm_lang == "english"
                else f"Action ID {aid}, तारीख {date}"
            )
        elif aid:
            action_texts.append(f"Action ID {aid}")

    actions_summary = (" and " if norm_lang == "english" else " और ").join(action_texts)

    # Storage confirmation text
    if storage.get("summary_saved") and storage.get("transcript_saved"):
        storage_note = (
            "Your conversation transcript and call summary have been saved. "
            "No email or notification was sent."
            if norm_lang == "english"
            else "आपकी बातचीत का transcript और call summary सुरक्षित दर्ज हैं। "
            "ध्यान दें कि कोई email या notification नहीं भेजा गया है।"
        )
    else:
        failed_parts = []
        if not storage.get("summary_saved"):
            failed_parts.append("call summary")
        if not storage.get("transcript_saved"):
            failed_parts.append("conversation transcript" if norm_lang == "english" else "बातचीत का transcript")
        failed_str = (" and " if norm_lang == "english" else " और ").join(failed_parts)
        storage_note = (
            f"The conversation is safe, but the {failed_str} could not be saved."
            if norm_lang == "english"
            else f"आपकी बातचीत सुरक्षित रही, लेकिन {failed_str} दर्ज नहीं हो सकी।"
        )

    goodbye = build_final_goodbye(norm_lang)

    # Use only facts already present in the structured summary.
    observations = []
    sales = metrics.get("sales", {}) if isinstance(metrics, dict) else {}
    orders = metrics.get("orders", {}) if isinstance(metrics, dict) else {}
    if isinstance(sales, dict) and sales.get("last_month") is not None and sales.get("this_month") is not None:
        observations.append(
            f"Sales were {sales['last_month']} last month and {sales['this_month']} this month"
            if norm_lang == "english"
            else f"Sales पिछले महीने {sales['last_month']} रुपये थी और इस महीने {sales['this_month']} रुपये रही"
        )
    if isinstance(orders, dict) and orders.get("last_month") is not None and orders.get("this_month") is not None:
        observations.append(
            f"Orders were {orders['last_month']} last month and {orders['this_month']} this month"
            if norm_lang == "english"
            else f"Orders पिछले महीने {orders['last_month']} थे और इस महीने {orders['this_month']} रहे"
        )
    main_observation = ("; " if norm_lang == "english" else "; ").join(observations[:2])

    # Compose language-specific spoken summary
    if norm_lang == "hindi":
        parts = [f"आज की बातचीत में हमने {main_observation} पर चर्चा की।" if main_observation else "आज हमने आपकी उपलब्ध business जानकारी की समीक्षा की।"]
        if actions_summary:
            parts.append(f"आपका सहमत follow-up action दर्ज है: {actions_summary}।")
        parts.append(storage_note)
        parts.append(goodbye)
        return ensure_hindi_response(" ".join(parts))

    parts = [f"Today we discussed {main_observation}." if main_observation else "Today we reviewed your available business information."]
    if actions_summary:
        parts.append(f"Your agreed follow-up is recorded: {actions_summary}.")
    parts.append(storage_note)
    parts.append(goodbye)
    return " ".join(parts)


def finalize_call_session(
    seller_id: str,
    session_id: str,
    channel: str = "voice",
    language: str | None = None,
    path_summaries: Any = None,
    path_conversations: Any = None,
    path_actions: Any = None,
    defer_completion: bool = False,
) -> dict:
    """Execute the end-to-end call finalization workflow atomically and idempotently."""
    voice_channel = channel == "voice"
    norm_seller = normalize_seller_id(seller_id) or "SD-DEFAULT"
    norm_session = str(session_id or "").strip()

    if not norm_session:
        return {
            "success": False,
            "status": "failed",
            "error": "session_id_required",
            "message": (
                "Call पूरी करने के लिए session की पहचान उपलब्ध नहीं है।"
                if voice_channel else "A session ID is required to finalize the call."
            ),
        }

    # Step 1: Idempotency check & mark session as finalizing
    with _CLOSURE_LOCK:
        current_state = _SESSION_STATES.get(norm_session, "active")
        if current_state == "completed":
            logger.info("Session %s is already completed. Returning existing summary.", norm_session)
            existing_summary = get_call_summary_record(norm_session, norm_seller, path=path_summaries)
            return {
                "success": bool(existing_summary and existing_summary.get("call_status") == "completed"),
                "status": "completed" if existing_summary and existing_summary.get("call_status") == "completed" else "failed",
                "seller_id": norm_seller,
                "session_id": norm_session,
                "summary": existing_summary,
                "final_message": _saved_final_message(norm_session, norm_seller, channel, path_conversations),
                "message": (
                    "यह call पहले ही पूरी हो चुकी है।"
                    if voice_channel and existing_summary and existing_summary.get("call_status") == "completed"
                    else "पूरी हुई call की summary की पुष्टि नहीं हो सकी।"
                    if voice_channel
                    else "This call is already complete."
                    if existing_summary and existing_summary.get("call_status") == "completed"
                    else "Could not verify the completed call summary."
                ),
            }
        if current_state == "finalizing":
            logger.info("Session %s is already being finalized.", norm_session)
            return {
                "success": False,
                "status": "finalizing",
                "seller_id": norm_seller,
                "session_id": norm_session,
                "error": "finalization_in_progress",
                "message": (
                    "Call पूरी करने की प्रक्रिया पहले से जारी है।"
                    if voice_channel else "Call finalization is already in progress."
                ),
            }
        _SESSION_STATES[norm_session] = "finalizing"

    try:
        # Step 2: Retrieve conversation history
        history = get_conversation_history(norm_session, norm_seller, path=path_conversations)
        if not history:
            mark_session_state(norm_session, "failed")
            return {
                "success": False,
                "status": "failed",
                "error": "empty_conversation",
                "message": (
                    "बातचीत उपलब्ध नहीं है, इसलिए call पूरी नहीं की जा सकती।"
                    if voice_channel else "The call cannot be finalized because no conversation was found."
                ),
            }

        # Determine session language
        detected_lang = "hindi" if channel == "voice" else "english"

        # Step 3: Retrieve seller actions
        actions = get_actions_by_session(norm_session, norm_seller, path=path_actions)

        # Step 4: Generate structured call summary
        summary_result = generate_call_summary(
            seller_id=norm_seller,
            session_id=norm_session,
            path=path_summaries,
            call_status="finalizing",
            language=detected_lang,
        )

        if not summary_result.get("success"):
            mark_session_state(norm_session, "failed")
            return {
                "success": False,
                "status": "failed",
                "error": summary_result.get("error", "summary_generation_failed"),
                "message": (
                    "Call summary तैयार नहीं हो सकी।"
                    if voice_channel else "Could not generate the call summary."
                ),
            }

        # Step 5: Verify summary persistence on disk
        verified_summary = get_call_summary_record(norm_session, norm_seller, path=path_summaries)
        if not verified_summary:
            mark_session_state(norm_session, "failed")
            return {
                "success": False,
                "status": "failed",
                "error": "summary_verification_failed",
                "message": (
                    "Call summary सुरक्षित दर्ज होने की पुष्टि नहीं हो सकी।"
                    if voice_channel else "Could not verify that the call summary was saved."
                ),
            }

        storage_status = {
            "summary_saved": True,
            "transcript_saved": bool(history),
            "actions_saved": isinstance(actions, list),
        }

        # Step 6: Formulate final spoken response & goodbye
        final_spoken = generate_final_spoken_summary(
            seller_id=norm_seller,
            session_id=norm_session,
            language=detected_lang,
            summary_record=verified_summary,
            storage_status=storage_status,
        )

        # Step 7: Persist final assistant closing message to conversation store
        save_res = save_message(
            seller_id=norm_seller,
            session_id=norm_session,
            speaker="assistant",
            message_text=final_spoken,
            channel=channel,
            language=detected_lang,
            path=path_conversations,
        )
        if not save_res.get("saved") and not save_res.get("duplicate"):
            raise IOError(f"Final closing message could not be persisted: {save_res.get('message', 'storage error')}")

        verified_history = get_conversation_history(norm_session, norm_seller, path=path_conversations)
        if not any(
            row.get("speaker") == "assistant" and row.get("message_text") == final_spoken
            for row in verified_history
        ):
            raise IOError("Final closing transcript could not be verified after write.")

        # Voice sessions stay finalizing until TTS has played in the browser.
        if not defer_completion:
            completion = complete_call_finalization(
                norm_seller,
                norm_session,
                path_summaries=path_summaries,
                path_conversations=path_conversations,
                path_actions=path_actions,
                channel=channel,
            )
            if not completion.get("success"):
                return completion
            verified_summary = completion["summary"]

        return {
            "success": True,
            "status": "finalizing" if defer_completion else "completed",
            "seller_id": norm_seller,
            "session_id": norm_session,
            "summary": verified_summary,
            "final_message": final_spoken,
            "language": detected_lang,
            "message": (
                "Call summary तैयार है; closing audio चलने की पुष्टि बाकी है।"
                if voice_channel and defer_completion
                else "Call सफलतापूर्वक पूरी और सुरक्षित दर्ज हो गई है।"
                if voice_channel
                else "Call summary is ready; waiting for closing audio playback."
                if defer_completion
                else "Call successfully finalized and saved."
            ),
        }
    except Exception as exc:
        logger.exception("Finalization failed for session %s: %s", norm_session, exc)
        fail_call_finalization(norm_seller, norm_session, str(exc), path_summaries=path_summaries)
        return {
            "success": False,
            "status": "failed",
            "error": "finalization_exception",
            "message": (
                "तकनीकी समस्या के कारण call पूरी नहीं हो सकी। आपके सहेजे गए रिकॉर्ड सुरक्षित हैं।"
                if voice_channel else "A technical issue prevented call finalization. Saved records are safe."
            ),
        }


def _saved_final_message(session_id: str, seller_id: str, channel: str, path: Any = None) -> str | None:
    history = get_conversation_history(session_id, seller_id, path=path)
    return next((
        row.get("message_text") for row in reversed(history)
        if row.get("speaker") == "assistant" and row.get("channel") == channel
    ), None)


def complete_call_finalization(
    seller_id: str,
    session_id: str,
    path_summaries: Any = None,
    path_conversations: Any = None,
    path_actions: Any = None,
    channel: str = "voice",
) -> dict:
    """Mark a staged voice finalization completed after verifying persisted records and playback."""
    norm_seller = normalize_seller_id(seller_id) or "SD-DEFAULT"
    norm_session = str(session_id or "").strip()
    if not norm_session:
        return {"success": False, "status": "failed", "error": "session_id_required"}

    with _CLOSURE_LOCK:
        state = _SESSION_STATES.get(norm_session, "active")
        if state == "completed":
            existing = get_call_summary_record(norm_session, norm_seller, path=path_summaries)
            return {"success": bool(existing and existing.get("call_status") == "completed"), "status": "completed", "summary": existing}
        if state != "finalizing":
            return {"success": False, "status": state, "error": "session_not_finalizing"}

    try:
        history = get_conversation_history(norm_session, norm_seller, path=path_conversations)
        summary = get_call_summary_record(norm_session, norm_seller, path=path_summaries)
        actions = get_actions_by_session(norm_session, norm_seller, path=path_actions)
        final_message = _saved_final_message(norm_session, norm_seller, channel, path_conversations)
        if not history or not summary or not isinstance(actions, list) or not final_message:
            raise IOError("Transcript, summary, or action records could not be verified.")
        summary["call_status"] = "completed"
        saved_summary = save_call_summary(summary, path=path_summaries)
        verified = get_call_summary_record(norm_session, norm_seller, path=path_summaries)
        if not saved_summary or not verified or verified.get("call_status") != "completed":
            raise IOError("Completed call summary could not be verified.")
        mark_session_state(norm_session, "completed")
        return {"success": True, "status": "completed", "summary": verified}
    except Exception as exc:
        logger.exception("Could not complete call finalization for %s: %s", norm_session, exc)
        mark_session_state(norm_session, "failed")
        return {"success": False, "status": "failed", "error": "completion_verification_failed", "message": str(exc)}


def fail_call_finalization(
    seller_id: str,
    session_id: str,
    reason: str,
    path_summaries: Any = None,
) -> None:
    """Record an incomplete finalization without marking the call completed."""
    norm_seller = normalize_seller_id(seller_id) or "SD-DEFAULT"
    norm_session = str(session_id or "").strip()
    try:
        summary = get_call_summary_record(norm_session, norm_seller, path=path_summaries)
        if summary and summary.get("call_status") != "completed":
            summary["call_status"] = "failed"
            save_call_summary(summary, path=path_summaries)
    except Exception:
        logger.exception("Failed to record finalization failure for session %s", norm_session)
    mark_session_state(norm_session, "failed")
    logger.error("Call finalization did not complete for session %s: %s", norm_session, reason)
