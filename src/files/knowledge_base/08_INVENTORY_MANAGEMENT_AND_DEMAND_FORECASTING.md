---
doc_id: "KB-08"
title: "Inventory Management and Demand Forecasting"
domain: "ecommerce_business"
doc_type: "business_knowledge"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - inventory planning
  - demand forecasting
  - reorder point
  - safety stock
  - lead time
  - days of inventory
  - dead stock
  - ABC analysis
  - seasonal inventory
applies_to:
  - general_marketplace
---

# Inventory Management and Demand Forecasting

This document covers how a marketplace seller plans stock: forecasting demand, setting reorder points and safety stock, measuring how long stock lasts, and handling excess, dead and seasonal stock. Every calculation lists its assumptions. An agent should **not** recommend precise reorder quantities without reliable demand, lead-time and current-stock data; when data is missing, give the method and ask for the inputs.

## 1. Why inventory planning matters

Too little stock causes stockouts: lost orders, cancellations (if panel stock is wrong) and visibility loss. Too much stock ties up cash, risks damage or obsolescence and may require clearance discounts. Good planning balances service level (being in stock when buyers want) against holding cost.

## 2. Demand forecasting basics

Forecasting estimates future orders or units from history.

- **Simple average**: average daily units over the last 30 days. Works for steady products.
- **Moving average**: average of the last N days, updated daily; reacts to trends.
- **Seasonal adjustment**: scale by a seasonal index (this season's demand ÷ normal) taken from prior years; only valid if prior-year data exists.
- **Event adjustment**: add expected lift from a planned promotion; remove demand distorted by past stockouts.

**Stockout bias**: sales during a stockout understate true demand. If a product was out of stock for 10 of 30 days, 30-day average sales underestimate daily demand. Use only in-stock days: daily demand = units sold ÷ in-stock days.

Example (illustrative): 180 units in 30 days, but out of stock 10 days. In-stock demand = 180 ÷ 20 = 9 per day, not 6.

## 3. Lead time

Lead time = days between placing a replenishment order and having sellable stock. Include supplier production time, transit, quality check, receiving and panel stock update. Use the real, observed lead time and its variability, not the promised one.

## 4. Reorder point

**Reorder point = Average daily demand × Lead time + Safety stock**

Assumption: demand and lead time are reasonably stable.

Example: 12 units/day, lead time 7 days, safety stock 18 → ROP = 84 + 18 = 102 units. When on-hand plus inbound falls to 102, reorder.

## 5. Safety stock

Safety stock protects against demand and lead-time variability.

A common formula, assuming demand is roughly normal and lead time is fixed: **Safety stock = z × σd × √L**
where z is the service-level factor (about 1.65 for roughly 95% in a normal distribution), σd is the standard deviation of daily demand and L is lead time in days.

Example: σd = 4 units, L = 7: 1.65 × 4 × √7 = 1.65 × 4 × 2.646 = 17.5, round to 18. Requires enough history to estimate σd; with few data points, treat the result as rough.

If lead time itself varies, safety stock must be higher.

## 6. Days of inventory on hand

**Days of inventory = Current stock ÷ Average daily demand**

Example: 240 units ÷ 12 per day = 20 days. If lead time is 7 days, there are about 13 spare days (before safety stock). If days of inventory < lead time, a stockout is likely before the next delivery.

## 7. Turnover and sell-through

Inventory turnover = COGS ÷ average inventory value. Sell-through = units sold ÷ units received. Low turnover or sell-through flags excess stock; very high turnover with frequent stockouts flags under-stocking. See KB-02.

## 8. Excess and dead stock

- **Excess stock**: more than needed for demand over a reasonable horizon.
- **Dead stock**: no meaningful sales over a long period (define a period with the seller, for example 90+ days without sales).

Options: bundle with fast sellers, targeted discount, improve listing, sell via other channels, return to supplier, donate or write off. Decide using contribution margin and holding cost: a modest discount that releases cash can beat holding.

## 9. ABC analysis

Rank products by sales (or contribution). By common convention: A items are the top group making roughly the first 70-80% of sales, B the next 15-20%, C the remainder. The percentages are a convention, not a rule. Use it to set priority: A items get higher safety stock, daily stock checks and fastest replenishment; C items get lean stock and periodic review.

## 10. Demand variability

High variability means higher safety stock for the same service level. Intermittent products (rare, lumpy sales) are hard to forecast; keep small stock or make-to-order if possible. Variants (sizes, colours) have their own demand; forecast at variant level for apparel (KB-18).

## 11. Seasonal products

- Identify the season window and the lead time back from it.
- Build stock before the peak using prior-year sell-through if available.
- Avoid ordering all stock at once for uncertain products.
- Plan end-of-season clearance in advance.
- Without prior-year data, start conservatively and replenish in smaller batches if lead time allows.

## 12. Marketplace-specific note

How and how often stock must be synced with a marketplace panel, and what happens at zero stock, depends on the platform; see KB-24. In general, a panel quantity higher than physical stock leads to order cancellations; a quantity lower than physical stock loses sales.

## 13. Questions a KAM should ask

- How many units of this product sell per day when it's in stock?
- How long does it take from placing a supplier order to having sellable stock?
- When did you last reconcile panel stock with physical stock?
- Which products do you want never to run out?
- Do you have items that haven't sold in the last three months?
- Is this product seasonal, and when does its busy period start?

## 14. What not to conclude

- Do not give a specific reorder quantity without demand, lead time and stock numbers.
- Do not forecast from months distorted by stockouts or promotions without adjustment.
- Do not apply a formula's assumptions (normal demand, stable lead time) blindly.

## 15. Related concepts

Stockouts (KB-09), assortment (KB-17), apparel size inventory (KB-18), cancellations from stock mismatch (KB-14), action planning (KB-23).
