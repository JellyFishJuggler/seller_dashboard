"""Backend-only storage for an optional custom Sarvam API key.

The original ``.env`` key is never modified. A custom key is written to a
local JSON file on the backend and used in preference to the environment
key. The full key is never returned to the frontend or written to logs.

Storage layout
--------------
* Primary location: per-user OS application data OUTSIDE the project
  workspace (``%LOCALAPPDATA%\\seller_dashboard`` on Windows,
  ``$XDG_CONFIG_HOME/seller-dashboard`` elsewhere), so the key can never be
  served by a static dev server or committed by accident.
* Fallback location: the gitignored ``private/`` directory inside the
  project, used only when the primary location is not writable (locked-down
  or sandboxed environments). It is still outside the served frontend
  directory, and is consolidated into the primary location automatically
  as soon as that becomes writable.
* Legacy locations written by earlier versions of this app are still read
  and consolidated into the primary location once, without ever losing a
  saved key.

When several locations hold a key, the most recently saved one wins, so a
fresh save is never shadowed by an older copy left in a location the
backend cannot delete.
"""

from __future__ import annotations

import hmac
import json
import os
from pathlib import Path
from threading import RLock
import time

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

if os.name == "nt":
    _APP_DATA_ROOT = Path(
        os.getenv("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    )
    DEFAULT_CREDENTIALS_PATH = (
        _APP_DATA_ROOT / "seller_dashboard" / "sarvam_credentials.json"
    )
else:
    _APP_DATA_ROOT = Path(
        os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config"
    )
    DEFAULT_CREDENTIALS_PATH = (
        _APP_DATA_ROOT / "seller-dashboard" / "sarvam_credentials.json"
    )

# Used only when the primary location cannot be written (sandboxed or
# locked-down environments). Gitignored and outside the served frontend
# directory, so a static dev server such as Live Server cannot expose it.
FALLBACK_CREDENTIALS_PATH = _PROJECT_ROOT / "private" / "sarvam_credentials.json"

# Storage locations written by earlier versions of this app. They are read
# (and consolidated into the primary location once) but never written to
# unless the primary location is unwritable and they double as the fallback.
LEGACY_CREDENTIALS_PATHS = (
    FALLBACK_CREDENTIALS_PATH,
    _APP_DATA_ROOT / "SnapdealSellerAssistant" / "sarvam_credentials.json",
    Path.home() / ".seller_dashboard" / "sarvam_credentials.json",
)

# Kept for backwards compatibility with older imports.
LEGACY_CREDENTIALS_PATH = Path.home() / ".seller_dashboard" / "sarvam_credentials.json"

MAX_KEY_LENGTH = 512
MASKED_KEY = "********"

# Reentrant: consolidation may run while set_custom_sarvam_api_key holds the
# lock, and must itself be atomic against concurrent saves.
_LOCK = RLock()
_CLIENT_KEY_INDEX: dict[str, int] = {}


def credentials_path() -> Path:
    """Return the configured credentials path (overridable for tests)."""
    override = os.getenv("SARVAM_CREDENTIALS_PATH")
    if override:
        return Path(override).expanduser()
    return DEFAULT_CREDENTIALS_PATH


def _uses_explicit_storage(path: Path | None) -> bool:
    """True when a single explicit path was requested (no fallback/legacy)."""
    return path is not None or bool(os.getenv("SARVAM_CREDENTIALS_PATH"))


def _storage_candidates(path: Path | None = None) -> list[Path]:
    """Return every location to read from, most authoritative first."""
    if path is not None:
        return [path]
    candidates = [credentials_path()]
    if not os.getenv("SARVAM_CREDENTIALS_PATH"):
        candidates.extend(LEGACY_CREDENTIALS_PATHS)
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def _read_custom_key_at(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    key = payload.get("api_key") if isinstance(payload, dict) else None
    if isinstance(key, str) and key.strip():
        return key.strip()
    return None


def _write_custom_key_at(path: Path, key: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["api_key"] = key
    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        temp_path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def _modification_time(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return float("-inf")


def _consolidate_into_primary(primary: Path, key: str, source_path: Path) -> None:
    """Move a key found in fallback/legacy storage into the primary location.

    Best effort and never destructive: the primary location is only written
    when it is empty, the copy is verified before any duplicate is removed,
    and an unwritable primary location is silently tolerated (the key keeps
    being read from where it is, and consolidation is retried later).
    """
    if source_path == primary:
        return
    with _LOCK:
        if _read_custom_key_at(primary) is not None:
            return
        try:
            _write_custom_key_at(primary, key)
        except OSError:
            return
        stored = _read_custom_key_at(primary)
        if stored is None or not hmac.compare_digest(stored, key):
            # Never remove the original unless the copy is verified intact.
            return
        # The primary location is now the single source of truth for this
        # key; verified duplicates are removed so no stale copy can win a
        # later mtime comparison.
        for duplicate in (source_path, *LEGACY_CREDENTIALS_PATHS):
            if duplicate == primary:
                continue
            if _read_custom_key_at(duplicate) == key:
                try:
                    duplicate.unlink()
                except OSError:
                    pass


def _read_custom_key(path: Path | None = None) -> str | None:
    candidates = _storage_candidates(path)
    if len(candidates) == 1:
        # Explicit path or SARVAM_CREDENTIALS_PATH override: exclusive.
        return _read_custom_key_at(candidates[0])

    # Default storage: the most recently saved key wins. Ties favour the
    # primary location, which is the canonical, most secure store.
    best_rank: tuple[float, int] | None = None
    winning_key: str | None = None
    winning_path: Path | None = None
    for index, candidate in enumerate(candidates):
        key = _read_custom_key_at(candidate)
        if key is None:
            continue
        rank = (_modification_time(candidate), -index)
        if best_rank is None or rank > best_rank:
            best_rank = rank
            winning_key = key
            winning_path = candidate
    if winning_key is None or winning_path is None:
        return None

    # Lazily move the winning key into the primary location so the app ends
    # up with a single key file outside the project workspace.
    _consolidate_into_primary(candidates[0], winning_key, winning_path)
    return winning_key


def get_sarvam_api_key(path: Path | None = None) -> str | None:
    """Return the custom key when present, otherwise the .env key."""
    custom_key = _read_custom_key(path)
    if custom_key:
        return custom_key
    return get_default_sarvam_api_key()


def get_default_sarvam_api_keys() -> list[str]:
    """Return configured deployment keys in priority order, without duplicates."""
    keys = []
    for name in ("SARVAM_API_KEY", "SARVAM_API_KEY_1", "SARVAM_API_KEY_2"):
        value = os.getenv(name)
        if value and value.strip() and value.strip() not in keys:
            keys.append(value.strip())
    return keys


def get_default_sarvam_api_key() -> str | None:
    """Return the first deployment key, never a browser-profile override."""
    keys = get_default_sarvam_api_keys()
    return keys[0] if keys else None


def _read_client_keys_at(path: Path) -> dict[str, dict[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    values = payload.get("client_keys", {}) if isinstance(payload, dict) else {}
    if not isinstance(values, dict):
        return {}
    return {
        session_id: item
        for session_id, item in values.items()
        if isinstance(session_id, str)
        and isinstance(item, dict)
        and isinstance(item.get("api_key"), str)
        and item["api_key"].strip()
    }


def _read_client_keys(path: Path | None = None) -> dict[str, dict[str, object]]:
    candidates = [path] if path is not None else _storage_candidates()
    merged: dict[str, dict[str, object]] = {}
    for candidate in candidates:
        for client_id, item in _read_client_keys_at(candidate).items():
            saved = merged.get(client_id)
            saved_at = item.get("updated_at", _modification_time(candidate))
            if not isinstance(saved_at, (int, float)):
                saved_at = _modification_time(candidate)
            previous_at = saved.get("updated_at", float("-inf")) if saved else float("-inf")
            if not isinstance(previous_at, (int, float)):
                previous_at = float("-inf")
            if saved is None or saved_at >= previous_at:
                merged[client_id] = item
    return merged


def _write_client_keys_at(
    path: Path,
    client_keys: dict[str, dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        current = {}
    payload = current if isinstance(current, dict) else {}
    payload["client_keys"] = client_keys
    temp_path = path.with_name(f"{path.name}.tmp")
    try:
        temp_path.write_text(json.dumps(payload), encoding="utf-8")
        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def get_client_sarvam_api_key(client_id: str) -> str | None:
    """Return this browser profile's override, falling back to deployment env."""
    keys = get_client_sarvam_api_keys(client_id)
    return keys[0] if keys else None


def get_client_sarvam_api_keys(client_id: str) -> list[str]:
    """Return this profile's custom key or its ordered deployment-key fallback."""
    normalized_client = (client_id or "").strip()
    if normalized_client:
        with _LOCK:
            saved = _read_client_keys().get(normalized_client)
        if saved:
            key = saved.get("api_key")
            if isinstance(key, str) and key.strip():
                return [key.strip()]

    keys = get_default_sarvam_api_keys()
    if normalized_client and len(keys) > 1:
        with _LOCK:
            start = _CLIENT_KEY_INDEX.get(normalized_client, 0) % len(keys)
        return keys[start:] + keys[:start]
    return keys


def is_sarvam_credential_error(error: BaseException) -> bool:
    """Identify API-key rejection or exhausted-account errors without logging details."""
    seen: set[int] = set()
    current: BaseException | None = error
    markers = (
        "invalid api key",
        "invalid_api_key",
        "invalid_subscription_key",
        "invalid subscription key",
        "unauthorized",
        "forbidden",
        "quota",
        "billing",
        "credits exhausted",
        "credit limit",
        "payment_required",
        "1003",
    )
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        status = getattr(current, "status_code", None)
        response = getattr(current, "response", None)
        status = status or getattr(response, "status_code", None)
        if status in {401, 402, 403}:
            return True
        message = f"{current} {getattr(current, 'code', '')}".lower()
        if any(marker in message for marker in markers):
            return True
        current = current.__cause__ or current.__context__
    return False


def advance_client_sarvam_api_key(client_id: str, failed_key: str) -> str | None:
    """Prefer the next deployment key after an authentication/quota failure."""
    normalized_client = (client_id or "").strip()
    if not normalized_client:
        return None
    with _LOCK:
        saved = _read_client_keys().get(normalized_client)
        if saved and saved.get("api_key") == failed_key:
            return None
        keys = get_default_sarvam_api_keys()
        if len(keys) < 2 or failed_key not in keys:
            return None
        next_index = (keys.index(failed_key) + 1) % len(keys)
        _CLIENT_KEY_INDEX[normalized_client] = next_index
        return keys[next_index]


def get_client_sarvam_key_status(client_id: str) -> dict:
    """Return masked credentials status for one browser profile."""
    normalized_client = (client_id or "").strip()
    with _LOCK:
        saved = _read_client_keys().get(normalized_client) if normalized_client else None
    if saved and isinstance(saved.get("api_key"), str):
        return {"configured": True, "source": "custom", "masked": MASKED_KEY}
    if get_default_sarvam_api_key():
        return {"configured": True, "source": "env", "masked": MASKED_KEY}
    return {"configured": False, "source": "none", "masked": ""}


def set_client_sarvam_api_key(client_id: str, api_key: str) -> dict:
    """Save or clear a private API-key override for one browser profile."""
    normalized_client = (client_id or "").strip()
    if not normalized_client or len(normalized_client) > 128 or any(
        character.isspace() for character in normalized_client
    ):
        raise ValueError("A valid browser profile ID is required.")

    key = (api_key or "").strip()
    if key and (any(character.isspace() for character in key) or len(key) > MAX_KEY_LENGTH):
        raise ValueError("API key must be a single value without spaces and at most 512 characters.")

    with _LOCK:
        client_keys = _read_client_keys()
        if key:
            client_keys[normalized_client] = {
                "api_key": key,
                "updated_at": time.time(),
            }
        else:
            client_keys.pop(normalized_client, None)
        _CLIENT_KEY_INDEX.pop(normalized_client, None)

        primary = credentials_path()
        try:
            _write_client_keys_at(primary, client_keys)
        except OSError:
            if _uses_explicit_storage(None):
                raise
            _write_client_keys_at(FALLBACK_CREDENTIALS_PATH, client_keys)

    return get_client_sarvam_key_status(normalized_client)


def get_sarvam_key_status(path: Path | None = None) -> dict:
    """Return non-sensitive key status for the settings UI."""
    custom_key = _read_custom_key(path)
    env_key = get_default_sarvam_api_key()
    if custom_key:
        source = "custom"
    elif env_key and env_key.strip():
        source = "env"
    else:
        source = "none"
    return {
        "configured": source != "none",
        "source": source,
        "masked": MASKED_KEY if source != "none" else "",
    }


def set_custom_sarvam_api_key(api_key: str, path: Path | None = None) -> dict:
    """Save a custom key, or clear it when the value is empty.

    Returns the masked status only. Raises ValueError for malformed input.
    With default storage, a save that cannot write the per-user primary
    location falls back to the gitignored ``private/`` directory inside the
    project so the feature keeps working in write-restricted environments;
    an explicit path (argument or ``SARVAM_CREDENTIALS_PATH``) never falls
    back and surfaces the write error instead.
    """
    key = (api_key or "").strip()
    if key and (any(character.isspace() for character in key) or len(key) > MAX_KEY_LENGTH):
        raise ValueError("API key must be a single value without spaces and at most 512 characters.")

    key_path = path or credentials_path()
    default_storage = not _uses_explicit_storage(path)
    with _LOCK:
        if not key:
            try:
                key_path.unlink()
            except FileNotFoundError:
                pass
            if default_storage:
                # Clearing must fully restore the .env fallback, so every
                # location that can hold a custom key is removed too.
                for legacy_path in LEGACY_CREDENTIALS_PATHS:
                    if legacy_path == key_path:
                        continue
                    try:
                        legacy_path.unlink()
                    except OSError:
                        pass
        else:
            write_path = key_path
            try:
                _write_custom_key_at(key_path, key)
            except OSError:
                if not default_storage:
                    raise
                # The per-user location is unwritable (sandboxed or locked
                # down environment): fall back to the project-private file.
                write_path = FALLBACK_CREDENTIALS_PATH
                _write_custom_key_at(write_path, key)
            if default_storage:
                # The write target is now the single source of truth; older
                # copies must not resurrect a previous key. Copies in
                # locations the backend cannot delete simply lose the mtime
                # comparison against this newer save.
                for legacy_path in LEGACY_CREDENTIALS_PATHS:
                    if legacy_path == write_path:
                        continue
                    try:
                        legacy_path.unlink()
                    except OSError:
                        pass

    # Default storage reads every location (the save may have landed in the
    # fallback); an explicit path reads exactly that path.
    return get_sarvam_key_status(None if default_storage else key_path)


def _read_client_key(client: object) -> str | None:
    wrapper = getattr(client, "_client_wrapper", None)
    client_key = getattr(wrapper, "api_subscription_key", None) if wrapper else None
    return client_key if isinstance(client_key, str) and client_key else None


def client_key_matches(client: object, active_key: str | None) -> bool | None:
    """Return whether a Sarvam SDK client holds the active key.

    Returns None when the client does not expose a readable credential. The
    key is only compared in memory and is never returned.
    """
    client_key = _read_client_key(client)
    if client_key is None:
        return None
    if not active_key:
        return False
    return hmac.compare_digest(client_key, active_key)


def build_sarvam_client_report(
    clients: dict[str, object],
    active_key: str | None,
) -> dict:
    """Build a key-free report describing which clients use the active key."""
    custom_key = _read_custom_key()
    env_keys = get_default_sarvam_api_keys()
    report: dict[str, dict] = {}
    stale_clients = []
    unknown_clients = []

    for name, client in clients.items():
        if client is None:
            report[name] = {
                "initialized": False,
                "credential_available": False,
                "matches_active_key": False,
                "key_source": "unknown",
            }
            stale_clients.append(name)
            continue

        matches = client_key_matches(client, active_key)
        client_key = _read_client_key(client)
        if client_key and custom_key and hmac.compare_digest(client_key, custom_key):
            key_source = "custom"
        elif client_key and any(
            hmac.compare_digest(client_key, env_key) for env_key in env_keys
        ):
            key_source = "environment"
        else:
            key_source = "unknown"
        report[name] = {
            "initialized": True,
            "credential_available": matches is not None,
            "matches_active_key": matches,
            "key_source": key_source,
        }
        if matches is False:
            stale_clients.append(name)
        elif matches is None:
            unknown_clients.append(name)

    return {
        "active_key_configured": bool(active_key),
        "clients": report,
        "all_clients_match_active_key": bool(active_key)
        and all(entry["matches_active_key"] is True for entry in report.values()),
        "stale_clients": stale_clients,
        "unknown_clients": unknown_clients,
    }
