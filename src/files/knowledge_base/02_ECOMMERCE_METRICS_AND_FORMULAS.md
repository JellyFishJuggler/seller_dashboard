---
doc_id: "KB-02"
title: "E-commerce Metrics and Formulas"
domain: "ecommerce_business"
doc_type: "business_knowledge"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - GMV
  - net sales
  - ASP
  - AOV
  - cancellation rate
  - return rate
  - RTO rate
  - conversion rate
  - CTR
  - stockout rate
  - inventory turnover
  - sell-through
  - contribution margin
  - gross margin
applies_to:
  - general_marketplace
---

# E-commerce Metrics and Formulas

This is a reference for the metrics a Key Account Manager uses to read a seller's business. Each metric has a definition, formula, worked example, interpretation, common mistakes and companion metrics. No universal industry benchmarks are given: "good" levels differ by category, price band, season and platform, so compare a seller with its own history and with like-for-like products.

Marketplaces and sellers define some metrics differently (for example, whether cancelled orders are counted in "orders"). Always confirm the definition used by the data source before comparing numbers. All numbers below are illustrative.

## 1. Sales-value metrics (not interchangeable)

### GMV (Gross Merchandise Value)
- **Definition**: Total value of goods ordered, usually before cancellations, returns, discounts borne by others, taxes or fees, depending on the definition used.
- **Formula**: GMV = Σ (selling price × quantity) over orders placed.
- **Example**: 400 orders × ₹500 = ₹2,00,000 GMV.
- **Interpretation**: A demand-side measure of what buyers tried to buy. It overstates money earned if cancellations and returns are high.
- **Common mistakes**: Treating GMV as revenue or profit; mixing GMV (orders placed) with delivered sales.
- **Check with**: cancellation rate, return rate, net sales.

### Gross sales and net sales
- **Gross sales** = sales value before deducting cancellations, returns and refunds.
- **Net sales** = gross sales − cancelled order value − returned/refunded value (− discounts if tracked separately).
- **Example**: Gross ₹2,00,000; cancelled ₹16,000; returned ₹10,000. Net sales = 2,00,000 − 16,000 − 10,000 = ₹1,74,000.
- **Interpretation**: Closer to money the seller actually keeps before costs. Falling net sales with steady gross sales signals leakage from cancellations or returns.

### Revenue versus sales versus profit
- Sales (or GMV) describes order value. Revenue is what the seller recognises as income, which depends on accounting treatment, taxes and platform deductions. Profit is revenue minus all costs. These three differ and must never be used as synonyms. A seller can have rising sales and falling profit (see KB-06).

### Revenue growth and order growth
- **Formula**: Growth % = (This period − Last period) ÷ Last period × 100.
- **Example (assignment sample seller, illustrative)**: Sales ₹2,00,000 → ₹1,35,000. Change = −65,000 ÷ 2,00,000 = −32.5%. Orders 400 → 270: −130 ÷ 400 = −32.5%.
- **Interpretation**: Identical sales and order growth with unchanged ASP means the whole change is from order volume.
- **Mistake**: Comparing unequal periods (30-day month versus 28-day month, or festival month versus normal month).

## 2. Price and basket metrics

### ASP (Average Selling Price)
- **Definition**: Average price per unit or per order line sold.
- **Formula**: ASP = Sales value ÷ Units sold (or ÷ orders if one unit per order).
- **Example**: ₹1,35,000 ÷ 270 = ₹500.
- **Interpretation**: ASP can rise because of price increases, or because the mix shifted to costlier products. It can fall from discounts or a shift to cheaper items. An unchanged ASP can still hide offsetting changes in mix and price.
- **Mistakes**: Assuming a constant ASP means no price change at product level.

### AOV (Average Order Value)
- **Definition**: Average value of one order.
- **Formula**: AOV = Sales value ÷ Number of orders.
- **Interpretation**: Differs from ASP when orders contain several units. Bundles and cross-selling raise AOV without changing ASP per unit.

## 3. Volume and funnel metrics

### Orders and units sold
- Orders are purchase events; units are items. One order may hold multiple units. Use units for inventory planning and orders for fulfilment workload.

### Impressions, clicks, CTR
- **Impressions**: Times a listing was shown.
- **Clicks**: Times it was opened.
- **CTR** = Clicks ÷ Impressions × 100.
- **Example**: 20,000 impressions, 600 clicks → CTR 3.0%.
- **Interpretation**: Low CTR with healthy impressions suggests weak title, image, price or relevance. Low impressions suggest a visibility problem (KB-11).
- **Mistake**: Comparing CTR across very different placements or categories.

