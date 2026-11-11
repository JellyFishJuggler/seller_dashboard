---
doc_id: "KB-04"
title: "Sales and Demand Analysis"
domain: "ecommerce_business"
doc_type: "business_knowledge"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - falling sales
  - sales decomposition
  - order volume
  - ASP
  - demand
  - seasonality
  - sales concentration
  - organic demand
  - promotional demand
applies_to:
  - general_marketplace
---

# Sales and Demand Analysis

This document explains how to diagnose a fall (or rise) in sales: decompose it into order volume and price effects, localise it to products, test demand versus supply explanations, and choose the next investigation from decision trees. All sample figures are illustrative; the assignment sample seller is used as the central example and is not real Snapdeal data.

## 1. Sales decomposition: volume versus price

Because Sales = Orders × ASP (when each order has one unit; otherwise use units), any change in sales can be split into a **volume effect** and a **price effect**.

- Volume effect = (New orders − Old orders) × Old ASP
- Price effect = New orders × (New ASP − Old ASP)
- Total change = Volume effect + Price effect

**Worked example (sample seller, illustrative)**
- Old: 400 orders × ₹500 = ₹2,00,000. New: 270 × ₹500 = ₹1,35,000.
- Volume effect = (270 − 400) × 500 = −130 × 500 = −₹65,000.
- Price effect = 270 × (500 − 500) = ₹0.
- Total = −₹65,000, equal to the actual change. The whole decline comes from order volume. This is why pricing is not the first thing to investigate when ASP is unchanged.

**Second example (price-driven, illustrative)**: Old: 300 orders × ₹600 = ₹1,80,000. New: 300 × ₹500 = ₹1,50,000. Volume effect = 0; price effect = 300 × (−100) = −₹30,000. Same orders, lower price: the decline is from price or mix.

**Third example (both)**: Old 400 × 500 = 2,00,000. New 340 × 450 = 1,53,000. Volume = −60 × 500 = −30,000. Price = 340 × −50 = −17,000. Total −47,000 ✓.

## 2. Why order volume changes

Orders fall when one or more of these falls: impressions, click-through rate, conversion rate, or the fraction of orders that survive cancellation. They also fall when products become unavailable. Possible reasons for declining orders:

- **Availability**: bestsellers or key sizes out of stock.
- **Visibility**: fewer impressions because of listing quality, relevance, competition or platform changes (not provable without impressions data).
- **Conversion**: price now above alternatives, weaker images, poor reviews, slower promised delivery.
- **Demand**: market-wide dip, end of a season, a trend change.
- **Promotion ending**: demand that was promotion-driven disappears.
- **Cancellations**: orders accepted then cancelled, reducing net orders.
- **Competition**: a new seller or lower-priced alternative (competitor prices are only known if data is available).

## 3. Product-level versus seller-level trends

A seller-level total can mask what is happening. Always break the total down.

- Which products lost the most orders (absolute, not just percent)?
- Were the losses concentrated in a few products or spread broadly? Concentrated losses point to product-specific causes (stockout, content, a competitor). Broad losses suggest seller-wide or market-wide causes (demand, platform-level changes, operational problem).
- Did any products gain? Gains can offset losses and hide problems.

Illustrative: Seller total orders fall by 130. If 5 products account for 110 of the lost orders, investigate those five first.

## 4. Sales concentration

Concentration shows dependence on a few products.

- **Share of sales** = Product sales ÷ Total sales.
- **Top-N share**: sum of shares of the top 3 or 5 products.
- Example: Top 3 products = ₹1,20,000 of ₹2,00,000 = 60%. If one of them goes out of stock, the seller can lose a large fraction of sales quickly.
- Higher concentration means higher risk; stockout and quality problems on top products matter far more than on tail products (see KB-09, KB-17).

## 5. Demand patterns

- **Steady demand**: stable weekly orders; forecast from recent averages.
- **Seasonal demand**: predictable peaks (festivals, weddings, winter, monsoon). Compare with the same period of the previous year when available; do not compare a peak month with a trough month.
- **Trending or fad demand**: quick rise and fall; stock risk.
- **Intermittent demand**: some products sell rarely and unpredictably; forecast poorly with averages.
- **Event-driven demand**: platform sale events, promotions.

If the seller has no prior-year data, say so; do not assert seasonality without evidence.

## 6. Organic versus promotional demand

Organic demand comes from regular search and browsing at normal prices. Promotional demand is created by discounts, coupons, ads or events and tends to pull purchases forward and fade after the promotion.

- Separate baseline orders (before the promotion) from lift orders (during).
- After a promotion, a dip below baseline is common (pull-forward). Judge the promotion over the full cycle: before, during and after.
- Example: baseline 10 orders/day; during promotion 18/day for 7 days; after promotion 7/day for 7 days. Extra over baseline during = 8 × 7 = 56; deficit after = 3 × 7 = 21; net gain = 35 orders over 14 days, before considering margin.

## 7. Decision trees: combinations of sales, orders and ASP

Use these as starting points, not conclusions.

**A. Sales down, orders down, ASP flat (sample seller pattern)**
Volume problem. Next: product-level orders; stockout history; cancellations; impressions/clicks/conversion; season; any promotion that ended.

**B. Sales down, orders flat, ASP down**
Price or mix problem. Next: discounts given; shift toward cheaper products; check margin; check if a promotion is running unintentionally.

**C. Sales down, orders down, ASP down**
Both. Next: decompose into volume and price effects; check whether discounts failed to lift volume or whether cheaper items replaced premium ones.

**D. Sales flat or up, orders up, ASP down**
More orders at lower prices. Next: contribution margin; cancellations and returns on the discounted items.

**E. Sales up, orders flat, ASP up**
Price increase or premium mix. Next: conversion and returns; sustainability of higher price.

**F. Sales flat, orders flat, but net delivered sales down**
Leakage after order: cancellations or returns. Next: cancellation and return rates (KB-14, KB-15).

## 8. Practical steps for a KAM

1. Confirm the periods and metric definitions.
2. Run the volume-versus-price decomposition.
3. Ask for or inspect product-level orders; find the top losers.
4. Test supply explanations (stock, cancellations) before demand explanations, because supply problems are more fixable and quickly testable.
5. Test demand-side explanations with impressions, clicks, conversion, price comparison and season.
6. Report findings as facts, supported hypotheses and unknowns.

## 9. Trade-offs and risks

- Chasing a short-term drop with price cuts can lock in lower margins when the real problem is stock or content.
- Over-attributing the fall to seasonality can excuse fixable problems.
- Looking only at percent changes can hide that a small product with a 50% fall matters less than a major product with a 10% fall.

## 10. Questions a KAM should ask

- Which products usually bring most of your orders, and did they sell less this month?
- Did you run any discount or ad campaign last month, and did it end?
- Do you remember the same period last year being slower or faster?
- Were your best products available through the whole month?
- Did any new competitor or lower-priced similar product appear?

## 11. What not to conclude

- Do not conclude "demand dropped" without ruling out supply and visibility issues.
- Do not assign a rupee loss to one cause without product-level order history.
- Do not call a pattern seasonal without prior-period evidence.
- Do not assume ASP unchanged means no price changes occurred at product level.

## 12. Related concepts

Metrics (KB-02), health diagnostics (KB-03), pricing (KB-05), promotions (KB-07), inventory (KB-08), stockouts (KB-09), search visibility (KB-11), conversion (KB-12), evidence-based reasoning (KB-25).

## 13. Source notes

General analytical technique (price-volume variance analysis, concentration analysis). No platform-specific claims.
