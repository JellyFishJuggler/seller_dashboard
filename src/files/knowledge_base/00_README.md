---
doc_id: "readme_000"
title: "Knowledge Base README: Seller KAM Assistant"
domain: "navigation"
doc_type: "navigation"
source_type: "internal"
verification_status: "not_applicable"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - knowledge base overview
  - seller KAM assistant
  - RAG documentation
  - how to update knowledge base
applies_to:
  - knowledge_base_maintainers
  - rag_pipeline
---

# Seller KAM Knowledge Base: README

## Purpose
This knowledge base supports an AI Seller Key Account Manager (KAM) assistant on a Snapdeal-style seller dashboard. It holds **business knowledge**: metric definitions, diagnostic methods, playbooks, conversation guidance and Snapdeal platform information. It never holds live seller data.

**Hard rule:** actual seller numbers (sales, orders, cancellation rate, ASP, stockout records) must always come from the backend Python tools. Documents here use only clearly labelled *illustrative* numbers. See `data_avail_025` for what the prototype can and cannot measure.

## What the assistant is expected to do
1. Understand the seller's business situation in voice or text.
2. Spot unusual patterns in the metrics returned by tools.
3. Investigate causes of falling sales, high cancellations, stockouts and weak products.
4. Ask a small number of relevant diagnostic questions.
5. Retrieve playbooks and recommend 2 to 3 prioritized actions with reasons.
6. Confirm which actions the seller agrees to.
7. Summarize the conversation and follow-ups.

## Document map
| ID | File | Purpose |
|---|---|---|
| readme_000 | 00_README.md | This guide |
| source_register_001 | 01_SOURCE_REGISTER.md | All sources with IDs (S001...) |
| routing_002 | 02_RETRIEVAL_ROUTING_GUIDE.md | Which document answers which query |
| kam_003 | 03_KAM_PRINCIPLES.md | KAM role, prioritization, trust |
| metrics_004 | 04_ECOMMERCE_METRICS_GLOSSARY.md | Metric definitions and formulas |
| diagnostic_005 | 05_BUSINESS_DIAGNOSTIC_FRAMEWORK.md | Root-cause framework and scenarios |
| pricing_006 | 06_PRICING_AND_MARGIN_MANAGEMENT.md | ASP, margin, discounting risk |
| inventory_007 | 07_INVENTORY_AND_STOCKOUT_MANAGEMENT.md | Stockouts, replenishment priority |
| fulfilment_008 | 08_ORDER_FULFILMENT_CANCELLATIONS_AND_RETURNS.md | Cancellations, RTO, returns |
| catalogue_009 | 09_CATALOGUE_AND_PRODUCT_LISTING_OPTIMIZATION.md | General listing quality |
| visibility_010 | 10_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md | Discoverability |
| conversion_011 | 11_CONVERSION_AND_CUSTOMER_EXPERIENCE.md | Funnel and conversion |
| promotions_012 | 12_PROMOTIONS_DISCOUNTS_AND_UNIT_ECONOMICS.md | Promotions and profitability |
| reviews_013 | 13_PRODUCT_RATINGS_REVIEWS_AND_QUALITY.md | Ratings and reviews |
| assortment_014 | 14_PRODUCT_ASSORTMENT_AND_SELLER_GROWTH.md | Portfolio and growth |
| conversation_015 | 15_SELLER_DISCOVERY_AND_CONVERSATION_PLAYBOOK.md | Voice conversation craft |
| actionplan_016 | 16_SELLER_ACTION_PLANNING_AND_FOLLOW_UP.md | Action plans and follow-up |
| apparel_017 | 17_APPAREL_SELLER_PLAYBOOK.md | Apparel specifics |
| homedecor_018 | 18_HOME_DECOR_SELLER_PLAYBOOK.md | Home decor specifics |
| mobileacc_019 | 19_MOBILE_ACCESSORIES_SELLER_PLAYBOOK.md | Mobile accessories specifics |
| sd_workflows_020 | 20_SNAPDEAL_SELLER_WORKFLOWS.md | Verified Snapdeal workflows |
| sd_listing_021 | 21_SNAPDEAL_LISTING_AND_CONTENT_GUIDELINES.md | Snapdeal listing rules |
| sd_platform_022 | 22_SNAPDEAL_PLATFORM_CAPABILITIES_AND_OPERATIONS.md | Seller API capabilities |
| sd_policy_023 | 23_SNAPDEAL_SELLER_POLICIES_AND_RISK_GUIDELINES.md | Policies and account risk |
| sd_limits_024 | 24_SNAPDEAL_POLICY_LIMITATIONS_AND_ESCALATION.md | When not to guess |
| data_avail_025 | 25_DATA_AVAILABILITY_AND_DIAGNOSTIC_LIMITATIONS.md | Prototype data limits |

## How documents are meant to be used
- Retrieve by intent using `routing_002`. Retrieve `data_avail_025` whenever a diagnosis depends on a metric.
- Treat `source_type: official_snapdeal` content as the only basis for Snapdeal-specific claims. Content tagged `general_guidance` is general e-commerce practice, never Snapdeal policy.
- Always read `verification_status` and `last_verified`. When status is `historical` or `unverified`, say so to the seller and point to the Seller Panel.

## Adding a new document
1. Choose the next free number and a single coherent topic.
2. Add YAML front matter (same keys as existing files) with a unique `doc_id`.
3. Use self-contained sections with descriptive headings; cross-reference by `doc_id`.
4. Register every external source in `source_register_001` before citing it.
5. Add the file to the map above and to `routing_002`.

## Updating outdated information
1. Re-fetch the official source and compare against the stored revision date.
2. Update the document text, bump `version`, and change `last_verified`.
3. Update the source's status and "Used by" list in `source_register_001`.
4. If a rule cannot be re-verified, change `verification_status` to `unverified` and add a note in `sd_limits_024`.
5. Re-embed only the changed documents.
