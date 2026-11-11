---
doc_id: "KB-24"
title: "Snapdeal Seller Platform and Operational Knowledge"
domain: "snapdeal_platform"
doc_type: "platform_knowledge"
source_type: "official_documentation_and_third_party"
verification_status: "historical"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - Snapdeal seller API
  - fulfilment modes
  - Dropship
  - Oneship
  - SD+
  - Vendor Self
  - order states
  - seller panel
  - seller notifications
  - returns
applies_to:
  - snapdeal
---

# Snapdeal Seller Platform and Operational Knowledge

This is the only document in the knowledge base that makes Snapdeal-specific claims. It follows a strict evidence rule: a claim is stated as documented only if it appears in an official Snapdeal source that was actually opened. Everything else is labelled unverified or historical. The document status is **historical** because the main official source, the Snapdeal Seller API documentation, has a changelog whose newest entry is dated 1 February 2017. The documentation site was reachable on the check date, but the documented behaviour may have changed since, and current policy must be confirmed with Snapdeal seller support.

Last checked: 2026-11-11.

## 1. Source register for this document

**Official source A (primary)**
- Publisher: Snapdeal (Snapdeal Seller APIs developer documentation).
- URL: http://sellerapis.snapdeal.com/reference/overview (also https://sellerapis.snapdeal.com/).
- Pages opened: Overview; Inventory Management description; Order Management description; Return Management description; Changelog.
- Dates: The pages show no publication date. The changelog's newest dated entry is 1 February 2017 and its oldest entries are from 2016. The page text shows "Updated less than a minute ago", which is a page-rendering label, not a content date.
- Status for this document: official but of unknown currency; treat the content as historical.

**Official source B (limited use)**
- Publisher: Snapdeal.
- URL: https://www.snapdeal.com/info/contactus (buyer-facing help centre).
- Used only to note that buyer help topics exist (order tracking, cancellation before delivery, returns and replacements, refunds). It is buyer-facing and says nothing verified about seller rules.