### Conversion rate
- **Formula**: Conversion rate = Orders ÷ Clicks (or visits/sessions) × 100.
- **Example**: 600 clicks, 30 orders → 5.0%.
- **Interpretation**: Low conversion despite good clicks points to price, trust, content mismatch, stock-by-size availability or delivery expectations (KB-12).
- **Mistake**: Using impressions as the denominator without saying so; the result then blends CTR and conversion.

## 4. Order quality metrics

### Cancellation rate
- **Formula**: Cancellation rate = Cancelled orders ÷ Orders placed × 100.
- **Example (illustrative)**: 8% of 400 = 32 cancelled; 14% of 270 ≈ 38 cancelled.
- **Interpretation**: A rise of 6 percentage points. Note the percentage-point versus percent difference: 8% → 14% is +6 percentage points, or a 75% relative increase.
- **Mistake**: Assuming all cancellations are the seller's fault; buyer-side, logistics and system-related cancellations exist (KB-14). Also check whether "orders" in the denominator includes cancelled ones.

### Return rate
- **Formula**: Return rate = Returned units (or orders) ÷ Delivered units (or orders) × 100.
- **Mistake**: Using orders placed as the denominator, which understates the rate.

### RTO rate (Return to Origin)
- **Definition**: Orders sent out but returned undelivered (refused, unreachable, address issues).
- **Formula**: RTO rate = RTO orders ÷ Shipped orders × 100.
- **Interpretation**: Differs from customer returns after delivery (KB-15). RTO often reflects delivery, address quality or cash-on-delivery refusals.

## 5. Inventory metrics

### Stockout rate
- **Formula**: Stockout rate = Out-of-stock products ÷ Total active products × 100 (or time-weighted: days out of stock ÷ days in period).
- **Example**: 18 out-of-stock of an unknown active catalogue size. The count alone does not give a rate; the number of active listings is needed.
- **Mistake**: Treating the count of out-of-stock items as equally serious across products.

### Inventory turnover
- **Formula**: Inventory turnover = Cost of goods sold ÷ Average inventory value.
- **Example**: COGS ₹6,00,000 per year; average inventory ₹1,50,000 → turnover 4 times a year (about 91 days of inventory).
- **Interpretation**: High turnover can mean efficient stock or too little stock (frequent stockouts). Low turnover can mean overstock or dead stock.

### Sell-through rate
- **Formula**: Sell-through % = Units sold ÷ (Units sold + Units remaining at period end) × 100, or units sold ÷ units received.
- **Example**: Receive 200 units, sell 140 → 70%.
- **Interpretation**: Useful for seasonal and fashion products.

## 6. Profitability metrics

### Gross margin
- **Formula**: Gross margin % = (Selling price − Product cost) ÷ Selling price × 100.
- **Example**: Price ₹500, product cost ₹300 → margin ₹200 = 40%.

### Contribution margin
- **Formula**: Contribution margin per order = Price − product cost − variable costs (marketplace charges, shipping, packaging, returns allowance).
- **Example (assumed costs)**: ₹500 − ₹300 − ₹60 (assumed fees) − ₹40 (assumed shipping) − ₹20 (packaging) = ₹80 → 16%.
- **Interpretation**: What each order contributes toward fixed costs and profit. See KB-06.
- **Mistake**: Using gross margin and ignoring shipping, fees and returns.

### Customer acquisition cost (CAC), where relevant
- **Formula**: CAC = Marketing spend ÷ New customers acquired.
- **Note**: On a marketplace the seller seldom sees customer identity; the nearest practical measure is advertising spend per order (ad cost ÷ ad-attributed orders). Confirm data availability.

## 7. How to read metrics together

- Sales down, orders down, ASP flat → volume problem; investigate stock, visibility, conversion, cancellations, demand.
- Sales flat, orders up, ASP down → discounting or mix shift; check margin.
- Orders flat, cancellation up → net orders fall; check operations.
- Clicks up, orders flat → conversion problem.

## 8. Questions a KAM should ask

- How does your report define "orders": placed, confirmed or delivered?
- Are these numbers for equal-length periods?
- Do you have product-level figures, or only the seller total?

## 9. What not to conclude

- Do not call a metric "good" or "bad" using an invented benchmark.
- Do not infer cause from a single metric change.
- Do not mix percentage points and percent changes.

## 10. Related concepts

Seller health check (KB-03), sales decomposition (KB-04), unit economics (KB-06), stockouts (KB-09), conversion (KB-12), cancellations (KB-14).

## 11. Source notes

General accounting and retail analytics definitions. Specific platform dashboards may define metrics differently; confirm from the platform's reports.
