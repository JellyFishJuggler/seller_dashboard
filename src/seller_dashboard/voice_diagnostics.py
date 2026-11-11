"""Safe, content-free diagnostics for the real-time voice pipeline."""
from __future__ import annotations

import json
import logging
from typing import Any


logger = logging.getLogger("seller_dashboard.voice")


class EmptyVoiceTextError(ValueError):
    """Raised when a required voice pipeline text value is absent or blank."""


class EmptyTranscriptError(EmptyVoiceTextError):
    pass


class EmptyAssistantResponseError(EmptyVoiceTextError):
    pass


class EmptyTTSInputError(EmptyVoiceTextError):
    pass


def text_status(value: Any) -> dict[str, Any]:
    if value is None:
        return {"text_exists": False, "text_length": 0, "text_state": "none"}
    if not isinstance(value, str):
        return {
            "text_exists": True,
            "text_length": len(value) if hasattr(value, "__len__") else 0,
            "text_state": "invalid_type",
        }
    if value == "":
        state = "empty"
    elif not value.strip():
        state = "whitespace"
    else:
        state = "present"
    return {"text_exists": bool(value), "text_length": len(value), "text_state": state}


def has_nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def clean_transcript(value: Any) -> str | None:
    """Return a stripped transcript, or None for absent/blank STT output."""
    return value.strip() if has_nonempty_text(value) else None


def extract_request_id(value: Any) -> str | None:
    """Read a request/correlation ID from SDK objects without logging payloads."""
    if value is None:
        return None
    candidates = [value]
    for attr in ("response_metadata", "metadata", "headers", "response"):
        nested = getattr(value, attr, None)
        if nested is not None:
            candidates.append(nested)
    for candidate in candidates:
        if isinstance(candidate, dict):
            for key in ("request_id", "requestId", "x-request-id", "X-Request-ID"):
                request_id = candidate.get(key)
                if request_id:
                    return str(request_id)
        else:
            for attr in ("request_id", "requestId"):
                request_id = getattr(candidate, attr, None)
                if request_id:
                    return str(request_id)
    return None


def log_text_boundary(
    service: str,
    session_id: str,
    text: Any,
    request_id: str | None = None,
    *,
    level: int = logging.INFO,
) -> None:
    record = {
        "service": service,
        "session_id": session_id,
        **text_status(text),
        "request_id": request_id or "unavailable",
    }
    logger.log(level, "voice_boundary %s", json.dumps(record, ensure_ascii=True))


def log_audio_boundary(
    service: str,
    session_id: str,
    byte_length: int,
    request_id: str | None = None,
    *,
    level: int = logging.DEBUG,
) -> None:
    record = {
        "service": service,
        "session_id": session_id,
        "text_exists": False,
        "text_length": 0,
        "text_state": "not_applicable",
        "audio_bytes": byte_length,
        "request_id": request_id or "unavailable",
    }
    logger.log(level, "voice_boundary %s", json.dumps(record, ensure_ascii=True))
