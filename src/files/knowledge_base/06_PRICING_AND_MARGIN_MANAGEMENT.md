---
doc_id: "pricing_006"
title: "Pricing and Margin Management"
domain: "pricing"
doc_type: "business_playbook"
source_type: "mixed"
verification_status: "partially_verified"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - pricing strategy
  - average selling price
  - margin optimization
  - competitive pricing
  - price elasticity
  - break-even
  - automated pricing Snapdeal
applies_to:
  - marketplace_sellers
---

# Pricing and Margin Management

## Overview
Pricing affects order volume, ASP and profit at once. This document gives the logic for pricing advice. General guidance is from [G001]; Snapdeal automated-pricing facts come from [S010] (dated 2019, historical).

## Competitive pricing fundamentals
Buyers compare similar listings. Price competitiveness matters most for commodity-like products (for example generic cables); differentiated products (unique decor) rely more on content and trust. Competitor prices are **not** in the prototype; ask the seller what comparable listings cost, or state that the comparison is unverified.

## Understanding ASP
ASP moves for three reasons: price changes, discount depth and product mix. A falling ASP with rising orders can mean discount-driven volume. A flat ASP with falling orders points elsewhere (stock, visibility). See `diagnostic_005`.

## Margin basics
- Gross margin % = (price - cost) / price.
- Contribution margin per unit = price - cost - commission/fees - shipping - packaging - returns allowance.
- **Break-even volume** for a price cut: if contribution is C per unit and a cut of d reduces it to C - d, orders must grow by at least C / (C - d) - 1 just to keep total contribution unchanged.
**Illustrative:** C = 80, cut d = 20 gives 80/60 - 1 = 33% more units required just to break even.

## Price elasticity (basics)
Elasticity = % change in quantity / % change in price. Elastic demand (many substitutes) responds strongly; inelastic demand does not. A seller cannot assume elasticity: it must be tested.

## Discounting and perceived value
Deep or constant discounts can signal low quality, anchor buyers on low prices and erode margin. Misstating MRP is prohibited (see `sd_policy_023`). Discount should come off a truthful MRP.

## Pricing experiments
Change one product at a time, for a fixed window, with stock available. Record starting orders and contribution. Judge on orders and contribution, not orders alone. Seasonal noise can mislead; compare against a similar period when possible.

## Snapdeal automated pricing (historical source)
A 2019 mailer says an automated pricing feature, when enabled, may change prices of listed products automatically to improve conversion and margins and the chance of getting the buy button. Reported navigation: Catalog tab, Edit Price & Inventory, Automated Pricing tab, Enable Automation; it can be paused or resumed [S010]. **Requires current Seller Panel verification**; rule details were in linked PDFs that could not be retrieved. If a seller sees unexplained ASP change, ask whether automation is on.

## Diagnostic scenarios
**Problem:** Seller wants to cut prices because sales fell.
**Possible causes:** real price disadvantage, or stockouts, visibility, listing issues.
**Evidence required:** ASP trend, stockouts, competitor prices (ask), margin.
**Questions:** "What does the same product cost elsewhere?" "What is your margin per unit?"
**Diagnosis:** Without a price gap and margin room, a cut is a gamble.
**Actions:** Fix supply and listing first; test a small price change on one product if a gap is confirmed.
**Limitations:** No competitor or margin data in tools.

**Problem:** ASP dropped but the seller did not change prices.
**Possible causes:** mix shift, automated pricing, discount campaigns.
**Actions:** Check mix and automation status with the seller.

## Risks
- Margin erosion and price wars.
- Price edits on listings with low stock that lead to cancellations.
- Competitor-matching without cost awareness.

## Recommendation rule
Never recommend a price reduction unless margin and a competitor comparison (even seller-reported) are considered. Never promise a sales lift.
