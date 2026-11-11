---
doc_id: "KB-13"
title: "Order Management and Fulfilment"
domain: "ecommerce_business"
doc_type: "business_knowledge"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - order lifecycle
  - order processing
  - picking and packing
  - dispatch
  - fulfilment models
  - inventory synchronisation
  - delivery
applies_to:
  - general_marketplace
---

# Order Management and Fulfilment

This document explains how orders move from purchase to delivery in marketplace e-commerce, where delays and failures arise, and how sellers can run efficient operations. It describes **general** marketplace practice. Snapdeal-specific modes and states are documented separately, with their verification limits, in KB-24; do not treat general steps here as Snapdeal policy.

## 1. The general order lifecycle

1. **Order placed** by the buyer (prepaid or cash on delivery).
2. **Order confirmed** (payment or address checks by the platform).
3. **Seller notified** and order awaits action.
4. **Seller accepts or processes** the order; stock is reserved.
5. **Picking**: locating the item in the warehouse.
6. **Packing**: packaging the item, attaching invoice and label.
7. **Handover/dispatch**: courier collects or seller hands over.
8. **In transit** with tracking updates.
9. **Delivery** to the buyer (or delivery failure and return to origin).
10. **Post-delivery**: return window, refunds, ratings.

At each step the order may be delayed or cancelled.

## 2. Inventory synchronisation

The number of units shown as available must match physical stock minus units reserved for open orders. Common causes of mismatch: selling the same stock on several channels, manual updates, damaged or lost items, returns not restocked, and delays in updating. A mismatch produces orders the seller cannot ship (seller-side cancellations). Sync should be as automatic and frequent as the seller's systems allow, with a safety buffer on fast-moving items.

## 3. Order acceptance and processing speed

Fast acceptance and packing reduce cancellations and buyer anxiety. Practices:
- Check new orders at fixed times (several times a day).
- Pack on the same day when possible.
- Keep packing material ready.
- Keep printing of invoices and labels simple.
- Flag stockouts immediately instead of waiting.

Whether a platform sets deadlines and penalties for late processing is platform-specific. The official Snapdeal API documentation says orders that cannot be fulfilled by the promised date must be marked out of stock and may incur a penalty, with details left to policy (KB-24); the amount is not verified.

## 4. Picking and packing

- Keep a clear location for each SKU.
- Verify product, size, colour, variant against the order before packing.
- Use appropriate packaging for fragile, liquid or electronic items (see KB-19, KB-20).
- Check item condition before sealing.
- Include invoice and any required inserts.
Errors at this stage cause wrong-item and damaged-item returns.

## 5. Dispatch and shipment tracking

Dispatch means handing the parcel to the courier (or the platform's designated process). Keep handover records (manifest or handover sheet where used), count parcels, and note timestamps. Track shipments; investigate parcels with no movement. Delays after handover are courier-side, but proof of timely handover protects the seller in disputes.

## 6. Delivery and failed delivery

Delivery can fail because of incorrect address, unreachable buyer, refusal (common with cash on delivery), or courier problems. Failed deliveries are returned to origin (RTO, KB-15). Reducing them: verify addresses where possible, accurate product content, and responsive communication where the platform allows.

## 7. Fulfilment delays

Typical causes: late order checking, out-of-stock discovered at packing, packing bottlenecks, lack of materials, waiting for couriers, printing or documentation issues, staff gaps. Track "time from order to handover" for each order; the average and the slowest 10% reveal bottlenecks.

## 8. Seller operational efficiency

Metrics (use the seller's own history): order-to-dispatch time, orders handled per person per day, error rate (wrong or damaged items), stock accuracy (cycle count match rate), and cancellation due to seller reasons. Improve by standardising processes, batching similar orders, labelling shelves, and training.

## 9. Fulfilment models in e-commerce (general)

- **Seller-fulfilled**: seller stores, packs, ships.
- **Marketplace-fulfilled (warehouse model)**: seller sends stock to the marketplace's warehouse; the marketplace packs and ships.
- **Hybrid or aggregator models**: courier or centre collects from seller, with packing or consolidation at an intermediate centre.
- **Dropshipping**: a seller lists items fulfilled by a supplier directly.

Each differs in control, cost, speed and risk. For example, warehouse models reduce seller packing work but need stock planning and may have storage costs.

Snapdeal's documented modes are named in KB-24 (Dropship, Oneship, Oneship Plus, SD+, Vendor Self). Never assume which mode applies; ask the seller.

## 10. Diagnosing operational problems

1. Measure order-to-dispatch time and its spread.
2. Count cancellations by reason (KB-14).
3. Compare panel stock with physical stock.
4. Review wrong/damaged item returns.
5. Interview staff or the seller about bottlenecks.

## 11. Questions a KAM should ask

- Who processes orders, and how often do they check for new ones?
- How long does it take from order to handover on a typical day?
- Do you ever discover at packing time that an item isn't in stock?
- Do you sell on other channels from the same stock?
- How do you pack fragile or high-value items?
- Do you keep handover records?

## 12. What not to conclude

- Do not describe Snapdeal's process from general steps.
- Do not blame couriers or sellers without evidence.
- Do not assume delays are seller-caused unless handover timing shows so.

## 13. Related concepts

Cancellations (KB-14), returns (KB-15), inventory (KB-08), platform knowledge (KB-24).
