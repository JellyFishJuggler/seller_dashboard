---
doc_id: "source_register_001"
title: "Source Register"
domain: "navigation"
doc_type: "source_register"
source_type: "internal"
verification_status: "maintained"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - source register
  - citations
  - Snapdeal official documentation
  - source reliability
applies_to:
  - knowledge_base_maintainers
---

# Source Register

All external sources used by the knowledge base. "Date researched" is 2026-11-11 for every entry. Status values: **current** (official, no sign of replacement), **historical** (dated and probably superseded or aged), **unverified** (could not confirm currency or authority).

## Snapdeal official sources

### S001: Snapdeal Seller APIs Overview
- Publisher: Snapdeal (sellerapis.snapdeal.com)
- URL: https://sellerapis.snapdeal.com/reference/overview
- Type: official API documentation
- Revision date: not shown
- Access note: direct page fetch was blocked by robots rules; only the search-result snippet was read (describes APIs for inventory, pricing, order management etc.)
- Reliability: high for existence of APIs; low depth
- Status: current (undated)
- Used by: sd_platform_022, sd_workflows_020

### S002: Snapdeal Seller APIs reference index (API groups and endpoint list, v1.1)
- Publisher: Snapdeal
- URL: http://sellerapis.snapdeal.com/reference/ocplusstnprint-1 (navigation lists all API groups)
- Type: official API documentation index
- Revision date: not shown; shows "v1.1"
- Reliability: high for which API groups and endpoints exist
- Status: current (undated)
- Used by: sd_platform_022, sd_workflows_020, sd_limits_024

### S003: Snapdeal Seller APIs, Order Management description
- Publisher: Snapdeal
- URL: https://sellerapis.snapdeal.com/reference/description-2
- Type: official API documentation
- Revision date: not shown
- Reliability: high; describes fulfilment modes, order states, out-of-stock marking
- Status: current (undated)
- Used by: sd_workflows_020, sd_platform_022, fulfilment_008, mobileacc_019

### S004: Snapdeal Seller APIs, Inventory Management description
- URL: http://sellerapis.snapdeal.com/reference/description-4
- Publisher: Snapdeal; type official API documentation; revision date not shown; reliability high; status current (undated)
- Used by: sd_platform_022, sd_workflows_020, inventory_007

### S005: Snapdeal Seller APIs, Pricing Management description
- URL: http://sellerapis.snapdeal.com/reference/description-5
- Publisher: Snapdeal; type official API documentation; revision date not shown; reliability high; status current (undated)
- Used by: sd_platform_022, sd_workflows_020, pricing_006

### S006: Snapdeal Seller APIs, Return Management description
- URL: http://sellerapis.snapdeal.com/reference/description-6
- Publisher: Snapdeal; type official API documentation; revision date not shown; reliability high but very brief; status current (undated)
- Used by: sd_platform_022, fulfilment_008

### S007: Listing Your Product FAQs (V1.2)
- Publisher: Snapdeal
- URL: https://sellercom.snapdeal.com/seller/2018/2020/Listing%20Your%20Product%20FAQs-V1.2.pdf
- Type: official seller FAQ (PDF)
- Revision date: version "V1.2"; file path suggests 2018 to 2020; exact date not shown
- Reliability: high authority, aged
- Status: **historical / requires verification** (panel navigation and figures may have changed)
- Used by: sd_listing_021, sd_workflows_020, catalogue_009, apparel_017

### S008: Listing Content Guidelines (general image and size chart guidelines)
- Publisher: Snapdeal
- URL: https://sellercom.snapdeal.com/seller/All%20Policies/2022/Content%20PTwise%20Guideline/6434.pdf
- Type: official guideline deck (PDF)
- Revision date: not shown; path folder "2022"
- Reliability: high authority; apparel-leaning examples
- Status: **requires verification** (undated; newer category guidelines may exist in Seller Panel)
- Used by: sd_listing_021, apparel_017, catalogue_009

