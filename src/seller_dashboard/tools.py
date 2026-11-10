from threading import Lock
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Findings and actions are kept in memory, separated by LangGraph thread ID.
_SESSION_LOCK = Lock()
_SESSION_FINDINGS: dict[str, list[dict]] = {}
_SESSION_ACTIONS: dict[str, list[dict]] = {}
_ACTION_COUNTER = 0


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
    "inventory": [
        "Prioritise restocking products with higher historical demand.",
        "Review stock availability regularly."
    ],
    "cancellations": [
        "Review products with unusually high cancellation rates.",
        "Check whether product availability matches actual stock."
    ],
    "pricing": [
        "Review the price change alongside the average selling price and order volume.",
        "Check whether the current price still covers product costs and margins."
    ],
    "visibility": [
        "Review product titles, images and category details for completeness.",
        "Check whether listings are active and correctly categorised."
    ],
    "sales": [
        "Compare orders, average selling price and cancellations to see what changed.",
        "Check whether stock-outs affected products with recent demand before assuming stock caused the change."
    ]
}
SELLERS = {
    # ------------------------------------------------------------------
    # Seller 1: the brief's seller. Cause: stock-outs leading to cancellations.
    # ------------------------------------------------------------------
    "SD-48213": {
        "name": "Rajesh",
        "business": "Rajesh Garments",
        "category": "Women's ethnic wear",
        "metrics_source": "assignment brief",
        "list_source": "assumed",
        "last_month": {
            "sales": 200000,
            "orders": 400,
            "cancellation_rate_pct": 8.0,
            "avg_selling_price": 500,
            "out_of_stock_products": 5,
        },
        "this_month": {
            "sales": 135000,
            "orders": 270,
            "cancellation_rate_pct": 14.0,
            "avg_selling_price": 500,
            "out_of_stock_products": 18,
        },
        # 13 newly out of stock (130 orders last month) + 5 already out of stock
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
            {"sku": "TOP-009", "name": "Crop Top", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False},
        ],
    },
    # ------------------------------------------------------------------
    # Seller 2 (assumed): orders are fine, sales fell because the seller cut
    # prices. Cause: pricing, not volume, stock or cancellations.
    # ------------------------------------------------------------------
    "SD-52077": {
        "name": "Meena",
        "business": "Meena Home Decor",
        "category": "Home decor",
        "metrics_source": "assumed",
        "list_source": "assumed",
        "last_month": {
            "sales": 150000,
            "orders": 300,
            "cancellation_rate_pct": 5.0,
            "avg_selling_price": 500,
            "out_of_stock_products": 3,
        },
        "this_month": {
            "sales": 124000,
            "orders": 310,
            "cancellation_rate_pct": 5.0,
            "avg_selling_price": 400,
            "out_of_stock_products": 4,
        },
        "out_of_stock": [
            {"sku": "DEC-004", "name": "Ceramic Flower Vase", "last_month_orders": 6, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "DEC-011", "name": "Wall Clock", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "DEC-002", "name": "Scented Candle Set", "last_month_orders": 2, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "DEC-019", "name": "Photo Frame Set", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False},
        ],
    },
    # ------------------------------------------------------------------
    # Seller 3 (assumed): stock is fine, orders dipped a little, but
    # cancellations tripled. Cause: cancellations and fulfilment.
    # ------------------------------------------------------------------
    "SD-63190": {
        "name": "Arjun",
        "business": "Arjun Mobile Accessories",
        "category": "Mobile accessories",
        "metrics_source": "assumed",
        "list_source": "assumed",
        "last_month": {
            "sales": 210000,
            "orders": 350,
            "cancellation_rate_pct": 6.0,
            "avg_selling_price": 600,
            "out_of_stock_products": 2,
        },
        "this_month": {
            "sales": 180000,
            "orders": 300,
            "cancellation_rate_pct": 19.0,
            "avg_selling_price": 600,
            "out_of_stock_products": 3,
        },
        "out_of_stock": [
            {"sku": "ACC-007", "name": "20W Fast Charger", "last_month_orders": 9, "bestseller": False, "newly_out_of_stock": True},
            {"sku": "ACC-015", "name": "Braided Cable 2m", "last_month_orders": 3, "bestseller": False, "newly_out_of_stock": False},
            {"sku": "ACC-021", "name": "Phone Stand", "last_month_orders": 1, "bestseller": False, "newly_out_of_stock": False},
        ],
    },
}
 
