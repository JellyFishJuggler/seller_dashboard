import csv
from datetime import datetime
import os
from pathlib import Path
import re
from threading import Lock
from typing import Literal
from zoneinfo import ZoneInfo

MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = MODULE_PATH.parents[2]
DEFAULT_ACTIONS_CSV = PROJECT_ROOT / "data" / "actions.csv"

_CUSTOM_CSV_PATH: Path | None = None
_STORE_LOCK = Lock()

CSV_FIELDS = [
    "action_id",
    "seller_id",
    "session_id",
    "action_type",
    "action_description",
    "related_product",
    "reminder_date",
    "reminder_time",
    "status",
    "seller_consent",
    "created_at",
    "updated_at",
    "notes",
]

VALID_STATUSES = {"Pending", "Completed", "Cancelled"}


def get_actions_csv_path() -> Path:
    """Return the active CSV path, respecting custom paths and environment overrides."""
    if _CUSTOM_CSV_PATH is not None:
        return _CUSTOM_CSV_PATH
    env_path = os.getenv("ACTIONS_CSV_PATH")
    if env_path:
        return Path(env_path).resolve()
    return DEFAULT_ACTIONS_CSV


def set_actions_csv_path(path: Path | str | None) -> None:
    """Override the actions CSV path, useful for testing with isolated temporary files."""
    global _CUSTOM_CSV_PATH
    if path is None:
        _CUSTOM_CSV_PATH = None
    else:
        _CUSTOM_CSV_PATH = Path(path).resolve()


def ensure_csv_file(path: Path | None = None) -> Path:
    """Ensure the CSV file exists with proper utf-8-sig BOM and headers."""
    csv_path = path or get_actions_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.is_file() or csv_path.stat().st_size == 0:
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
    return csv_path