### S009: Prohibited Seller Activities and Consequences Policy
- Publisher: Snapdeal
- URL: https://sellercom.snapdeal.com/seller/All%20Policies/ProhibitedSellerActivitiesAndConsequencesPolicy.pdf
- Type: official policy (PDF), forms part of the Seller Agreement
- Revision date: version 1.2 dated 01-07-2017 (v1.0 01-02-2016, v1.1 14-07-2016)
- Reliability: high authority
- Status: **historical / requires verification** (latest version seen is 2017)
- Used by: sd_policy_023, sd_limits_024, catalogue_009, visibility_010, reviews_013

### S010: Automated Pricing mailer
- Publisher: Snapdeal
- URL: https://sellercom.snapdeal.com/seller/All%20Policies/Automated_Pricing_Mailer.html
- Type: official seller announcement
- Revision date: linked assets are dated 01-11-2019 (November 2019)
- Reliability: high authority, aged
- Status: **historical / requires verification** (the linked how-to and FAQ PDFs returned errors when fetched)
- Used by: pricing_006, sd_workflows_020, sd_limits_024

## Regulatory and standards sources (secondary summaries)

### S011: Consumer Protection (E-Commerce) Rules, 2020: law-firm summaries
- Publisher: various law firms (e.g. https://www.mondaq.com/india/dodd-frank-consumer-protection-act/970010/safety-net-for-online-shopping-woes ; https://www.indialaw.in/guides/civil/consumer-protection-e-commerce-rules/)
- Type: secondary legal commentary. The official gazette text was **not** retrieved.
- Revision date: 2020 rules (notified 23 July 2020); summaries dated 2020 to 2024
- Reliability: medium
- Status: unverified against official text
- Used by: sd_policy_023, sd_limits_024, fulfilment_008

### S012: Reports of 2026 amendments to the E-Commerce Rules
- URLs: https://www.indialaw.in/blog/consumer/consumer-protection-e-commerce-amendment-rules-2026/pdf/ ; https://foxmandal.in/?p=59924
- Type: secondary legal commentary reporting a notification in September 2026
- Reliability: low to medium (not confirmed on an official government site)
- Status: **unverified**
- Used by: sd_limits_024, sd_policy_023

### S013: IS 19000:2022 Online Consumer Reviews (BIS / Department of Consumer Affairs)
- URL: https://www.mondaq.com/india/doddfrank-consumer-protection-act/1263914/framework-launched-by-the-government-of-india-to-restrict-fake-reviews-on-ecommerce-sites ; https://en.vikaspedia.in/viewcontent/social-welfare/social-awareness/consumer-education/bis-framework-for-online-consumer-reviews
- Type: news and public-information summaries of a standard
- Revision date: launched November 2022; described as voluntary initially; later reports mention plans to make it mandatory (status unverified)
- Reliability: medium
- Status: unverified for current legal force
- Used by: reviews_013

## Sources reviewed and deliberately not relied on
### S014: Third-party integration notes for Snapdeal APIs (Atlassian page by an integrator)
- URL: https://auperator.atlassian.net/wiki/spaces/POE/pages/3711238149/Snapdeal+Integration
- Type: third-party; reliability low; used only to corroborate that the order-rejection endpoint is treated as out-of-stock. Not used for any policy claim.

### S015: Unattributed slide decks on seller order penalties and SLA
- Example: https://www.slideshare.net/slideshow/orders-overview-95823837/95823837
- Type: unattributed; could not confirm publisher or platform. **No penalty percentages from these decks are used anywhere.**

## General knowledge
### G001: General e-commerce, inventory, pricing and analytics frameworks
Standard textbook formulas and practices (revenue decomposition, safety stock, break-even, funnel analysis, price elasticity, ABC analysis). No single URL; these were not individually web-verified in this build. Documents tag such content `general_guidance`. Used by most business playbooks.
