---
doc_id: "data_avail_025"
title: "Data Availability and Diagnostic Limitations"
domain: "technical_compatibility"
doc_type: "data_map"
source_type: "internal"
verification_status: "maintained"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - data availability
  - prototype limitations
  - what the assistant can conclude
  - hallucination prevention
  - python tools
applies_to:
  - ai_assistant
  - developers
---

# Data Availability and Diagnostic Limitations

## Purpose
Maps business concepts to what the **current prototype tools** return. Rule: never present a metric the tools do not return. Tools provide mock seller data; update this file if tools change.

## Available through Python tools
For each item: source is the backend Python tool (mock seller data).

### Sales (monthly)
- **Safe conclusions:** direction and size of change month over month.
- **Avoid:** calling it profit or net revenue; the exact definition (gross or net of cancellations) must be confirmed from tool code.

### Order count (monthly)
- **Safe:** volume trend; with sales, derive ASP and decompose changes.
- **Avoid:** inferring demand loss when stockouts or cancellations may explain it.

### ASP
- **Safe:** whether price per item moved; with flat ASP, price is unlikely the main driver of change in sales.
- **Avoid:** claiming price cuts or mix shift without evidence.

### Cancellation rate
- **Safe:** that it rose or fell.
- **Avoid:** saying who cancelled or why; no reason codes. Also confirm denominator.

### Out-of-stock count
- **Safe:** number of products unavailable.
- **Avoid:** a stockout percentage (no total active product count) or lost-sales amounts.

### Product-level stockout records
- **Safe:** which products are out of stock.
- **Avoid:** how long they have been out unless the record says so.

### Historical orders of stocked-out products
- **Safe:** relative priority for restocking (higher history means higher likely lost demand).
- **Avoid:** restock quantities or promised sales recovery.

### Bestseller flag (some)
- **Safe:** treat flagged products as important.
- **Avoid:** assuming unflagged products are not important.

## Not available (extra fields required)
| Information | Needed to calculate or investigate | Avoid saying |
|---|---|---|
| Impressions, clicks, CTR | product-level views and clicks by period | "your visibility is low/high" |
| Conversion rate | page visits or clicks plus orders per product | "your conversion is poor" |
| Profit margin | cost price, fees, shipping, packaging | "this is profitable", "you can afford a discount" |
| Dispatch delays | placed, packed and handover timestamps | "you are shipping late" |
| Returns, RTO | return counts, reasons, delivered units | "returns are the cause" |
| Customer ratings and reviews | rating and review text per product | "customers complain about..." |
| Competitor prices | competitor price feed for matching products | "you are overpriced" |
| Total active products, current stock levels | product list and stock quantities | "inventory cover is X days" |
| Cancellation reason and initiator | order-level reason codes | "this is seller fault" |

## What the assistant should do when data is missing
1. Say what the tools show.
2. Name the missing piece plainly ("I cannot see your product views").
3. Ask the seller a targeted question or note the extra data needed.
4. Label any resulting advice as a hypothesis.

## Safe example (illustrative)
"Orders dropped, and your price per item stayed the same, so price changes do not explain this. Several products are out of stock. I cannot see views or conversion, so I cannot tell whether visibility also changed. Which of those out-of-stock products matter most?"
