---
doc_id: "inventory_007"
title: "Inventory and Stockout Management"
domain: "inventory"
doc_type: "business_playbook"
source_type: "mixed"
verification_status: "partially_verified"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - stockout
  - out of stock
  - replenishment prioritization
  - safety stock
  - inventory cover
  - bestseller restock
  - dead stock
applies_to:
  - marketplace_sellers
---

# Inventory and Stockout Management

## Overview
A stockout means a listed product has no sellable stock. Lost orders, lost momentum and possible cancellations follow. General guidance [G001]; Snapdeal inventory update method [S004].

## Why stockouts matter
- Shoppers who find a product unavailable choose another seller.
- Orders accepted without stock can be cancelled (see `fulfilment_008`).
- Snapdeal's order documentation warns that marking an order out of stock when it cannot be fulfilled in time **may attract a seller penalty**; details are in Snapdeal policies [S003]. Penalty values are unverified (`sd_limits_024`).

## Prioritizing which stockouts to fix first
Rank out-of-stock products by:
1. Historical order count (higher means more lost demand).
2. Recency of that demand.
3. Contribution per unit (if the seller knows).
4. Restock lead time and supplier availability.
5. Seller cash constraints.
Historical orders give a *relative* priority only; they do not give quantity.

## Bestseller out of stock with significant history
**Problem:** A product with many past orders is out of stock.
**Possible causes:** slow supplier, under-ordering, cash limits, unexpected spike.
**Evidence required:** past orders (tool), current stock, lead time, supplier minimum order.
**Questions:** "When can this item be back?" "What stops you restocking, supplier time or cash?"
**Diagnosis:** Replenishing this product probably recovers more than restocking low-history items, but future demand is not guaranteed.
**Actions:** Restock the top-history products first; ask for lead time before suggesting any quantity.
**Limitations:** We must **not** invent a restock quantity. A quantity needs daily demand, lead time, variability and cash.

## Replenishment fundamentals
- **Inventory cover (days)** = units on hand / average daily sales.
- **Reorder point** = (average daily demand x lead time days) + safety stock.
- **Safety stock** protects against demand and lead-time variability; higher variability needs more.
**Illustrative:** demand 5/day, lead time 10 days, safety stock 15 gives reorder point 65. Real figures must come from the seller.

## Fast and slow movers
Use ABC thinking: a few products (A) drive most orders; protect them. Slow movers (C) tie up cash; avoid deep stocks.

## Dead stock and overstock
Signs: long cover, no orders for a long time. Options: bundle, modest markdown, liquidate, stop reordering. Check margin before discounting (`promotions_012`).

## Seasonality
Plan stock ahead of known demand peaks using last year's same-period orders if the seller has them. Festive or wedding seasons raise demand in some categories (see category playbooks).

## Keeping Snapdeal inventory accurate
Snapdeal's Seller APIs allow sellers to update inventory for listed products; the update is processed asynchronously (an upload ID is returned and its status can be fetched) [S004]. Seller Panel steps need current confirmation (`sd_workflows_020`).

## Risks and limitations
- Overstocking from over-reacting to one strong month.
- Treating a stockout count as a rate without knowing total products.
- Quantities require data the prototype lacks (`data_avail_025`).