**Third-party sources (unverified for Snapdeal facts)**
- Unicommerce blog "How to sell on Snapdeal" (https://unicommerce.com/blog/how-to-sell-on-snapdeal-guide/), WareIQ, Shiprocket, RegisterKaro, Streamoid and similar guides describe the Seller Panel, onboarding and listing steps. They are commercial service providers, not Snapdeal. Their statements are not treated as official.
- News reports (Economic Times via third parties, Inc42, YourStory, India TV, Business World) describe 2016-era policy changes. They are historical and must not be presented as current policy.

## 2. What the official API documentation says (documented, historical currency)

### 2.1 Purpose and structure
The documentation describes the Snapdeal Seller APIs as a way for partners and sellers to communicate with Snapdeal programmatically for capabilities such as inventory, pricing and order management. The reference is organised into these sections: Seller Notifications, Seller Onboarding, Product Listing, Inventory Management, Pricing Management, Order Management, Return Management, Payment Management and Seller Ads.

### 2.2 Access
The documentation states that a user must register as an API user and obtain an access token, by submitting a form on the site, and that the Snapdeal API team would respond within about two days. Sandbox and production environments are separate and need separate tokens. The inventory and order pages state that calls carry the headers X-Seller-Authz-Token, X-Auth-Token and clientId. These are access details for developers and are not business advice.

### 2.3 Inventory management
The documentation says the inventory process lets sellers update stock for products they have listed. Updating inventory returns an uploadId that can be used with a feed-result call to check the update status, and a separate result call shows SKU-level status of the seller's update operations in chronological order. The changelog notes seller SKU support was added to inventory and price update calls in June 2016. Get-inventory calls (bulk and single) are listed in the reference.

Business meaning: inventory on Snapdeal is a number the seller must keep updated. If the number is wrong, orders can be taken for items the seller cannot ship. Whether the platform auto-hides zero-stock listings is **not stated** in the pages opened and needs confirmation.

### 2.4 Pricing management
The reference lists calls to get price (bulk and single) and update price, with a feed-result mechanism like inventory. No rules about price caps, discounts, margins or fees were found in the opened pages. One third-party news report from the 2016 era described a cap on discount percentages; its current validity is unverified and must not be quoted as current policy.

### 2.5 Order management and fulfilment modes
The documentation says order management supports order processing from placement to delivery, depending on a fulfilment mode set at seller SUPC (Snapdeal product code) level. Five modes are named: Dropship, Oneship, Oneship Plus (OC+), SD+ and Vendor Self.

- **Dropship**: Snapdeal takes the order and notifies the seller and assigns the courier; the seller prints the pack slip and invoice, packs, creates a manifest and physically hands items to the courier; the courier delivers.
- **Oneship**: the seller prints, packs and creates a Hand Over Sheet (HOS); inbound couriers collect from sellers and take items to a Oneship centre; outbound couriers then deliver.
- **Oneship Plus (OC+)**: the seller prints and pastes a barcode and creates a Stock Transfer Note (STN); the item is picked up unpacked, and packing and quality check happen at the OC+ centre before it goes to the courier.
- **SD+**: Snapdeal stores the seller's items in its warehouse before an order, processes and ships the order, and notifies the seller.
- **Vendor Self**: the seller handles everything from processing to delivery and must update Snapdeal at each step, including selecting the courier and confirming delivery.

Order states named in the documentation: PFF (pending for fulfilment), PRNT (printed), MFG (item added to manifest), BARP (barcode printed), AHOS (added to HOS), ASTN (added to STN), SHP (courier enables tracking/shipped), FFD (delivered) and CLD (cancelled).

Documented seller actions in the pending-for-fulfilment state include: marking an order out of stock when it cannot be fulfilled in time (the order is then cancelled for the seller), providing IMEI or serial numbers where required (for example mobile phones and some computer accessories), providing an invoice number where the seller uses manual invoice mode, giving courier and tracking details in Vendor Self mode, splitting packages when suborders cannot ship together, and printing pack slip, invoice or barcode.

The documentation includes this warning in the Dropship, Oneship and Oneship Plus steps: if a pending order cannot be fulfilled by the promised ship date or handover date, it must be marked out of stock, and the documentation adds that this **may result in a penalty** and refers to Snapdeal policies for details. The penalty amount and rules are not stated and are unverified.

Other documented details: order list calls accept a start and end date in epoch format with a maximum span of seven days; the newest changelog entry (1 February 2017) said the new-orders call returns orders in descending order of creation time and can filter by PFF or PRNT status.

### 2.6 Cancelled orders
The reference lists calls to read cancelled suborders (single and all). The cancellation reason categories and who is responsible in each case are **not** described in the pages opened.

### 2.7 Return management
The documentation says the section provides details of both buyer returns and courier returns, and that sellers can receive a push notification when an order is returned by a buyer or courier (via Seller Notifications). Calls exist to read pending and completed returns, dispute issue categories, return-to-vendor (RTV) packs for Oneship and OC+, and return-status updates for courier, Oneship, OC+ and buyer returns. Return eligibility rules, timelines, who bears cost, and refund timelines are **not** stated in the pages opened.

### 2.8 Notifications, payments and ads
Seller Notifications allow registering and de-registering for push notifications. Payment Management lists calls for payments, transactions, commission invoices and report retrieval. A Seller Ads section lists campaign-related calls. The content of fees, commission rates, payout cycles and ad pricing is **not** given in the opened pages.

## 3. Onboarding, Seller Panel and listing (unverified, third-party descriptions only)

No official Seller Panel help page was successfully opened. Third-party guides commonly state that registration happens at sellers.snapdeal.com, that GST and bank details are needed, that a Seller Panel and a mobile app are used to manage inventory, prices and orders, and that products are added through a catalogue section, sometimes with Excel templates. These are **unverified**. Dashboard navigation labels, menu paths and required documents must be confirmed from current official seller help or seller support before being given to a seller.

The official API documentation does confirm that onboarding and listing capabilities exist through APIs (lead and seller registration calls; category, attribute and listing calls including image upload and edit listing; listing tracking). That shows the data a listing needs are category-driven (category attributes are fetched per category), but the specific mandatory fields per category were not reviewed.

## 4. Historical news that must not be treated as current policy

Reports from 2016 described Snapdeal changing seller policies, including simplifying policies, adjusting marketing fee levels across many sub-categories, tightening electronics return acceptance, and sharing return costs. A later report described a communication to sellers limiting discounts above a certain percentage. These were press accounts of past announcements. They are historical or unverified for today. Never state any of them as a current rule, fee, penalty or discount cap.

## 5. What is not verified (needs confirmation from current official seller support)

- Current commission, marketing fee, shipping fee and payment-gateway charges.
- Current penalties for seller-side cancellations, late dispatch or out-of-stock marking.
- Payout cycle and payment hold rules.
- Search ranking, listing quality scoring or any algorithm.
- Seller Panel navigation, report names, metrics definitions and available analytics.
- Seller support and escalation channels and response times.
- Return and refund timelines and cost responsibilities for sellers.
- Whether each fulfilment mode (Dropship, Oneship, Oneship Plus, SD+, Vendor Self) is currently offered to a given seller.

## 6. How a KAM should use this knowledge

- Use the general operating logic (orders move through states; the seller must update stock; failing to ship in time forces an out-of-stock cancellation) as context, always with the caveat that it is from documentation of unknown currency.
- Ask the seller which fulfilment model applies to their SUPCs instead of assuming.
- When a seller asks about fees, penalties, payouts or ranking, say that the figure or rule must be confirmed through current seller support, and offer to note the question as an action.
- Never turn a general marketplace practice from other documents into a claimed Snapdeal policy.

## 7. Questions a KAM should ask

- Which fulfilment mode are your products on?
- Do you update stock through the panel, a spreadsheet or an integration?
- Do you receive return or cancellation notifications, and where do you see the reasons?
- Have you received any written policy communication from Snapdeal about penalties or fees?

## 8. Related concepts

Order management and fulfilment (KB-13), cancellation root causes (KB-14), returns (KB-15), inventory (KB-08), evidence discipline (KB-25).
