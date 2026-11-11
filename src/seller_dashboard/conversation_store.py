import csv
from datetime import datetime
import logging
import os
from pathlib import Path
import re
from threading import Lock
from zoneinfo import ZoneInfo

from seller_dashboard.bot import classify_text_language
from seller_dashboard.tools import normalize_seller_id

logger = logging.getLogger("seller_dashboard.conversation")

MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = MODULE_PATH.parents[2]
DEFAULT_CONVERSATIONS_CSV = PROJECT_ROOT / "data" / "conversations.csv"

_CUSTOM_CONVERSATIONS_PATH: Path | None = None
_CONVERSATION_LOCK = Lock()

CSV_FIELDS = [
    "message_id",
    "seller_id",
    "session_id",
    "timestamp",
    "speaker",
    "message_text",
    "language",
    "channel",
]

ALLOWED_SPEAKERS = {"seller", "assistant"}
ALLOWED_CHANNELS = {"voice", "text"}


def get_conversations_csv_path() -> Path:
    """Return the active conversations CSV path, respecting overrides."""
    if _CUSTOM_CONVERSATIONS_PATH is not None:
        return _CUSTOM_CONVERSATIONS_PATH
    env_path = os.getenv("CONVERSATIONS_CSV_PATH")
    if env_path:
        return Path(env_path).resolve()
    return DEFAULT_CONVERSATIONS_CSV


def set_conversations_csv_path(path: Path | str | None) -> None:
    """Override the conversations CSV path for isolated tests."""
    global _CUSTOM_CONVERSATIONS_PATH
    if path is None:
        _CUSTOM_CONVERSATIONS_PATH = None
    else:
        _CUSTOM_CONVERSATIONS_PATH = Path(path).resolve()


def ensure_csv_file(path: Path | None = None) -> Path:
    """Ensure the conversations CSV exists with UTF-8 BOM headers."""
    csv_path = path or get_conversations_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
    return csv_path


def read_all_messages(path: Path | None = None) -> list[dict]:
    """Read all conversation messages from CSV using utf-8-sig."""
    csv_path = ensure_csv_file(path)
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def write_all_messages(messages: list[dict], path: Path | None = None) -> bool:
    """Write messages atomically using a temp file and utf-8-sig."""
    csv_path = path or get_conversations_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = csv_path.with_name(f"{csv_path.name}.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for msg in messages:
                row = {field: str(msg.get(field, "") or "") for field in CSV_FIELDS}
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


def next_message_id(messages: list[dict]) -> str:
    """Generate next unique message ID (e.g. MSG-0001)."""
    max_id = 0
    for msg in messages:
        mid = str(msg.get("message_id", ""))
        match = re.search(r"MSG-(\d+)", mid, re.IGNORECASE)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"MSG-{max_id + 1:04d}"


def detect_message_language(text: str) -> str:
    """Detect language (hindi, english, or hinglish) of message text."""
    lang = classify_text_language(text)
    if lang in {"hindi", "english", "hinglish"}:
        return lang
    if any("\u0900" <= c <= "\u097f" for c in text):
        return "hindi"
    return "english"


def is_duplicate_message(
    messages: list[dict],
    session_id: str,
    speaker: str,
    message_text: str,
    channel: str,
    window_seconds: float = 15.0,
) -> dict | None:
    """Detect if an identical message was written recently (WebSocket retry / repeated turn)."""
    norm_session = (session_id or "").strip()
    norm_speaker = (speaker or "").strip().lower()
    norm_text = (message_text or "").strip()
    norm_channel = (channel or "").strip().lower()
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))

    for msg in reversed(messages):
        if msg.get("session_id", "").strip() != norm_session:
            continue
        if msg.get("speaker", "").strip().lower() != norm_speaker:
            continue
        if msg.get("channel", "").strip().lower() != norm_channel:
            continue
        if msg.get("message_text", "").strip() == norm_text:
            # Check if within duplicate time window
            raw_ts = msg.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(raw_ts)
                if abs((now_ist - ts).total_seconds()) <= window_seconds:
                    return msg
            except Exception:
                return msg

    return None