def read_all_actions(path: Path | None = None) -> list[dict]:
    """Read all action records from the CSV file using utf-8-sig encoding."""
    csv_path = ensure_csv_file(path)
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def write_all_actions(actions: list[dict], path: Path | None = None) -> bool:
    """Write action records to CSV atomically using utf-8-sig encoding."""
    csv_path = path or get_actions_csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = csv_path.with_name(f"{csv_path.name}.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for action in actions:
                row = {field: str(action.get(field, "") or "") for field in CSV_FIELDS}
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


def next_action_id(actions: list[dict]) -> str:
    """Generate the next unique action ID (e.g. ACT-001, ACT-002)."""
    max_id = 0
    for action in actions:
        action_id = action.get("action_id", "")
        match = re.search(r"ACT-(\d+)", str(action_id), re.IGNORECASE)
        if match:
            max_id = max(max_id, int(match.group(1)))
    return f"ACT-{max_id + 1:03d}"


def find_duplicate_action(
    actions: list[dict],
    seller_id: str,
    session_id: str,
    action_type: str,
    reminder_date: str,
    action_description: str,
    related_product: str = "",
) -> dict | None:
    """Detect if an identical pending action already exists."""
    norm_seller = (seller_id or "").strip().upper()
    norm_session = (session_id or "").strip()
    norm_type = (action_type or "").strip().lower()
    norm_date = (reminder_date or "").strip()
    norm_desc = (action_description or "").strip().lower()
    norm_prod = (related_product or "").strip().lower()

    for action in actions:
        existing_status = action.get("status", "").strip().title()
        if existing_status != "Pending":
            continue

        existing_session = action.get("session_id", "").strip()
        existing_seller = action.get("seller_id", "").strip().upper()
        existing_type = action.get("action_type", "").strip().lower()
        existing_date = action.get("reminder_date", "").strip()
        existing_desc = action.get("action_description", "").strip().lower()
        existing_prod = action.get("related_product", "").strip().lower()

        if existing_type != norm_type or existing_date != norm_date:
            continue

        # Case 1: Same session retry (same request processed twice in a session)
        if norm_session and existing_session == norm_session:
            if (norm_prod and existing_prod and norm_prod == existing_prod) or (norm_desc == existing_desc):
                return action

        # Case 2: Same registered seller (excluding generic anonymous fallback)
        if norm_seller and norm_seller not in {"SD-DEFAULT", "UNKNOWN"}:
            if existing_seller == norm_seller:
                if norm_prod and existing_prod:
                    if norm_prod == existing_prod:
                        return action
                elif norm_desc == existing_desc:
                    return action

    return None


def persist_action(
    seller_id: str,
    session_id: str,
    action_type: str,
    action_description: str,
    reminder_date: str,
    seller_consent: str,
    related_product: str = "",
    reminder_time: str = "",
    notes: str = "",
    status: str = "Pending",
    path: Path | None = None,
) -> dict:
    """Save an action record to CSV with concurrency locking, verification, and duplicate check."""
    csv_path = path or get_actions_csv_path()

    with _STORE_LOCK:
        actions = read_all_actions(csv_path)

        # Check for duplicates
        duplicate = find_duplicate_action(
            actions=actions,
            seller_id=seller_id,
            session_id=session_id,
            action_type=action_type,
            reminder_date=reminder_date,
            action_description=action_description,
            related_product=related_product,
        )
        if duplicate:
            return {
                "saved": False,
                "duplicate": True,
                "action_id": duplicate["action_id"],
                "record": duplicate,
                "message": (
                    f"A pending action with ID {duplicate['action_id']} already exists "
                    f"for this seller and date ({duplicate['reminder_date']}). Duplicate action was not created."
                ),
            }

        # Generate unique action ID
        action_id = next_action_id(actions)
        now_iso = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

        record = {
            "action_id": action_id,
            "seller_id": seller_id,
            "session_id": session_id,
            "action_type": action_type,
            "action_description": action_description,
            "related_product": related_product,
            "reminder_date": reminder_date,
            "reminder_time": reminder_time,
            "status": status.strip().title() if status else "Pending",
            "seller_consent": seller_consent,
            "created_at": now_iso,
            "updated_at": now_iso,
            "notes": notes,
        }

        actions.append(record)
        write_all_actions(actions, csv_path)

        # Verification: Read back and verify record is present in CSV
        verified_actions = read_all_actions(csv_path)
        matching = [a for a in verified_actions if a.get("action_id") == action_id]
        if not matching:
            raise IOError(f"Verification failed: action {action_id} not found in CSV after write.")

        verified_record = matching[0]
        return {
            "saved": True,
            "duplicate": False,
            "action_id": action_id,
            "record": verified_record,
        }


def update_action_status_record(
    action_id: str,
    new_status: str,
    seller_id: str | None = None,
    notes: str = "",
    path: Path | None = None,
) -> dict:
    """Update status of an action (Pending, Completed, Cancelled) with seller isolation check."""
    normalized_status = new_status.strip().title()
    if normalized_status not in VALID_STATUSES:
        return {
            "updated": False,
            "error": "invalid_status",
            "message": f"Invalid status '{new_status}'. Status must be one of: {', '.join(sorted(VALID_STATUSES))}.",
        }

    csv_path = path or get_actions_csv_path()

    with _STORE_LOCK:
        actions = read_all_actions(csv_path)
        target = None
        target_idx = -1

        for idx, action in enumerate(actions):
            if action.get("action_id", "").strip().upper() == action_id.strip().upper():
                target = action
                target_idx = idx
                break

        if target is None:
            return {
                "updated": False,
                "error": "not_found",
                "message": f"Action with ID '{action_id}' was not found.",
            }

        # Seller isolation check
        if seller_id:
            norm_seller = seller_id.strip().upper()
            if target.get("seller_id", "").strip().upper() != norm_seller:
                return {
                    "updated": False,
                    "error": "unauthorized",
                    "message": "Cannot update action belonging to another seller.",
                }

        now_iso = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()
        target["status"] = normalized_status
        target["updated_at"] = now_iso
        if notes:
            existing_notes = target.get("notes", "").strip()
            if existing_notes:
                target["notes"] = f"{existing_notes}; {notes.strip()}"
            else:
                target["notes"] = notes.strip()

        actions[target_idx] = target
        write_all_actions(actions, csv_path)

        # Verification step
        verified_actions = read_all_actions(csv_path)
        matching = [a for a in verified_actions if a.get("action_id") == target["action_id"]]
        if not matching or matching[0].get("status") != normalized_status:
            raise IOError(f"Verification failed: action {action_id} status update not confirmed in CSV.")

        return {
            "updated": True,
            "action_id": target["action_id"],
            "status": normalized_status,
            "updated_at": now_iso,
            "record": matching[0],
            "message": f"Action {target['action_id']} status successfully updated to {normalized_status}.",
        }


def get_actions_by_seller(
    seller_id: str,
    status: str | None = None,
    session_id: str | None = None,
    path: Path | None = None,
) -> list[dict]:
    """Retrieve actions strictly isolated to a seller, optionally filtered by status or session."""
    csv_path = path or get_actions_csv_path()
    norm_seller = (seller_id or "").strip().upper()
    if not norm_seller:
        return []

    actions = read_all_actions(csv_path)
    results = []

    norm_status = status.strip().title() if status else None
    norm_session = session_id.strip() if session_id else None

    for action in actions:
        if action.get("seller_id", "").strip().upper() != norm_seller:
            continue
        if norm_status and action.get("status", "").strip().title() != norm_status:
            continue
        if norm_session and action.get("session_id", "").strip() != norm_session:
            continue
        results.append(action)

    return results


def get_actions_by_session(
    session_id: str,
    seller_id: str | None = None,
    path: Path | None = None,
) -> list[dict]:
    """Retrieve actions for a given session, ensuring seller isolation if seller_id is supplied."""
    csv_path = path or get_actions_csv_path()
    norm_session = (session_id or "").strip()
    if not norm_session:
        return []

    actions = read_all_actions(csv_path)
    results = []
    norm_seller = seller_id.strip().upper() if seller_id else None

    for action in actions:
        if action.get("session_id", "").strip() != norm_session:
            continue
        if norm_seller and action.get("seller_id", "").strip().upper() != norm_seller:
            continue
        results.append(action)

    return results
