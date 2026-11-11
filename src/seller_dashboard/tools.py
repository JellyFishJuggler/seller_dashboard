from threading import Lock
from datetime import date, datetime
import re
from typing import Literal
import unicodedata
from zoneinfo import ZoneInfo

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from seller_dashboard.action_store import (
    get_actions_by_seller,
    get_actions_by_session,
    persist_action,
    update_action_status_record,
)

# Findings and actions are kept in memory and backed by persistent CSV storage.
_SESSION_LOCK = Lock()
_SESSION_FINDINGS: dict[str, list[dict]] = {}
_SESSION_ACTIONS: dict[str, list[dict]] = {}
_SESSION_SELLER: dict[str, str] = {}
_ACTION_COUNTER = 0


def register_session_seller(thread_id: str, seller_id: str) -> None:
    """Associate a session/thread ID with a validated seller ID."""
    normalized = normalize_seller_id(seller_id)
    if normalized and is_known_seller(normalized):
        with _SESSION_LOCK:
            _SESSION_SELLER[str(thread_id)] = normalized


def get_session_seller(thread_id: str | None) -> str | None:
    """Return the seller ID registered for a session, if any."""
    if not thread_id:
        return None
    with _SESSION_LOCK:
        return _SESSION_SELLER.get(str(thread_id))


def is_known_seller(raw_seller_id: object) -> bool:
    """Check whether a seller ID resolves to a record in the seller dataset."""
    normalized = normalize_seller_id(raw_seller_id)
    return bool(normalized) and normalized in SELLERS


def _resolve_seller_id(
    config: RunnableConfig | None = None,
    thread_id: str | None = None,
    explicit_id: str | None = None,
) -> str:
    """Resolve the active seller ID from explicit argument, config, or session registry."""
    if explicit_id:
        normalized = normalize_seller_id(explicit_id)
        if normalized:
            return normalized

    configurable = (config or {}).get("configurable") or {}
    cfg_seller = configurable.get("seller_id")
    if cfg_seller:
        normalized = normalize_seller_id(cfg_seller)
        if normalized:
            return normalized

    if thread_id:
        with _SESSION_LOCK:
            known = _SESSION_SELLER.get(str(thread_id))
            if known:
                return known

    return "SD-DEFAULT"


def _extract_product_from_details(details: str) -> str:
    """Extract recognized product name from action details text if present."""
    if not details:
        return ""
    # Check known out-of-stock products across SELLERS dataset
    for seller in SELLERS.values():
        for product in seller.get("out_of_stock", []):
            pname = product.get("name", "")
            if pname and pname.lower() in details.lower():
                return pname

    # Check for capitalized product names (e.g. Cotton Casual Shirt)
    matches = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", details)
    for candidate in matches:
        if candidate.lower() not in {"virtual kam", "seller dashboard", "stock sync", "follow up"}:
            return candidate
    return ""


def _thread_id(config: RunnableConfig | None) -> str:
    configurable = (config or {}).get("configurable") or {}
    thread_id = configurable.get("thread_id")

    if thread_id is None or str(thread_id).strip() == "":
        return "default"

    return str(thread_id)


class Seller(BaseModel):
    seller_id: str | int = Field(
        ...,
        description=(
            "Seller identifier, not a number. Examples: 'SD-52077', '52077' or 52077. "
            "The SD- prefix is added automatically when it is missing."
        ),
    )


class OutOfStockQuery(Seller):
    onlyNew: bool = Field(
        True,
        description=(
            "True to list only products that went out of stock since last month. "
            "False to list every product that is currently out of stock."
        ),
    )


PLAYBOOK = {
    "inventory": {
        "goal": "Identify products that are out of stock and prioritize restocking.",
        "rules": [
            "Prioritize products with higher historical orders.",
            "Prioritize bestsellers that are newly out of stock.",
            "Check stock availability before recommending promotions.",
            "Avoid recommending restocking every product equally."
        ]
    },
    "cancellations": {
        "goal": "Identify products with unusually high cancellation rates.",
        "rules": [
            "Compare product-level cancellation rates.",
            "Check stock availability and fulfilment delays.",
            "Distinguish seller-side issues from customer cancellations.",
            "Do not assume every cancellation is caused by stockouts."
        ]
    },
    "pricing": {
        "goal": "Analyze changes in average selling price and their possible impact.",
        "rules": [
            "Compare current and previous month ASP.",
            "Compare ASP movement with order volume.",
            "Do not treat ASP as profit margin.",
            "Recommend reviewing competitor pricing and costs before changing prices."
        ]
    },
    "visibility": {
        "goal": "Improve product discoverability.",
        "rules": [
            "Review product titles and descriptions.",
            "Check product images and category mapping.",
            "Ensure listings are active and correctly categorized."
        ]
    },
    "sales": {
        "goal": "Diagnose sales performance changes.",
        "rules": [
            "Compare sales, orders, ASP and cancellations.",
            "Check stockouts before attributing sales decline to demand.",
            "Separate observed metrics from possible explanations."
        ]
    }
}

