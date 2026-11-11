---
doc_id: "KB-03"
title: "Seller Business Health Diagnostics"
domain: "ecommerce_business"
doc_type: "business_knowledge"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - seller health check
  - diagnostic methodology
  - baseline
  - root cause
  - symptoms
  - largest negative change
  - prioritisation
applies_to:
  - general_marketplace
---

# Seller Business Health Diagnostics

This document teaches a repeatable method for reviewing a marketplace seller's performance: establish a baseline, compare equal periods, find the biggest negative movements, separate symptoms from root causes, rank hypotheses and decide what to investigate next. It uses the assignment's sample seller as an illustrative example. That data is assignment data, not real Snapdeal data.

## 1. The five areas of a health check

A seller review should touch five areas, in roughly this order:

1. **Revenue and order performance**: sales, orders, ASP, growth versus last period.
2. **Pricing and profitability**: ASP trend, discounts, margin per order.
3. **Inventory and availability**: out-of-stock count, which products, for how long.
4. **Fulfilment and cancellations**: cancellation rate, dispatch delays, returns.
5. **Catalogue, discoverability and conversion**: impressions, clicks, orders per click, content quality, ratings.

Each area produces symptoms that may be caused by another area. For example, a catalogue issue can look like a revenue issue.

## 2. Step 1: establish a baseline

A baseline is what "normal" looks like for this seller. Use the seller's own history, not an outside number.

- Prefer at least 3 comparable periods where available, not only the previous month.
- Note known events: festival sales, a promotion, a supplier change, a price change.
- Identify the seller's top products, because the seller-level average hides product behaviour.

If only two periods are available, say clearly that the comparison is limited and avoid strong conclusions.

## 3. Step 2: compare equivalent periods

Compare like with like:

- Same number of days (or normalise to per-day).
- Same type of period (festival week versus festival week, not versus a quiet week).
- Same metric definition (orders placed versus delivered).

Example: if this month has 28 days and last month had 31, compare per-day orders. 400 orders over 31 days is about 12.9 per day; 270 over 28 days is about 9.6 per day, a fall of roughly 25%, not 32.5%. Whether the months are unequal must be checked before quoting the decline.

## 4. Step 3: find the largest negative change

Calculate percent change for every metric and rank by size and business importance.

Illustrative sample seller (assignment data):

- Sales ₹2,00,000 → ₹1,35,000: −32.5%.
- Orders 400 → 270: −32.5%.
- ASP ₹500 → ₹500: unchanged.
- Cancellation rate 8% → 14%: +6 percentage points (+75% relative).
- Out-of-stock products 5 → 18: +13 products (3.6 times).

Observations (facts): sales and orders fell by the same percentage; ASP did not move; cancellations and out-of-stock counts rose. These are observations. Anything about why is a hypothesis until evidence supports it.

## 5. Step 4: separate symptoms from root causes

A symptom is what you see in the numbers. A root cause is the operational reason underneath.

- Symptom: fewer orders. Possible root causes: fewer impressions, lower click-through, lower conversion, unavailable products, more cancellations, lower demand.
- Symptom: higher cancellations. Possible root causes: stock mismatch, slow dispatch, buyer cancellations, courier problems, system issues.
- Symptom: more out-of-stock products. Possible root causes: late replenishment, supplier delay, wrong forecast, over-selling after a promotion, panel stock not updated.

Ask "what would have to be true for this symptom to appear?" for each. List the possibilities before choosing one.

## 6. Step 5: rank possible problems

Rank hypotheses on three questions:

1. **Plausibility**: does the evidence at hand fit it?
2. **Size**: if true, could it explain much of the movement?
3. **Fixability**: can the seller act on it soon?

For the sample seller, a plausible ranking (a hypothesis list, not conclusions):

1. Availability: stockouts rose from 5 to 18. Fits fewer orders; also may relate to cancellations. Needs product-level history to size.
2. Cancellations: rate rose 6 points. Relevant if orders are counted before cancellation. Cause unknown.
3. Visibility or conversion: no data yet. Cannot be assessed without impressions, clicks, conversion.
4. Demand or seasonality: not tested; needs prior-year or category context.
5. Pricing: ASP unchanged, so a price-driven decline is unlikely to be the main factor at seller level; still check product-level price moves and competitor price position if data exists.

## 7. Step 6: decide what to investigate next

Choose the data that best separates the hypotheses:

- Product-level orders last month versus this month (which products fell?).
- Which of the 18 out-of-stock products were bestsellers last month, and since when are they out of stock?
- Cancellation reasons: seller-side, buyer-side, logistics, system.
- Impressions, clicks and conversion by product, if available.
- Any pricing, content, packaging or courier changes in the period.

One question at a time is best in a conversation; ask the most separating question first (usually: which products drove the drop, and are those the out-of-stock ones?).

## 8. Complete diagnostic walkthrough (illustrative)

**Situation**: Sales and orders both fell by 32.5% with ASP flat; cancellations and stockouts rose.

1. **Decompose**: ΔSales = ΔOrders × ASP (price effect zero). So the entire fall is volume. (Detailed method in KB-04.)
2. **Locate**: Ask which products contributed most of the 130-order loss.
3. **Test availability**: Compare the lost products with the 13 newly out-of-stock ones. If most lost orders belong to newly out-of-stock bestsellers, availability is a strong candidate. If they do not, look elsewhere.
4. **Test cancellations**: 8% of 400 = 32 cancelled; 14% of 270 ≈ 38 cancelled. Cancelled orders are a small share of the 130-order gap in absolute terms (cancellation count actually went up by about 6 while orders fell by 130), so cancellations alone cannot explain the order fall if "orders" means orders placed. If "orders" means orders after cancellation, the maths changes. Clarify the definition.
5. **Check demand side**: impressions, clicks, conversion, price versus alternatives, season.
6. **Conclude carefully**: state what is supported, what is not, and what is still unknown.
7. **Recommend 2-3 actions**: for example, prioritise replenishment of high-demand out-of-stock products, review cancellation reasons, and confirm stock sync. Get the seller's agreement before logging them (see KB-23).

## 9. A second walkthrough: sales flat, profit down (illustrative)

Sales stay at ₹2,00,000, orders rise from 400 to 450, ASP falls from ₹500 to about ₹444 (2,00,000 ÷ 450). This looks like heavier discounting or a shift to cheaper items. Health checks should move to margin: if price fell 11% and cost per unit did not, margin per unit has fallen more than 11% in percent of margin terms. Investigate promotions and contribution margin (KB-06, KB-07).

## 10. Questions a KAM should ask

- Which area worries you most right now: sales, stock, cancellations or something else?
- Did anything change last month in prices, stock, courier, packing or promotions?
- Which five products usually sell most?
- Do you see the cancellation reasons, or only the totals?

## 11. What not to conclude

- Do not say the largest percentage change is the root cause; it may be a symptom.
- Do not attribute a rupee loss to stockouts without product-level sales history.
- Do not claim a ranking or search visibility problem without impressions data.
- Do not compare unequal periods without normalising.

## 12. Related concepts

Metrics (KB-02), sales decomposition (KB-04), stockouts (KB-09), cancellations (KB-14), evidence-based reasoning (KB-25), action planning (KB-23).

## 13. Source notes

Methodology is general business guidance (variance analysis and issue-tree reasoning). The sample seller figures come from the assignment brief and are illustrative.
