---
doc_id: "KB-09"
title: "Stockout Analysis and Recovery"
domain: "ecommerce_business"
doc_type: "business_knowledge"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - stockout
  - out of stock
  - replenishment prioritisation
  - bestseller stockout
  - stockout recovery
  - lost sales
applies_to:
  - general_marketplace
---

# Stockout Analysis and Recovery

This document explains why stockouts hurt a marketplace seller, how to decide which out-of-stock products deserve attention first, and how to recover and prevent repeats. Example products and numbers are illustrative. The assignment sample seller (out-of-stock products rising from 5 to 18) is used as the central scenario; its data is assignment data, not real Snapdeal data.

## 1. Why stockouts hurt

- **Direct lost orders**: an unavailable product cannot be bought.
- **Cancellations**: if panel stock is higher than physical stock, orders are accepted then cancelled.
- **Visibility and momentum**: unavailable listings may lose exposure and sales history momentum. How a specific platform treats out-of-stock listings must be confirmed (KB-24); do not assert a ranking effect.
- **Customer loss**: buyers switch to competitors and may not return.
- **Bundle and variant damage**: one missing component or size spoils the offer.
- **Wasted marketing**: ads or promotions on unavailable items burn budget.

## 2. Not all stockouts are equal

A count of out-of-stock products (5 to 18, +13) tells you something changed but not how much revenue is at risk. A stockout on a bestseller is more damaging than one on a product that sells twice a month. Prioritise by demand, margin, duration and fixability.

## 3. Information needed to rank stockouts

For each out-of-stock product:
- Average daily orders in the weeks before stockout (use in-stock days).
- Contribution margin per unit (or at least price).
- Date it went out of stock (new versus long-term).
- Replenishment lead time and whether the supplier has stock.
- Whether it is a variant (size or colour) of a bigger product.
- Any open or recently cancelled orders.
- Whether it is part of a bundle or campaign.

If history is missing, ask for order history by product before ranking.

## 4. Practical ranking framework

**Daily contribution at risk = Average daily orders × Contribution margin per unit**

Then adjust for urgency and feasibility:
1. Rank by daily contribution at risk (or daily sales value if margin is unknown).
2. Boost products that went out of stock recently (their listings and history are intact) and those with long supplier lead times (start earliest).
3. Boost products that unlock other sales (bundle components, top-selling variants).
4. Demote products with very low demand, negative margin, quality problems or discontinuation plans.

**Example (illustrative):**
- Product A: 6 orders/day × ₹80 = ₹480/day; out for 3 days; lead time 5 days.
- Product B: 2 × ₹150 = ₹300/day; out for 25 days; lead time 10 days.
- Product C: 0.3 × ₹100 = ₹30/day; out for 40 days.
- Product D: 4 × ₹40 = ₹160/day; out for 2 days; lead time 3 days.
- Product E: 5 × ₹60 = ₹300/day; out for 6 days; lead time 20 days.

Order: A first (highest daily value, new). E and B next (equal ₹300/day; E has 20-day lead time so order it today; B needs checking why it has been out so long). D next (cheap and fast to fix, quick win). C last (low demand; consider discontinuing).

Note this ranking is a prioritisation tool. It does not prove how many rupees were lost.

## 5. Newly out-of-stock versus long-term out-of-stock

- **Newly out of stock**: recent demand history is fresh; recovery restores sales faster; investigate whether the sell-out came from a demand spike, a forecasting gap or a stock sync error.
- **Long-term out of stock**: may be discontinued, supplier-blocked or low priority. Decide: restock, replace, deactivate or delist. Check whether the listing is still useful.

For the sample seller: 13 more products out of stock than last month. A KAM should ask which of the 13 are new this month, and whether they were top sellers before.

## 6. Bestseller stockouts

Treat as urgent:
1. Confirm physical stock; fix panel quantity if wrong.
2. Check inbound shipments; expedite if feasible.
3. If lead time is long, consider partial or alternative supply, or temporary substitute variant.
4. Pause promotions or ads on the product.
5. Plan restock quantity from demand, lead time and safety stock (KB-08), asking for missing data rather than guessing.

## 7. Replenishment prioritisation under constraints

If cash or supplier capacity is limited, restock in order of contribution at risk per rupee of stock purchased: (daily orders × unit contribution) ÷ unit cost. This favours fast, profitable, cheap-to-buy items. Avoid putting all cash into one slow, expensive item.

## 8. Recovery plan

1. **Triage**: list out-of-stock products with demand and margin; tag new versus long-term.
2. **Stabilise**: update panel stock to match reality; pause promotions on out-of-stock items.
3. **Restock** in priority order with realistic lead times.
4. **Communicate**: note expected restock dates internally; do not promise buyers specifics without confirmation.
5. **Re-launch**: after restocking, verify listing is live, content intact, price correct.
6. **Monitor** daily orders for 1-2 weeks to see recovery.
7. **Review** root cause.

Recovery speed depends on lead time and how the platform treats listings after restock; do not promise a specific rebound.

## 9. Preventing repeated stockouts

- Daily stock check on A items; weekly on others.
- Reorder points with safety stock (KB-08).
- Stock sync between warehouse, sales channels and panel.
- Cap panel quantity on risky items or reserve buffer for multiple channels.
- Supplier relationships and alternative suppliers.
- Pre-peak stocking for seasonal items.
- Post-promotion stock review.

## 10. Product-level stockout analysis (quick method)

1. List all SKUs with out-of-stock days in the period.
2. Compute lost-days = days out of stock.
3. Estimate "expected missed orders" as lost-days × baseline daily orders; label as an estimate with a range, because demand may not have been constant and buyers might have bought a substitute.
4. Sum by product to compare, not to report as a precise loss.

## 11. Questions a KAM should ask

- Which of your top 5 products are in stock today?
- Which items went out of stock this month, and when?
- Do you know why: late supplier, demand spike, wrong stock count?
- How long does restocking take for each?
- Is panel stock updated by hand or automatically?
- Were any promotions running on these items?

## 12. What not to conclude

- Do not say stockouts caused the full sales drop; test with product-level history.
- Do not state a rupee loss as fact.
- Do not claim a ranking drop from stockouts without platform evidence.
- Do not give restock quantities without demand and lead-time data.

## 13. Related concepts

Inventory planning (KB-08), cancellations (KB-14), sales decomposition (KB-04), action planning (KB-23), evidence-based reasoning (KB-25).
