---
doc_id: "visibility_010"
title: "Search Visibility and Product Discoverability"
domain: "visibility"
doc_type: "business_playbook"
source_type: "general_guidance"
verification_status: "research_based"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - search visibility
  - discoverability
  - impressions
  - click-through rate
  - search relevance
  - product ranking
applies_to:
  - marketplace_sellers
---

# Search Visibility and Product Discoverability

## Overview
Visibility is how often and how prominently shoppers see a product. General guidance [G001]. **Snapdeal's actual ranking algorithm is not documented in the sources reviewed; do not describe or invent it.** One official Snapdeal policy item is relevant: search manipulation (misleading keywords, hidden text) is prohibited [S009, historical].

## Marketplace search fundamentals (general)
Marketplace search typically matches shopper words to product titles, attributes and category, then orders results using relevance and other signals such as price, availability, sales history, ratings and seller performance. Exact weights vary by platform and are not public for Snapdeal here.

## What sellers can control
- Title and attribute relevance.
- Correct category and product type.
- In-stock status (unavailable items cannot convert).
- Price competitiveness and clean listing quality.
- Seller reliability (fewer cancellations).
- Advertising tools if available. Snapdeal's API navigation lists "Seller Ads" and campaign endpoints [S002]; current ad features should be verified in the panel.

## Impressions versus clicks versus orders
Funnel: impressions, clicks, product page visits, orders.
- **Low impressions** suggests the product is rarely shown: relevance, category, availability or ranking issue.
- **Impressions fine, CTR low** suggests the title, main image or price in the results is unattractive.
- **CTR fine, orders low** is a conversion issue (see `conversion_011`).
The prototype has none of these metrics (`data_avail_025`). Ask the seller or request analytics.

## Diagnosing low visibility
**Problem:** Seller thinks products are not being seen.
**Possible causes:** stockouts, poor titles, wrong category, listing quality, new listing with no history, seasonal demand drop.
**Evidence required:** impressions and clicks per product; search terms; listing status (approved or rejected).
**Questions:** "Are your listings live and approved?" "Do you see them when you search by name?"
**Diagnosis:** If listings are not live or are out of stock, visibility will not help; fix that first.
**Actions:** Check listing status; improve title and attributes; restore stock.
**Limitations:** Visibility cannot be measured from current tools; recommendations are hypotheses.

## Traffic quality
More traffic is not better if it does not match the product. Broad keywords can raise views but lower conversion.

## Visibility versus conversion
Increasing visibility on a poorly converting listing wastes effort. Improve conversion basics first when clicks are already healthy.

## Compliance warning
Do not add unrelated brand names, hidden text or misleading keywords; Snapdeal's policy treats this as search manipulation with possible listing removal or suspension [S009].

## Expected outcomes
Better relevance often improves discoverability over time, but no guaranteed ranking or sales change.