def save_message(
    seller_id: str,
    session_id: str,
    speaker: str,
    message_text: str,
    channel: str = "text",
    language: str | None = None,
    timestamp: str | None = None,
    path: Path | None = None,
) -> dict:
    """Persist a single conversation message with validation, atomic write, and verification."""
    clean_text = str(message_text or "").strip()
    if not clean_text:
        return {
            "saved": False,
            "error": "empty_message",
            "message": "Message text cannot be empty or whitespace only.",
        }

    norm_speaker = str(speaker or "").strip().lower()
    if norm_speaker not in ALLOWED_SPEAKERS:
        return {
            "saved": False,
            "error": "invalid_speaker",
            "message": f"Speaker must be one of: {', '.join(sorted(ALLOWED_SPEAKERS))}.",
        }

    norm_channel = str(channel or "").strip().lower()
    if norm_channel not in ALLOWED_CHANNELS:
        return {
            "saved": False,
            "error": "invalid_channel",
            "message": f"Channel must be one of: {', '.join(sorted(ALLOWED_CHANNELS))}.",
        }

    norm_session = str(session_id or "").strip()
    if not norm_session:
        return {
            "saved": False,
            "error": "session_id_required",
            "message": "Session ID is required to save a message.",
        }

    norm_seller = normalize_seller_id(seller_id) or (
        str(seller_id).strip().upper() if seller_id else "SD-DEFAULT"
    )

    detected_lang = language or detect_message_language(clean_text)
    ts = timestamp or datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
    csv_path = path or get_conversations_csv_path()

    with _CONVERSATION_LOCK:
        try:
            messages = read_all_messages(csv_path)

            # Duplicate check
            duplicate = is_duplicate_message(
                messages=messages,
                session_id=norm_session,
                speaker=norm_speaker,
                message_text=clean_text,
                channel=norm_channel,
            )
            if duplicate:
                return {
                    "saved": False,
                    "duplicate": True,
                    "message_id": duplicate["message_id"],
                    "record": duplicate,
                    "message": f"Duplicate message {duplicate['message_id']} detected; skipped write.",
                }

            # Backfill: if we now have a real seller ID, update any earlier SD-DEFAULT rows in this session
            if norm_seller not in {"SD-DEFAULT", "UNKNOWN"}:
                for prev_msg in messages:
                    if (
                        prev_msg.get("session_id") == norm_session
                        and prev_msg.get("seller_id") in {"SD-DEFAULT", "UNKNOWN"}
                    ):
                        prev_msg["seller_id"] = norm_seller

            msg_id = next_message_id(messages)
            record = {
                "message_id": msg_id,
                "seller_id": norm_seller,
                "session_id": norm_session,
                "timestamp": ts,
                "speaker": norm_speaker,
                "message_text": clean_text,
                "language": detected_lang,
                "channel": norm_channel,
            }

            messages.append(record)
            write_all_messages(messages, csv_path)

            # Verification: Read back and confirm row on disk
            verified_messages = read_all_messages(csv_path)
            matching = [m for m in verified_messages if m.get("message_id") == msg_id]
            if not matching:
                raise IOError(f"Verification failed: message {msg_id} was not found on disk after write.")

            return {
                "saved": True,
                "duplicate": False,
                "message_id": msg_id,
                "record": matching[0],
                "message": f"Message {msg_id} successfully persisted.",
            }

        except Exception as exc:
            logger.exception("Failed to persist conversation message: %s", exc)
            return {
                "saved": False,
                "error": "storage_error",
                "message": f"Conversation message could not be persisted: {exc}",
            }


def get_conversation_history(
    session_id: str,
    seller_id: str | None = None,
    path: Path | None = None,
) -> list[dict]:
    """Retrieve all messages for a session in chronological order, enforcing seller isolation."""
    csv_path = path or get_conversations_csv_path()
    norm_session = str(session_id or "").strip()
    if not norm_session:
        return []

    norm_seller = normalize_seller_id(seller_id) if seller_id else None
    messages = read_all_messages(csv_path)

    results = []
    for msg in messages:
        if msg.get("session_id", "").strip() != norm_session:
            continue
        if norm_seller and norm_seller not in {"SD-DEFAULT", "UNKNOWN"}:
            msg_seller = msg.get("seller_id", "").strip().upper()
            if msg_seller not in {norm_seller, "SD-DEFAULT"}:
                continue
        results.append(msg)

    # Sort chronologically by timestamp
    results.sort(key=lambda m: m.get("timestamp", ""))
    return results


def get_seller_conversations(
    seller_id: str,
    path: Path | None = None,
) -> list[dict]:
    """Retrieve all conversation sessions for a seller without exposing other sellers' data."""
    csv_path = path or get_conversations_csv_path()
    norm_seller = normalize_seller_id(seller_id)
    if not norm_seller:
        return []

    messages = read_all_messages(csv_path)
    sessions: dict[str, list[dict]] = {}

    for msg in messages:
        if msg.get("seller_id", "").strip().upper() == norm_seller:
            sess_id = msg.get("session_id", "").strip()
            if sess_id:
                sessions.setdefault(sess_id, []).append(msg)

    result_sessions = []
    for sess_id, s_msgs in sessions.items():
        s_msgs.sort(key=lambda m: m.get("timestamp", ""))
        channels = {m.get("channel") for m in s_msgs if m.get("channel")}
        channel_str = "/".join(sorted(channels)) if channels else "text"
        result_sessions.append(
            {
                "session_id": sess_id,
                "seller_id": norm_seller,
                "message_count": len(s_msgs),
                "channel": channel_str,
                "start_time": s_msgs[0].get("timestamp") if s_msgs else "",
                "last_time": s_msgs[-1].get("timestamp") if s_msgs else "",
                "messages": s_msgs,
            }
        )

    # Sort sessions by last_time descending (most recent first)
    result_sessions.sort(key=lambda s: s.get("last_time", ""), reverse=True)
    return result_sessions