SELLERS = {

    "SD-48213": {
        "seller_id": "SD-48213",
        "seller_name": "Rajesh",
        "business_name": "Rajesh Garments",
        "category": "Women's ethnic wear",

        "metrics_source": "seller_records",
        "list_source": "seller_records",
        "cancellations_source": "seller_records",

        "metrics": {
            "last_month": {
                "sales": 200000,
                "orders": 400,
                "cancellation_rate": 8,
                "asp": 500,
                "out_of_stock_products": 5
            },
            "this_month": {
                "sales": 135000,
                "orders": 270,
                "cancellation_rate": 14,
                "asp": 500,
                "out_of_stock_products": 18
            }
        },

        "out_of_stock": [
            {"sku": "KRT-001", "name": "Printed Cotton Kurti", "last_month_orders": 28, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "KRT-014", "name": "Anarkali Kurta Set", "last_month_orders": 19, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "LEG-007", "name": "Churidar Leggings", "last_month_orders": 16, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "DUP-003", "name": "Cotton Dupatta", "last_month_orders": 12, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "KRT-022", "name": "Straight Fit Kurti", "last_month_orders": 9, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "PLZ-005", "name": "Palazzo Pants", "last_month_orders": 8, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "KRT-031", "name": "Embroidered Kurti", "last_month_orders": 7, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "SET-002", "name": "Kurti Pant Set", "last_month_orders": 7, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "DUP-011", "name": "Chiffon Dupatta", "last_month_orders": 6, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "LEG-012", "name": "Ankle Leggings", "last_month_orders": 6, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "TOP-004", "name": "Cotton Tunic", "last_month_orders": 5, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "SKT-001", "name": "A-Line Skirt", "last_month_orders": 4, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "STL-003", "name": "Printed Stole", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "KRT-009", "name": "Linen Kurti", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "LEG-003", "name": "Printed Leggings", "last_month_orders": 2, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "SET-007", "name": "Cotton Co-ord Set", "last_month_orders": 2, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "DUP-006", "name": "Silk Dupatta", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "TOP-009", "name": "Crop Top", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False}
        ],

        "product_cancellations": [
            {
                "product_id": "KRT-001",
                "product_name": "Printed Cotton Kurti",
                "total_orders": 28,
                "cancelled_orders": 9,
                "cancellation_reasons": {
                    "seller_cancelled": 2,
                    "customer_cancelled": 1,
                    "stock_issue": 6,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "KRT-014",
                "product_name": "Anarkali Kurta Set",
                "total_orders": 19,
                "cancelled_orders": 6,
                "cancellation_reasons": {
                    "seller_cancelled": 1,
                    "customer_cancelled": 1,
                    "stock_issue": 4,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "LEG-007",
                "product_name": "Churidar Leggings",
                "total_orders": 16,
                "cancelled_orders": 4,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 1,
                    "stock_issue": 3,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "DUP-003",
                "product_name": "Cotton Dupatta",
                "total_orders": 12,
                "cancelled_orders": 3,
                "cancellation_reasons": {
                    "seller_cancelled": 1,
                    "customer_cancelled": 0,
                    "stock_issue": 2,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "KRT-022",
                "product_name": "Straight Fit Kurti",
                "total_orders": 9,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 0,
                    "stock_issue": 1,
                    "fulfilment_delay": 1
                },
                "reason_source": "seller_records"
            }
        ]
    },


    "SD-52077": {
        "seller_id": "SD-52077",
        "seller_name": "Meena",
        "business_name": "Meena Home Decor",
        "category": "Home decor",

        "metrics_source": "seller_records",
        "list_source": "seller_records",
        "cancellations_source": "seller_records",

        "metrics": {
            "last_month": {
                "sales": 150000,
                "orders": 300,
                "cancellation_rate": 5,
                "asp": 500,
                "out_of_stock_products": 3
            },
            "this_month": {
                "sales": 124000,
                "orders": 310,
                "cancellation_rate": 5,
                "asp": 400,
                "out_of_stock_products": 4
            }
        },

        "out_of_stock": [
            {"sku": "DEC-004", "name": "Ceramic Flower Vase", "last_month_orders": 6, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "DEC-011", "name": "Wall Clock", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "DEC-002", "name": "Scented Candle Set", "last_month_orders": 2, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "DEC-019", "name": "Photo Frame Set", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False}
        ],

        "product_cancellations": [
            {
                "product_id": "DEC-004",
                "product_name": "Ceramic Flower Vase",
                "total_orders": 40,
                "cancelled_orders": 3,
                "cancellation_reasons": {
                    "seller_cancelled": 1,
                    "customer_cancelled": 0,
                    "stock_issue": 2,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "DEC-011",
                "product_name": "Wall Clock",
                "total_orders": 55,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 2,
                    "stock_issue": 0,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "DEC-002",
                "product_name": "Scented Candle Set",
                "total_orders": 45,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 1,
                    "stock_issue": 0,
                    "fulfilment_delay": 1
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "DEC-019",
                "product_name": "Photo Frame Set",
                "total_orders": 30,
                "cancelled_orders": 1,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 0,
                    "stock_issue": 0,
                    "fulfilment_delay": 1
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "DEC-025",
                "product_name": "Decorative Table Lamp",
                "total_orders": 35,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 2,
                    "stock_issue": 0,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            }
        ]
    },


    "SD-63190": {
        "seller_id": "SD-63190",
        "seller_name": "Arjun",
        "business_name": "Arjun Mobile Accessories",
        "category": "Mobile accessories",

        "metrics_source": "seller_records",
        "list_source": "seller_records",
        "cancellations_source": "seller_records",

        "metrics": {
            "last_month": {
                "sales": 210000,
                "orders": 350,
                "cancellation_rate": 6,
                "asp": 600,
                "out_of_stock_products": 2
            },
            "this_month": {
                "sales": 180000,
                "orders": 300,
                "cancellation_rate": 19,
                "asp": 600,
                "out_of_stock_products": 3
            }
        },

        "out_of_stock": [
            {"sku": "ACC-007", "name": "20W Fast Charger", "last_month_orders": 9, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "ACC-015", "name": "Braided Cable 2m", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "ACC-021", "name": "Phone Stand", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False}
        ],

        "product_cancellations": [
            {
                "product_id": "ACC-007",
                "product_name": "20W Fast Charger",
                "total_orders": 45,
                "cancelled_orders": 10,
                "cancellation_reasons": {
                    "seller_cancelled": 3,
                    "customer_cancelled": 1,
                    "stock_issue": 6,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "ACC-015",
                "product_name": "Braided Cable 2m",
                "total_orders": 35,
                "cancelled_orders": 7,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 2,
                    "stock_issue": 0,
                    "fulfilment_delay": 5
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "ACC-021",
                "product_name": "Phone Stand",
                "total_orders": 30,
                "cancelled_orders": 5,
                "cancellation_reasons": {
                    "seller_cancelled": 2,
                    "customer_cancelled": 3,
                    "stock_issue": 0,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "ACC-030",
                "product_name": "Wireless Earbuds",
                "total_orders": 50,
                "cancelled_orders": 8,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 0,
                    "stock_issue": 3,
                    "fulfilment_delay": 5
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "ACC-042",
                "product_name": "USB-C Charging Cable",
                "total_orders": 40,
                "cancelled_orders": 6,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 4,
                    "stock_issue": 0,
                    "fulfilment_delay": 2
                },
                "reason_source": "seller_records"
            }
        ]
    },


    "SD-12345": {
        "seller_id": "SD-12345",
        "seller_name": "Srijan",
        "business_name": "Srijan Apparel Studio",
        "category": "Apparel",

        "metrics_source": "seller_records",
        "list_source": "seller_records",
        "cancellations_source": "seller_records",

        "metrics": {
            "last_month": {
                "sales": 150000,
                "orders": 300,
                "cancellation_rate": 5,
                "asp": 500,
                "out_of_stock_products": 3
            },
            "this_month": {
                "sales": 124000,
                "orders": 310,
                "cancellation_rate": 5,
                "asp": 400,
                "out_of_stock_products": 4
            }
        },

        "out_of_stock": [
            {"sku": "APP-001", "name": "Cotton Casual Shirt", "last_month_orders": 6, "bestseller": True, "newly_out_of_stock": True},
            {"sku": "APP-008", "name": "Slim Fit Denim Jeans", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "APP-014", "name": "Graphic Printed T-Shirt", "last_month_orders": 2, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "APP-021", "name": "Men's Formal Chinos", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False}
        ],

        "product_cancellations": [
            {
                "product_id": "APP-001",
                "product_name": "Cotton Casual Shirt",
                "total_orders": 45,
                "cancelled_orders": 3,
                "cancellation_reasons": {
                    "seller_cancelled": 1,
                    "customer_cancelled": 0,
                    "stock_issue": 2,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "APP-008",
                "product_name": "Slim Fit Denim Jeans",
                "total_orders": 40,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 2,
                    "stock_issue": 0,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "APP-014",
                "product_name": "Graphic Printed T-Shirt",
                "total_orders": 35,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 1,
                    "stock_issue": 0,
                    "fulfilment_delay": 1
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "APP-021",
                "product_name": "Men's Formal Chinos",
                "total_orders": 30,
                "cancelled_orders": 1,
                "cancellation_reasons": {
                    "seller_cancelled": 0,
                    "customer_cancelled": 0,
                    "stock_issue": 0,
                    "fulfilment_delay": 1
                },
                "reason_source": "seller_records"
            },
            {
                "product_id": "APP-035",
                "product_name": "Casual Printed Hoodie",
                "total_orders": 35,
                "cancelled_orders": 2,
                "cancellation_reasons": {
                    "seller_cancelled": 1,
                    "customer_cancelled": 1,
                    "stock_issue": 0,
                    "fulfilment_delay": 0
                },
                "reason_source": "seller_records"
            }
        ]
    }
}


_SELLER_ID_DIGIT_WORDS = {
    "zero": "0", "oh": "0", "shunya": "0", "shoonya": "0", "शून्य": "0",
    "जीरो": "0", "ज़ीरो": "0",
    "one": "1", "ek": "1", "एक": "1", "वन": "1",
    "two": "2", "do": "2", "दो": "2", "टू": "2",
    "three": "3", "teen": "3", "tin": "3", "तीन": "3", "थ्री": "3",
    "four": "4", "char": "4", "chaar": "4", "चार": "4", "फोर": "4",
    "five": "5", "panch": "5", "paanch": "5", "पांच": "5", "पाँच": "5", "फाइव": "5",
    "six": "6", "chhe": "6", "chhah": "6", "छह": "6", "छः": "6", "सिक्स": "6",
    "seven": "7", "saat": "7", "sat": "7", "सात": "7", "सेवन": "7",
    "eight": "8", "aath": "8", "आठ": "8", "एट": "8",
    "nine": "9", "nau": "9", "नौ": "9", "नाइन": "9",
}
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")


def _spoken_seller_id_digits(value: str) -> str | None:
    """Convert a complete spoken sequence of digits to its numeric form."""
    candidate = unicodedata.normalize("NFKC", value).translate(_DEVANAGARI_DIGITS).casefold().strip()
    candidate = re.sub(
        r"^(?:(?:my|the)\s+)?seller\s*(?:id|identifier)|^unique\s*id",
        "",
        candidate,
        flags=re.IGNORECASE,
    )
    candidate = re.sub(r"^\s*(?:is|:|=)\s*", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"^\s*sd\s*-\s*", "", candidate, flags=re.IGNORECASE)
    candidate = candidate.strip(" \t\r\n.,!?;:'\"`()[]{}<>|/\\-_।")

    if re.fullmatch(r"\d+(?:[\s,.-]+\d+)*", candidate):
        return re.sub(r"\D", "", candidate)

    tokens = [token.strip(".,!?;:'\"`()[]{}<>|/\\-_।") for token in candidate.split()]
    tokens = [token for token in tokens if token]
    if len(tokens) < 4 or any(token not in _SELLER_ID_DIGIT_WORDS for token in tokens):
        return None
    return "".join(_SELLER_ID_DIGIT_WORDS[token] for token in tokens)


def normalize_seller_id(value: object) -> str | None:
    """Normalise a seller identifier without ever changing the seller dataset.

    ``52077``, ``"52077"``, ``"sd-52077"`` and ``" SD-52077 "`` all become
    ``"SD-52077"``. Returns ``None`` when no usable identifier was supplied.
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    raw_text = str(value).strip()
    spoken_digits = _spoken_seller_id_digits(raw_text)
    text = (spoken_digits or raw_text).upper().replace(" ", "")

    if not text:
        return None

    if text.startswith("SD-"):
        text = text[3:]
    elif text.startswith("SD"):
        text = text[2:].lstrip("-")

    text = text.lstrip("-")

    if not text:
        return None

    return f"SD-{text}"


def _lookup_seller(raw_seller_id: object) -> tuple[str | None, dict | None, dict | None]:
    """Resolve a seller ID to a read-only seller profile record."""
    normalized = normalize_seller_id(raw_seller_id)

    if normalized is None:
        return None, None, {
            "error": True,
            "code": "seller_id_required",
            "message": (
                "A seller ID is required. Ask the seller for their Snapdeal "
                "seller ID (for example SD-52077)."
            ),
        }

    seller = SELLERS.get(normalized)

    if seller is None:
        return normalized, None, {
            "error": True,
            "code": "seller_not_found",
            "message": (
                f"No seller record was found for seller ID '{raw_seller_id}' "
                f"(normalised to '{normalized}'). Ask the seller to check their "
                "seller ID. Do not invent seller data."
            ),
        }

    return normalized, seller, None


def _format_inr(amount: int | float) -> str:
    """Format a number with the rupee symbol and Indian digit grouping."""
    sign = "-" if amount < 0 else ""
    digits = str(int(round(abs(amount))))

    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []

        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]

        if head:
            groups.insert(0, head)

        digits = ",".join(groups + [tail])

    return f"{sign}₹{digits}"


def _percent_change(old: int | float, new: int | float) -> float | None:
    if not old:
        return None

    return round((new - old) / old * 100, 1)


def _format_pct(value: float | None) -> str:
    if value is None:
        return "n/a"

    return f"{value:+.1f}%"


def _month_view(month: dict) -> dict:
    """Copy a month's aggregate metrics and add display-only currency values."""
    view = dict(month)
    view["sales_display"] = _format_inr(month["sales"])
    view["avg_selling_price_display"] = _format_inr(month["avg_selling_price"])
    return view


def _normalise_month(month: object) -> dict:
    """Map the current seller dataset fields to the tool's public response keys.

    The current dataset stores ``metrics.last_month`` / ``metrics.this_month``
    with ``asp`` and ``cancellation_rate``. The public tool contract has always
    used ``avg_selling_price`` and ``cancellation_rate_pct``, so normalise here
    instead of changing callers or the response shape.
    """
    if not isinstance(month, dict):
        raise ValueError("Month metrics must be a mapping.")

    values = {
        "sales": month.get("sales"),
        "orders": month.get("orders"),
        "avg_selling_price": month.get("avg_selling_price", month.get("asp")),
        "cancellation_rate_pct": month.get(
            "cancellation_rate_pct", month.get("cancellation_rate")
        ),
        "out_of_stock_products": month.get("out_of_stock_products"),
    }

    missing = [
        key for key, value in values.items()
        if not isinstance(value, (int, float)) or isinstance(value, bool)
    ]
    if missing:
        raise ValueError(f"Missing numeric month metrics: {', '.join(missing)}")

    # The previous dataset exposed this field as a float (for example 6.0),
    # and downstream prompts/tests format it with one decimal place.
    values["cancellation_rate_pct"] = float(values["cancellation_rate_pct"])

    return values


def _seller_months(seller: dict) -> tuple[dict, dict]:
    """Return normalised last/this month metrics for current and legacy records."""
    metrics = seller.get("metrics")
    if not isinstance(metrics, dict):
        # Backward compatibility for any older flat seller record.
        metrics = seller
    return (
        _normalise_month(metrics.get("last_month")),
        _normalise_month(metrics.get("this_month")),
    )


@tool(args_schema=Seller)
def get_seller_metrics(seller_id: str | int) -> dict:
    """Get monthly aggregate seller metrics using the seller's unique ID.

    Get the seller's business numbers for last month and this month, with the
    changes already calculated.

    Call this when the seller asks about business performance, sales, orders,
    average selling price or cancellations, or when these metrics are needed to
    diagnose a stated concern. Reuse results already present in the current
    conversation unless the seller asks for a fresh check or changes the period.

    This returns monthly totals only: sales, orders, cancellation rate, average
    selling price and the COUNT of out-of-stock products. Use sales, orders and
    average selling price together when diagnosing sales changes. It does NOT return
    individual products, SKUs, names or which products are out of stock. Never
    infer product-level details from these aggregate figures. Call
    get_out_of_stock_products when individual product information is needed.

    All monetary values are in Indian Rupees (₹). Never use dollars or convert
    the currency. Use the figures exactly as returned. Never recalculate or guess
    a number that is not in the result.

    The data has no traffic, visibility, ratings or competitor prices. If the
    seller asks about those, say you do not have that data and ask them instead.

    Args:
        seller_id: Seller identifier, not a number. 'SD-52077', '52077' and
            52077 are all accepted and resolved to the same seller.
    """
    normalized, seller, error = _lookup_seller(seller_id)

    if error is not None:
        return error

    try:
        last_month, this_month = _seller_months(seller)
    except ValueError:
        return {
            "error": True,
            "code": "seller_metrics_unavailable",
            "message": (
                f"Seller metrics for '{normalized}' are incomplete or invalid. "
                "No values were inferred or invented."
            ),
        }

    sales_pct = _percent_change(last_month["sales"], this_month["sales"])
    orders_pct = _percent_change(last_month["orders"], this_month["orders"])
    avg_selling_price_pct = _percent_change(
        last_month["avg_selling_price"], this_month["avg_selling_price"]
    )
    cancellation_rate_pp = round(
        this_month["cancellation_rate_pct"] - last_month["cancellation_rate_pct"], 1
    )
    out_of_stock_change = (
        this_month["out_of_stock_products"] - last_month["out_of_stock_products"]
    )

    return {
        "seller_id": normalized,
        "name": seller.get("seller_name") or seller.get("name") or normalized,
        "business": seller.get("business_name") or seller.get("business") or "",
        "category": seller.get("category", ""),
        "currency": "INR",
        "currency_symbol": "₹",
        "last_month": _month_view(last_month),
        "this_month": _month_view(this_month),
        "changes": {
            "sales": this_month["sales"] - last_month["sales"],
            "sales_display": _format_inr(this_month["sales"] - last_month["sales"]),
            "sales_pct": sales_pct,
            "orders": this_month["orders"] - last_month["orders"],
            "orders_pct": orders_pct,
            "cancellation_rate_pp": cancellation_rate_pp,
            "avg_selling_price_pct": avg_selling_price_pct,
            "out_of_stock_products": out_of_stock_change,
        },
        "summary": (
            f"Sales {_format_pct(sales_pct)} "
            f"({_format_inr(last_month['sales'])} to {_format_inr(this_month['sales'])}). "
            f"Orders {_format_pct(orders_pct)}. "
            f"Average selling price {_format_pct(avg_selling_price_pct)}. "
            f"Cancellation rate {cancellation_rate_pp:+.1f} percentage points. "
            f"Out-of-stock count {out_of_stock_change:+d}."
        ),
        "note": (
            "Monthly aggregate metrics only. This response does not contain "
            "individual product details. The out-of-stock count is a total: it "
            "does not identify products or prove that stock caused the sales "
            "change. Call get_out_of_stock_products before discussing individual "
            "products or linking the sales change to stock."
        ),
    }


@tool(args_schema=OutOfStockQuery)
def get_out_of_stock_products(seller_id: str | int, onlyNew: bool = True) -> dict:
    """List individual out-of-stock products with last month's orders for each.

    Call this for a relevant inventory/stockout concern, or when rising
    cancellations coincide with a higher out-of-stock count. Call it before
    naming, listing, ranking or describing any specific out-of-stock product.
    get_seller_metrics gives only an aggregate count and must never be used to
    infer product-level details.

    onlyNew=True returns only products that went out of stock since last month.
    These are the likely contributors to a recent stock change. onlyNew=False
    returns every product that is currently out of stock. Keep these two results
    clearly distinct when speaking to the seller.

    Returns each product's name, SKU, last month's orders and whether it was a
    bestseller. Use only what is returned and never invent products or numbers.
    This shows where orders were likely lost; it does not prove it, so say
    "likely".

    Args:
        seller_id: Seller identifier, with or without the SD- prefix.
        onlyNew: True to list only products that went out of stock since last
            month. False to list every out-of-stock product.
    """
    normalized, seller, error = _lookup_seller(seller_id)

    if error is not None:
        return error

    products = seller["out_of_stock"]
    filtered_products = []

    for product in products:
        if onlyNew and not product["newly_out_of_stock"]:
            continue

        filtered_products.append(
            {
                "sku": product["sku"],
                "name": product["name"],
                "last_month_orders": product["last_month_orders"],
                "bestseller": product["bestseller"],
                "newly_out_of_stock": product["newly_out_of_stock"],
            }
        )

    newly_out_of_stock_count = sum(
        1 for product in products if product["newly_out_of_stock"]
    )
    bestseller_count = sum(1 for product in filtered_products if product["bestseller"])
    total_orders_last_month = sum(
        product["last_month_orders"] for product in filtered_products
    )
    list_label = "newly out-of-stock" if onlyNew else "currently out-of-stock"

    return {
        "seller_id": normalized,
        "only_new": onlyNew,
        "products": filtered_products,
        "total_products": len(filtered_products),
        "bestseller_count": bestseller_count,
        "total_out_of_stock_products": len(products),
        "newly_out_of_stock_products": newly_out_of_stock_count,
        "previously_out_of_stock_products": len(products) - newly_out_of_stock_count,
        "total_orders_last_month": total_orders_last_month,
        "summary": (
            f"{len(filtered_products)} {list_label} products. "
            f"{bestseller_count} were bestsellers last month. "
            f"These products had {total_orders_last_month} orders last month in total."
        ),
        "note": (
            "Orders are from last month. New stock-outs are likely contributors "
            "to a recent change, but they do not prove the cause."
        ),
    }


@tool(args_schema=Seller)
def get_cancellation_breakdown(seller_id: str | int) -> dict:
    """Get the seller's cancellations broken down by reason.

    Returns the total cancelled orders grouped by cancellation reason, plus
    the per-product records the totals come from. Use only the reason
    categories and counts returned; never invent reasons or numbers.

    Call this when the seller asks why orders were cancelled, who cancelled
    them, or which products had cancellations. get_seller_metrics returns
    only the seller-level monthly cancellation rate and must never be used
    to infer reasons or product-level detail.

    Treat the returned seller-profile records as the seller's account data
    available in this application. Product-level cancellation counts are
    separate from the seller-level monthly cancellation rate; never present
    one as the other.

    Args:
        seller_id: Seller identifier, with or without the SD- prefix.
    """
    normalized, seller, error = _lookup_seller(seller_id)

    if error is not None:
        return error

    records = seller.get("product_cancellations") or []

    reason_totals: dict[str, int] = {}
    total_cancelled_orders = 0
    products = []

    for record in records:
        reasons = dict(record.get("cancellation_reasons") or {})
        cancelled_orders = record.get("cancelled_orders", 0)
        total_cancelled_orders += cancelled_orders

        for reason, count in reasons.items():
            reason_totals[reason] = reason_totals.get(reason, 0) + count

        products.append(
            {
                "product_id": record.get("product_id"),
                "product_name": record.get("product_name"),
                "total_orders": record.get("total_orders"),
                "cancelled_orders": cancelled_orders,
                "cancellation_reasons": reasons,
            }
        )

    # Largest reason first so the main driver is obvious; ties stay stable.
    ordered_reasons = {
        reason: count
        for reason, count in sorted(
            reason_totals.items(), key=lambda item: (-item[1], item[0])
        )
    }

    if total_cancelled_orders or products:
        summary = (
            f"{total_cancelled_orders} cancelled orders across "
            f"{len(products)} products, grouped by cancellation reason."
        )
    else:
        summary = (
            "No product-level cancellation records are available for this "
            "seller."
        )

    return {
        "seller_id": normalized,
        "total_cancelled_orders": total_cancelled_orders,
        "cancellation_reasons": ordered_reasons,
        "products": products,
        "products_covered": len(products),
        "reason_source": seller.get("cancellations_source", "seller_records"),
        "summary": summary,
        "note": (
            "Cancellation reasons come from the seller's product-level "
            "records for the products listed. These product-level counts are "
            "separate from the seller-level monthly cancellation rate; do not "
            "mix or compare them as one metric."
        ),
    }


@tool(parse_docstring=True)
def record_findings(
    issue: Literal["inventory", "cancellations", "pricing", "visibility", "other"],
    summary: str,
    evidence: str,
    confidence: Literal["high", "medium", "low"],
    config: RunnableConfig,
) -> dict:
    """Save one diagnosis finding for the current conversation thread.

    Call this when a material diagnosis is supported by tool data or a seller
    answer. Record one focused finding at a time; do not record every hypothesis
    or intermediate observation. Never record a finding that the data or the
    seller has not supported.

    Args:
        issue: Category of the finding: inventory, cancellations, pricing, visibility or other.
        summary: One plain sentence stating the finding, for example "13 more products went out of stock this month."
        evidence: The specific numbers or the seller's own statement that support it.
        confidence: high, medium or low. Use high only when the data and the seller's answer both support it.
    """
    clean_summary = str(summary).strip()
    clean_evidence = str(evidence).strip()

    if not clean_summary or not clean_evidence:
        return {
            "saved": False,
            "error": "evidence_required",
            "message": (
                "The finding was not saved. A finding needs both a summary and "
                "specific evidence from a tool result or from the seller."
            ),
        }

    thread_id = _thread_id(config)

    with _SESSION_LOCK:
        findings = _SESSION_FINDINGS.setdefault(thread_id, [])
        findings.append(
            {
                "issue": issue,
                "summary": clean_summary,
                "evidence": clean_evidence,
                "confidence": confidence,
            }
        )
        finding_number = len(findings)

    return {
        "saved": True,
        "finding_number": finding_number,
    }


@tool(parse_docstring=True)
def create_action(
    action: Literal["restock_reminder", "stock_sync_check", "followup_call"] | str,
    details: str,
    config: RunnableConfig,
    seller_confirmation: str = "",
    seller_id: str = "",
    related_product: str = "",
    reminder_date: str = "",
    reminder_time: str = "",
    notes: str = "",
) -> dict:
    """Log a persistent follow-up action for the seller.

    This tool records a reminder or next step into persistent CSV storage. It does
    NOT send emails or automated notifications. Never claim an email or notification
    was sent.

    Call this ONLY after the seller has clearly agreed to that specific action in
    this conversation, and pass their agreement in seller_confirmation. A general
    question, a request for suggestions, or silence is not agreement. Never call
    it on your own initiative. Details or reminder_date must contain exactly one
    confirmed future or current date in YYYY-MM-DD format. If the date is missing
    or ambiguous, ask the seller and do not call this tool. After it succeeds,
    report the action ID and confirmed date.

    Args:
        action: restock_reminder (remind seller to restock named products), stock_sync_check (check that listed stock matches real stock), or followup_call (schedule a follow-up call with the Virtual KAM).
        details: What the action covers and its confirmed date in YYYY-MM-DD format.
        seller_confirmation: The seller's own words showing clear agreement to this specific action.
        seller_id: The seller identifier (e.g. 'SD-48213'). Resolved automatically if omitted.
        related_product: Specific product or SKU related to the action (e.g. 'Cotton Casual Shirt').
        reminder_date: Confirmed date in YYYY-MM-DD format (can also be included inside details).
        reminder_time: Optional time string (e.g. '14:00').
        notes: Optional additional notes or remarks.
    """
    clean_confirmation = str(seller_confirmation).strip()
    if not clean_confirmation:
        return {
            "logged": False,
            "saved": False,
            "executed": False,
            "error": "seller_agreement_required",
            "message": (
                "No action was logged. create_action may only be called after "
                "the seller clearly agrees to this specific action. Ask the "
                "seller for agreement, then pass their words in seller_confirmation."
            ),
        }

    clean_details = str(details).strip()
    if not clean_details:
        return {
            "logged": False,
            "saved": False,
            "executed": False,
            "error": "details_required",
            "message": "No action was logged. Describe what the seller agreed to in details.",
        }

    target_date_str = str(reminder_date).strip() if reminder_date else ""
    if not target_date_str:
        action_dates = re.findall(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)", clean_details)
        if not action_dates:
            return {
                "logged": False,
                "saved": False,
                "executed": False,
                "error": "action_date_required",
                "message": (
                    "No action was logged. Confirm one exact calendar date with the "
                    "seller and include it in YYYY-MM-DD format in the action details."
                ),
            }
        if len(action_dates) > 1:
            return {
                "logged": False,
                "saved": False,
                "executed": False,
                "error": "action_date_ambiguous",
                "message": (
                    "No action was logged. Confirm one exact calendar date with the "
                    "seller and include it in YYYY-MM-DD format in the action details."
                ),
            }
        target_date_str = action_dates[0]

    try:
        requested_date = date.fromisoformat(target_date_str)
    except ValueError:
        return {
            "logged": False,
            "saved": False,
            "executed": False,
            "error": "action_date_invalid",
            "message": "No action was logged. The requested calendar date is invalid; clarify it with the seller.",
        }

    if requested_date < datetime.now(ZoneInfo("Asia/Kolkata")).date():
        return {
            "logged": False,
            "saved": False,
            "executed": False,
            "error": "action_date_in_past",
            "message": "No action was logged. Confirm a current or future date with the seller.",
        }

    thread_id = _thread_id(config)
    resolved_seller_id = _resolve_seller_id(config=config, thread_id=thread_id, explicit_id=seller_id)

    resolved_product = (related_product or "").strip()
    if not resolved_product:
        resolved_product = _extract_product_from_details(clean_details)

    try:
        persisted = persist_action(
            seller_id=resolved_seller_id,
            session_id=thread_id,
            action_type=str(action),
            action_description=clean_details,
            reminder_date=requested_date.isoformat(),
            seller_consent=clean_confirmation,
            related_product=resolved_product,
            reminder_time=str(reminder_time).strip(),
            notes=str(notes).strip(),
            status="Pending",
        )
    except Exception as exc:
        return {
            "logged": False,
            "saved": False,
            "executed": False,
            "error": "storage_error",
            "message": f"Action could not be recorded due to a storage failure: {exc}",
        }

    if persisted.get("duplicate"):
        dup = persisted.get("record", {})
        return {
            "logged": False,
            "saved": False,
            "executed": False,
            "duplicate": True,
            "action_id": persisted["action_id"],
            "reference_id": persisted["action_id"],
            "error": "duplicate_action",
            "message": persisted["message"],
            "existing_action": dup,
        }

    record = persisted["record"]
    global _ACTION_COUNTER
    with _SESSION_LOCK:
        _ACTION_COUNTER += 1
        _SESSION_ACTIONS.setdefault(thread_id, []).append(record)

    return {
        "logged": True,
        "saved": True,
        "executed": False,
        "action_id": record["action_id"],
        "reference_id": record["action_id"],
        "action": record["action_type"],
        "action_type": record["action_type"],
        "details": record["action_description"],
        "action_description": record["action_description"],
        "related_product": record["related_product"],
        "requested_date": record["reminder_date"],
        "reminder_date": record["reminder_date"],
        "reminder_time": record["reminder_time"],
        "status": record["status"],
        "seller_consent": record["seller_consent"],
        "seller_id": record["seller_id"],
        "session_id": record["session_id"],
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
        "notes": record["notes"],
        "message": (
            f"Demo action {record['action_id']} has been logged only. It has "
            "NOT been executed: no reminder was sent, no stock check was "
            "performed, and no follow-up call was scheduled. There is no "
            "execution step in this demo."
        ),
    }


@tool(parse_docstring=True)
def get_actions(
    config: RunnableConfig,
    seller_id: str = "",
    status: str = "",
    session_id: str = "",
) -> dict:
    """Retrieve saved follow-up actions and reminders.

    Use this tool to look up previously saved actions, reminders, and pending
    tasks. Filters results by seller ID to keep seller records completely isolated.

    Args:
        seller_id: The seller identifier (e.g. 'SD-48213'). If omitted, the seller from the current session is used.
        status: Optional status filter: 'Pending', 'Completed', 'Cancelled', or empty for all.
        session_id: Optional session ID filter. If omitted, actions across all sessions for this seller are returned.
    """
    thread_id = _thread_id(config)
    resolved_seller = _resolve_seller_id(config=config, thread_id=thread_id, explicit_id=seller_id)

    if not resolved_seller:
        return {
            "error": "seller_id_required",
            "actions": [],
            "message": "Seller ID is required to retrieve actions. Please ask the seller for their Seller ID.",
        }

    actions = get_actions_by_seller(
        seller_id=resolved_seller,
        status=status or None,
        session_id=session_id or None,
    )

    return {
        "seller_id": resolved_seller,
        "count": len(actions),
        "actions": actions,
        "message": f"Found {len(actions)} action(s) for seller {resolved_seller}.",
    }


@tool(parse_docstring=True)
def update_action_status(
    action_id: str,
    status: str,
    config: RunnableConfig,
    seller_id: str = "",
    notes: str = "",
) -> dict:
    """Update the status of an existing action record.

    Support updating action status to Pending, Completed, or Cancelled. Ensures
    that actions can only be updated for the authorized seller.

    Args:
        action_id: The identifier of the action to update (e.g. 'ACT-001').
        status: The new status ('Pending', 'Completed', or 'Cancelled').
        seller_id: The seller identifier to verify ownership. If omitted, resolved from session.
        notes: Optional notes or remarks regarding the status update.
    """
    thread_id = _thread_id(config)
    resolved_seller = _resolve_seller_id(config=config, thread_id=thread_id, explicit_id=seller_id)

    return update_action_status_record(
        action_id=action_id,
        new_status=status,
        seller_id=resolved_seller if resolved_seller != "SD-DEFAULT" else None,
        notes=notes,
    )


@tool
def get_call_summary(config: RunnableConfig) -> dict:
    """Get the findings and logged actions for the current conversation thread.

    Call this once, when the seller is ready to end the call or asks for a recap,
    and base your closing summary only on what it returns. Keep the spoken
    summary to three short parts: the main issue, what you recommend, and the
    next steps already logged. Remember that logged demo actions have not been
    executed.
    """
    thread_id = _thread_id(config)
    resolved_seller = _resolve_seller_id(config=config, thread_id=thread_id)

    with _SESSION_LOCK:
        findings = [
            dict(item) for item in _SESSION_FINDINGS.get(thread_id, [])
        ]

    # Retrieve actions for the current session from persistent CSV
    session_actions = get_actions_by_session(
        session_id=thread_id,
        seller_id=resolved_seller if resolved_seller != "SD-DEFAULT" else None,
    )

    # Format actions for backward compatibility
    formatted_actions = []
    for item in session_actions:
        record = dict(item)
        record["reference_id"] = item.get("action_id", "")
        record["action"] = item.get("action_type", "")
        record["details"] = item.get("action_description", "")
        record["requested_date"] = item.get("reminder_date", "")
        record["executed"] = False
        formatted_actions.append(record)

    return {
        "findings": findings,
        "actions": formatted_actions,
    }


@tool(parse_docstring=True)
def get_playbook(
    issue: Literal[
        "inventory", "cancellations", "pricing", "visibility", "sales"
    ],
) -> dict:
    """Look up general practical tips that help sellers recover from a specific problem.

    Call this before recommending actions, once the main issue is clear. Use at
    most 2 or 3 of the returned tips and describe them as general practices, not
    guarantees. Do not generalize one seller's records as facts about other
    sellers.

    Args:
        issue: The problem to look up: inventory, cancellations, pricing, visibility or sales.
    """
    return {
        "issue": issue,
        "tips": list(PLAYBOOK[issue]),
    }
