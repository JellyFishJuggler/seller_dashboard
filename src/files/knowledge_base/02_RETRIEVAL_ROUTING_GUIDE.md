---
doc_id: "routing_002"
title: "Retrieval Routing Guide"
domain: "navigation"
doc_type: "routing_guide"
source_type: "internal"
verification_status: "not_applicable"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - retrieval routing
  - query to document mapping
  - synonyms
  - which document to retrieve
applies_to:
  - rag_pipeline
  - ai_assistant
---

# Retrieval Routing Guide

Use this guide to decide which documents to retrieve for a seller query. Retrieve 2 to 4 documents per turn. Always add `data_avail_025` when the answer depends on a metric, and `sd_limits_024` when the seller asks about a Snapdeal rule or feature.

## Routing by seller problem

### Sales are falling ("sales down", "business slow", "orders kam ho gaye")
Retrieve `diagnostic_005` first, then `pricing_006`, `visibility_010`, `conversion_011`, `inventory_007`. Keywords: revenue drop, month-over-month decline, GMV down, demand fall.

### Cancellations are rising ("cancel zyada", "orders getting cancelled", "cancellation rate high")
Retrieve `fulfilment_008`, then `inventory_007` (stock mismatch), `sd_workflows_020` (how out-of-stock marking works), `data_avail_025`. Keywords: seller cancellation, order rejected, out of stock penalty, late dispatch, SLA.

### Bestseller or high-demand product out of stock ("stock khatam", "stockout")
Retrieve `inventory_007`, `assortment_014`, the category playbook (`apparel_017`, `homedecor_018` or `mobileacc_019`), `sd_platform_022` if inventory update methods are asked.

### Average selling price dropped, or "I am giving discounts"
Retrieve `pricing_006`, `promotions_012`, `diagnostic_005`. Keywords: ASP, margin, discounting, price war, product mix.

### Poor listing, few views, weak search presence
Retrieve `catalogue_009`, `visibility_010`, `sd_listing_021`, `sd_limits_024`. Keywords: title, images, attributes, discoverability, impressions.

### Views but no orders, or high returns
Retrieve `conversion_011`, `reviews_013`, `catalogue_009`, category playbook, `fulfilment_008` for returns.

### Ratings and customer complaints
Retrieve `reviews_013`, `fulfilment_008`, category playbook.

### Growth planning, which products to push, new products
Retrieve `assortment_014`, `actionplan_016`, `promotions_012`.

### Metric definition questions (GMV, AOV, RTO, CTR)
Retrieve `metrics_004` only, plus `data_avail_025` if the seller expects the assistant to quote it.

### Snapdeal rules, panel steps, API, listing rejection
Retrieve `sd_workflows_020`, `sd_listing_021`, `sd_platform_022`, `sd_policy_023`, and always `sd_limits_024`. Answer only from official-source content; state document date and verification status.

### Conversation mechanics (opening, frustrated seller, closing, summary)
Retrieve `conversation_015` and `actionplan_016`. For general role guidance use `kam_003`.

## Category routing
Apparel, garments, kurti, shirt, size, fit: `apparel_017`. Home decor, wall art, showpiece, lamp, curtain, fragile: `homedecor_018`. Mobile accessories, cover, charger, cable, earphones, tempered glass, compatibility: `mobileacc_019`.

## Synonyms and aliases
- Sales = revenue = turnover = GMV (check definitions in `metrics_004`).
- Cancellation = order rejection = order not fulfilled.
- Stockout = out of stock = OOS = inventory zero = stock khatam.
- ASP = average selling price = average price per order item.
- Visibility = discoverability = search presence = reach.
- Conversion = orders per visit = buy rate.
- RTO = return to origin = courier return = undelivered return.
- KAM = key account manager = account manager = relationship manager.

## Sample queries and routing
| Seller query | Retrieve |
|---|---|
| "Meri sales 30 percent gir gayi, kya karun?" | diagnostic_005, data_avail_025, pricing_006 |
| "Why are my orders getting cancelled?" | fulfilment_008, inventory_007 |
| "My top kurti is out of stock" | inventory_007, apparel_017 |
| "Is there a penalty if I mark out of stock?" | sd_workflows_020, sd_limits_024 |
| "Can I put best seller in my title?" | sd_listing_021, catalogue_009 |
| "My cover is returned as not fitting" | mobileacc_019, fulfilment_008 |

## Routing rules for safety
1. Never answer a Snapdeal-policy question from `general_guidance` documents alone.
2. If a metric is not available (see `data_avail_025`), ask the seller or state the limit; do not estimate.
3. Prefer fewer, more relevant chunks over many loosely related ones.
