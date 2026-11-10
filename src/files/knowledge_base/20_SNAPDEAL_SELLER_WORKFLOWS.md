---
doc_id: "sd_workflows_020"
title: "Snapdeal Seller Workflows"
domain: "snapdeal_operations"
doc_type: "platform_reference"
source_type: "official_snapdeal"
verification_status: "partially_verified"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - Snapdeal seller panel
  - catalog tab
  - add product
  - track listings
  - edit price and inventory
  - order fulfilment modes
  - returns
applies_to:
  - snapdeal_sellers
---

# Snapdeal Seller Workflows

## Overview and status
This document paraphrases official Snapdeal documents. Panel navigation comes mostly from an older FAQ (V1.2, c. 2018 to 2020) [S007] and a 2019 mailer [S010]; treat navigation as **historical and requiring Seller Panel verification**. API-based workflows come from the Seller API documentation [S002 to S006], which is undated. The assistant is **not connected** to the Seller Panel or APIs in the prototype.

## Seller panel overview
Sources mention a Catalog tab (left side of the dashboard) and a Seller Help tab with listing guidelines and training videos [S007]. No other panel sections were verified. Do not describe panel screens beyond these.

## Product catalogue management
- **Add Product** inside the Catalog tab offers: create a single listing, bulk listing (Lite content sheet, Bulk content sheet, Import your listings) and sell an existing product [S007].
- **Track Listings** shows New, Edit and Existing (multi-mapped) listings with tabs for Under Review, Approved, Rejected and Drafts [S007].
- Rejected listings show reasons; sellers correct and resubmit [S007]. Details in `sd_listing_021`.

## Product listing workflow (single listing, historical steps)
Catalog, Add Product, Create a Single listing; choose category, subcategory, product type and brand; fill product details, attributes and images, shipping and pricing; preview and add to catalog; check status in Track Listings [S007].

## Inventory and pricing workflows
- Panel: Catalog, Edit Price & Inventory (referenced in the automated pricing mailer) [S010].
- Automated pricing: a feature that may adjust prices automatically; reported to be enabled or paused from Edit Price & Inventory, Automated Pricing tab [S010]. Current availability unverified.
- API: inventory and price updates are posted, return an upload ID, and the status is fetched with a feed-result call; SKU-level update results can also be listed [S004, S005].

## Order management
- Fulfilment mode is set at product (SUPC) level: Dropship, Oneship, Oneship Plus (OC+), SD+, Vendor Self [S003].
- Stages include Pending for fulfilment, Printed, Added to manifest or HOS or STN, Shipped, Delivered, Cancelled [S003].
- Typical seller steps in Dropship: print invoice and pack-slip, pack, create a manifest, hand over to courier [S003].
- If a pending order cannot be fulfilled in time, mark it out of stock; this may lead to a penalty per Snapdeal policies [S003]. Amounts are **not verified**.

## Return management
Sellers can retrieve buyer and courier return details via the Return Management APIs and may receive push notifications through Seller Notifications [S006, S002].

## Payment-related workflows
The API index lists Payment Management endpoints (payments, transactions, commission invoice, reports) [S002]. Their behavior was **not read** in detail; do not describe payout rules or timelines.

## Actions requiring seller-panel access or permissions
Everything above. The assistant must say it cannot perform these actions and must not claim to have done them. API use requires seller credentials and headers (X-Seller-Authz-Token, X-Auth-Token, clientId per documentation) [S004].

## Answering seller questions
"I can explain the general process, but please confirm exact steps in your current Seller Panel." See `sd_limits_024`.