def normalize_seller_id(value: object) -> str | None:
    """Normalise a seller identifier without ever changing the seller dataset.

    ``52077``, ``"52077"``, ``"sd-52077"`` and ``" SD-52077 "`` all become
    ``"SD-52077"``. Returns ``None`` when no usable identifier was supplied.
    """
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, float) and value.is_integer():
        value = int(value)

    text = str(value).strip().upper().replace(" ", "")

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
    """Resolve a seller ID to a read-only record from the mock dataset."""
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


@tool(args_schema=Seller)
def get_seller_metrics(seller_id: str | int) -> dict:
    """Get monthly aggregate seller metrics using the seller's unique ID.

    Get the seller's business numbers for last month and this month, with the
    changes already calculated.

    Call this FIRST, as soon as the seller says their sales or orders have dropped
    or asks how their business is doing. Call it again only to re-check a number.

    This returns monthly totals only: sales, orders, cancellation rate, average
    selling price and the COUNT of out-of-stock products. It does NOT return
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

    last_month = seller["last_month"]
    this_month = seller["this_month"]

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
        "name": seller["name"],
        "business": seller["business"],
        "category": seller["category"],
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

    Call this before naming, listing or describing any specific out-of-stock
    product. get_seller_metrics gives only an aggregate count and must never be
    used to infer product-level details.

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


@tool(parse_docstring=True)
def record_findings(
    issue: Literal["inventory", "cancellations", "pricing", "visibility", "other"],
    summary: str,
    evidence: str,
    confidence: Literal["high", "medium", "low"],
    config: RunnableConfig,
) -> dict:
    """Save one diagnosis finding for the current conversation thread.

    Call this each time you have formed a view about a cause, or ruled one out,
    and you have data evidence for it. Record 2 to 4 findings per call, not every
    sentence. Never record a finding that the data or the seller has not supported.

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
    action: Literal["restock_reminder", "stock_sync_check", "followup_call"],
    details: str,
    config: RunnableConfig,
    seller_confirmation: str = "",
) -> dict:
    """Log a follow-up action for the current conversation thread.

    This is a demo logging tool only. It does NOT send reminders, perform stock
    checks, schedule calls or start any monitoring. Never tell the seller that
    an action has been executed or is running automatically.

    Call this ONLY after the seller has clearly agreed to that specific action in
    this conversation, and pass their agreement in seller_confirmation. A general
    question, a request for suggestions, or silence is not agreement. Never call
    it on your own initiative. Call it once per agreed action. After it succeeds,
    tell the seller the reference ID and make clear the action was logged only.

    Args:
        action: restock_reminder (remind the seller to restock named products), stock_sync_check (check that listed stock matches real stock), or followup_call (schedule a follow-up call with the Virtual KAM).
        details: What the action covers in one sentence, for example the product names or the follow-up timing the seller agreed to.
        seller_confirmation: The seller's own words showing clear agreement to this specific action. Leave empty if the seller has not agreed, and no action will be logged.
    """
    if not str(seller_confirmation).strip():
        return {
            "logged": False,
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
            "executed": False,
            "error": "details_required",
            "message": "No action was logged. Describe what the seller agreed to in details.",
        }

    global _ACTION_COUNTER

    thread_id = _thread_id(config)

    with _SESSION_LOCK:
        _ACTION_COUNTER += 1
        record = {
            "reference_id": f"ACT-{_ACTION_COUNTER:03d}",
            "action": action,
            "details": clean_details,
            "status": "logged",
            "executed": False,
        }
        _SESSION_ACTIONS.setdefault(thread_id, []).append(record)
        record = dict(record)

    return {
        "logged": True,
        "executed": False,
        "reference_id": record["reference_id"],
        "action": record["action"],
        "details": record["details"],
        "status": record["status"],
        "message": (
            f"Demo action {record['reference_id']} has been logged only. It has "
            "NOT been executed: no reminder was sent, no stock check was "
            "performed, and no follow-up call was scheduled. There is no "
            "execution step in this demo."
        ),
    }


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

    with _SESSION_LOCK:
        return {
            "findings": [
                dict(item) for item in _SESSION_FINDINGS.get(thread_id, [])
            ],
            "actions": [
                dict(item) for item in _SESSION_ACTIONS.get(thread_id, [])
            ],
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
    guarantees. The tips are illustrative sample content for this demo and not
    real Snapdeal benchmarks, so never quote numbers from them as facts about
    other sellers.

    Args:
        issue: The problem to look up: inventory, cancellations, pricing, visibility or sales.
    """
    return {
        "issue": issue,
        "tips": list(PLAYBOOK[issue]),
    }