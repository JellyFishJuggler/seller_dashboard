---
doc_id: "fulfilment_008"
title: "Order Fulfilment, Cancellations and Returns"
domain: "operations"
doc_type: "business_playbook"
source_type: "mixed"
verification_status: "partially_verified"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - order cancellation
  - seller cancellation
  - RTO
  - returns
  - dispatch delay
  - fulfilment
  - cancellation rate diagnosis
applies_to:
  - marketplace_sellers
---

# Order Fulfilment, Cancellations and Returns

## Overview
Cancellations and returns reduce net sales, cost money and hurt buyer trust. General guidance [G001]. Snapdeal facts from [S003] and [S006].

## Cancellation categories
| Category | Meaning | Typical examples |
|---|---|---|
| Seller-side | Seller could not or did not fulfil | no stock, late dispatch, pricing error |
| Buyer-side | Buyer cancelled | changed mind, found cheaper, ordered wrong variant |
| Logistics-side | Courier could not pick or deliver | pickup failure, serviceability, address issue |
| System/other | Payment, fraud checks, platform action | payment failure |
The prototype gives only a **cancellation rate**, not the category (`data_avail_025`). Never assign blame from the rate alone.

## Snapdeal facts (official API documentation)
- Fulfilment modes at product level: Dropship, Oneship, Oneship Plus, SD+, Vendor Self [S003].
- If a pending order cannot be fulfilled by the promised ship or handover date, it should be marked out of stock, which may result in a penalty; refer to Snapdeal policies [S003].
- Cancelled orders can be checked through the cancelled-orders endpoints [S003]; courier and buyer returns can be retrieved through Return Management APIs [S006].
- Mobile phones need an IMEI and some computer accessories a serial number before invoice and pack-slip printing [S003].

## Common causes of cancellation
1. **Inventory mismatch:** stock count higher than physical stock.
2. **Delayed dispatch:** orders not packed by the deadline.
3. **Incorrect availability:** variants (size, colour, model) shown but unavailable.
4. **Description mismatch:** buyer cancels after noticing differences.
5. **Operational overload:** volume spikes beyond packing capacity.
6. **Pricing errors:** product listed far below cost.

## Diagnosing a rising cancellation rate
**Problem:** Cancellation rate rose.
**Possible causes:** the six above; plus courier pickup failures.
**Evidence required:** cancellations split by initiator and reason, order-to-dispatch time, stock counts versus physical stock, stockout timing.
**Questions:** "Do you reconcile stock daily?" "Who packs orders and by what time?" "Do cancellations cluster on specific products?"
**Diagnosis:** If cancellations rose when stockouts rose, stock accuracy is a leading hypothesis. If cancellations are on few products, check those listings.
**Actions (max 2 to 3):** reconcile stock and update inventory; set a daily packing cut-off; fix problem listings.
**Limitations:** Without reason codes this is a hypothesis, not a finding.

## Returns, replacements and RTO
- **Customer return:** after delivery. **RTO:** not delivered, returned to seller.
- Returns driven by sizing, compatibility or description mismatch are fixed in the catalogue (see `apparel_017`, `mobileacc_019`, `homedecor_018`).
- Damage-related returns point to packaging.
- RTO clusters by pincode or buyer refusal need courier and address checks.

## Packaging
Snapdeal's historical prohibited-activities policy says sellers should use only Snapdeal standard wrapping materials and not competitor or non-standard packaging; it dates from 2017 and needs verification [S009].

## Additional data needed
Order timestamps (placed, packed, handed over), cancellation reason and initiator, return reasons, courier handover records, pincode.

## Operational improvement ideas
Daily stock reconciliation; dispatch cut-off times; buffer stock on top sellers; barcode or SKU labelling; photo of packed item for disputes (general practice).

## Compliance note
Consumer rules in India require clear return, refund and cancellation information for consumers (secondary summaries only [S011]); verify current text (`sd_limits_024`).
