---
doc_id: "diagnostic_005"
title: "Business Diagnostic Framework for Seller Performance"
domain: "diagnosis"
doc_type: "diagnostic_framework"
source_type: "general_guidance"
verification_status: "research_based"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - sales decline diagnosis
  - revenue decomposition
  - month over month analysis
  - root cause analysis
  - orders versus ASP
  - product concentration
applies_to:
  - marketplace_sellers
---

# Business Diagnostic Framework

## Overview
This framework tells the assistant how to move from "sales are down" to a supported explanation and an action. It uses only metrics the prototype provides (sales, orders, ASP, cancellation rate, stockout count and records, historical orders of stocked-out products) and flags where extra data is needed (`data_avail_025`). Source type: general guidance [G001].

## Step 1: Interpret month-over-month (MoM) changes
- **Formula:** MoM % = (this month - last month) / last month.
- Compare equal-length periods; note festivals, sale events and month length.
- One month is a signal, not a trend. Say "this month" rather than "you are declining" unless several months agree.
- Size matters: a small base makes large percentages.

## Step 2: Decompose sales
**Sales = Orders x ASP** (when ASP is sales per order). Split the change into:
- **Volume effect:** change in orders at old ASP.
- **Price/mix effect:** change in ASP at new orders.
**Illustrative:** Sales 100,000 (250 orders, ASP 400) falls to 80,000. If orders are 200 and ASP 400, the whole fall is volume. If orders stay 250 and ASP is 320, the whole fall is price/mix.

## Step 3: Check supporting signals
Look at cancellation rate, stockout count and which products stocked out. Ask whether demand fell (fewer orders placed) or supply failed (orders cancelled, products unavailable).

## Step 4: Product-level versus seller-level
- Seller-level issue: all products weaken together (account, logistics, season, overall visibility).
- Product-level issue: one or few products drive the change (stockout, price, listing, reviews).
With current data, product-level evidence exists only for stocked-out products. Ask the seller for the rest.

## Step 5: Hypothesis, test, act
List 2 to 3 hypotheses, name the evidence that would confirm each, ask 1 to 2 questions, then recommend. **Correlation is not causation:** orders falling while stockouts rise suggests a link, but confirm with the history of those specific products.

## Evidence strength labels
- **Strong:** directly measured by tools (for example orders fell 20% and ASP flat).
- **Moderate:** consistent pattern plus seller confirmation.
- **Weak:** inferred only. Say "possible" and ask.

---

## Scenario A: Sales down, order volume stable
**Problem:** Sales fell but orders are about the same.
**Possible causes:** ASP fell (discounting, cheaper products selling more, lower-priced variants), higher-priced items out of stock, price changes by the seller or automated pricing.
**Evidence required:** ASP trend, product mix, stockouts of higher-priced items, any recent price edits.
**Questions:** "Did you change prices or start discounts?" "Which higher-priced items are unavailable?"
**Diagnosis:** If ASP fell, the problem is price/mix, not demand.
**Actions:** Review mix and pricing against margin before cutting more (`pricing_006`); restock premium items.
**Limitations:** Product-level price history and margins are not in the prototype.

## Scenario B: Sales and orders fall together
**Problem:** Both decline, ASP roughly flat.
**Possible causes:** fewer visitors (visibility), stockouts, lower conversion, season, cancellation losses.
**Evidence required:** stockout records and past demand, cancellation rate, impressions and clicks (not available).
**Questions:** "Any listings changed or removed?" "Which top sellers are out?"
**Diagnosis:** If top historical products are out of stock, supply is a probable driver; otherwise ask about visibility and listings.
**Actions:** Restock priority products (`inventory_007`); then review catalogue and visibility (`catalogue_009`, `visibility_010`).
**Limitations:** Cannot separate visibility from conversion without funnel data.

## Scenario C: Sales rise but cancellations also rise
**Problem:** Growth with a higher cancellation rate.
**Possible causes:** inventory shown but not available, slow dispatch under higher volume, pricing errors, bulk orders.
**Evidence required:** cancellation reasons and initiator, stock accuracy, dispatch timing.
**Questions:** "Do your stock counts match what is on the shelf?" "What is the daily dispatch capacity?"
**Diagnosis:** Cancelled orders can inflate gross sales; check whether sales is net of cancellations.
**Actions:** Fix stock accuracy first (`fulfilment_008`).
**Limitations:** Reason codes are not available.

## Scenario D: High historical demand for out-of-stock products
**Problem:** Stocked-out products had many past orders.
**Possible causes:** replenishment delay, supplier issues, cash constraints, unexpected demand.
**Evidence required:** past orders per product, lead time, current stock.
**Questions:** "How long does restocking take?" "Is supplier availability the constraint?"
**Diagnosis:** Products with higher past orders likely hold more lost demand, so rank them first.
**Actions:** Restock by historical order rank; do not set quantities without lead time (`inventory_007`).
**Limitations:** Past orders do not guarantee future demand.

## Scenario E: ASP falling while orders rise
**Problem:** More orders at lower average price.
**Possible causes:** discounts, shift to cheaper items, price competition.
**Evidence required:** sales, orders, margin per product.
**Questions:** "Are the extra orders coming from discounted items?" "What margin remains?"
**Diagnosis:** Sales may rise while profit falls.
**Actions:** Compute contribution per unit before extending discounts (`promotions_012`).
**Limitations:** Margin data needed.

## Scenario F: A few products make most of the business
**Problem:** Concentration risk.
**Possible causes:** thin assortment, one strong product.
**Evidence required:** product-level sales (ask seller; only partial in prototype).
**Questions:** "Which three products are most of your orders?"
**Diagnosis:** One stockout or review problem can cut sales sharply.
**Actions:** Protect bestsellers' stock and add adjacent products (`assortment_014`).
**Limitations:** Share of sales by product not available from current tools.

## Common mistakes
- Recommending discounts before decomposing sales.
- Assuming a cause the data cannot show.
- Reporting many issues at once; pick the top one to three.
