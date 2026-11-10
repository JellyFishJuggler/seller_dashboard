---
doc_id: "sd_platform_022"
title: "Snapdeal Platform Capabilities and Seller API Operations"
domain: "snapdeal_platform"
doc_type: "platform_reference"
source_type: "official_snapdeal"
verification_status: "partially_verified"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - Snapdeal Seller API
  - inventory API
  - pricing API
  - order management API
  - return management API
  - seller notifications
  - onboarding
applies_to:
  - snapdeal_sellers
  - developers
---

# Snapdeal Platform Capabilities and Seller API Operations

## Status and caution
Source: official Snapdeal Seller APIs documentation, v1.1 shown, undated [S001 to S006]. The **prototype is not connected to these APIs**; it uses mock data via Python tools. Do not tell a seller the assistant can change their inventory, prices or orders.

## What the documentation says the APIs cover [S001, S002]
Snapdeal's API index lists these groups: Seller Notifications, Seller Onboarding, Product Listing, Inventory Management, Pricing Management, Order Management, Return Management, Payment Management and Seller Ads/campaign endpoints.

## Access
The documentation has pages on API authentication and authorization [S002]. Calls for inventory, pricing and order APIs require headers X-Seller-Authz-Token, X-Auth-Token and clientId [S003, S004, S005]. The credential process was not read in detail.

## Inventory management [S004]
Sellers can get inventory for one or many products, update inventory for products they have listed, retrieve the status of an update using the upload ID, and list SKU-level update results chronologically.

## Pricing management [S005]
Sellers can get price information, update price points for listed products, check update status by upload ID and view SKU-level update results.

## Product listing [S002]
Endpoints exist for categories, category attributes, searching seller products or all products, posting a new listing (including with external image URLs), uploading images, listing an existing product, editing a listing, fetching image configuration and tracking listing results.

## Order management [S003]
Fulfilment modes: Dropship, Oneship, Oneship Plus, SD+, Vendor Self. APIs fetch new and completed orders, cancelled suborders, manifests, handover sheets (HOS) and stock transfer notes (STN); print invoices and pack slips; mark orders out of stock; update IMEI or serial, invoice details and tracking details; split orders.
- Order date-range queries are limited to 7 days (start and end inclusive) [S003].
- Marking an order out of stock when it cannot be fulfilled may lead to a penalty; refer to policies [S003].

## Return management [S006, S002]
APIs give details of buyer and courier returns; endpoints include pending and completed returns, return-to-vendor packs and return status updates. Seller Notifications can push return events.

## Seller notifications [S002]
Registration and de-registration endpoints exist; contents not reviewed.

## Seller profile and onboarding [S002]
Endpoints exist for primary categories, lead registration, seller registration and seller profile; details not reviewed.

## Payment and ads [S002]
Payment endpoints (payments, transactions, commission invoice, reports) and Seller Ads endpoints (product campaigns, campaign status, reports) are listed. Behavior and eligibility are **unverified**.

## What is not in these sources
Impressions, clicks, conversion rate, ranking logic, competitor prices and review data were not found in the reviewed API documentation. Do not assume Snapdeal exposes them.

## Future integration idea (not current)
A production assistant could call inventory, order and return APIs to replace mock data. This needs seller consent and credentials.
