---
doc_id: "metrics_004"
title: "E-commerce Metrics Glossary"
domain: "metrics"
doc_type: "glossary"
source_type: "general_guidance"
verification_status: "research_based"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - GMV
  - average selling price
  - average order value
  - cancellation rate
  - conversion rate
  - RTO rate
  - inventory turnover
  - metric definitions
applies_to:
  - marketplace_sellers
---

# E-commerce Metrics Glossary

**Reading rules.** Platforms define metrics differently. For every rate below, the denominator and period are stated; always confirm the definition used by the backend tool before quoting a number. All numbers in examples are **illustrative**, not benchmarks. No metric has a universal "healthy" threshold; norms vary by category, price band, season, traffic source and seller maturity. Source type: general guidance [G001].

Availability key: **Available** = current prototype tools return it; **Not available** = needs extra data (see `data_avail_025`).

## Money metrics: GMV, sales, net sales, revenue, profit

### GMV (Gross Merchandise Value)
- **Definition:** total value of goods ordered, usually at selling price, before removing cancellations, returns, discounts funded by the platform, taxes or fees. Definitions vary.
- **Formula:** GMV = sum of (selling price x quantity) over orders placed in the period.
- **Example:** 100 orders at 500 each = 50,000.
- **Increase/decrease:** more or fewer orders, or price change.
- **Related:** cancellation rate, return rate, net sales.
- **Data needed:** order-level values including cancelled and returned orders.
- **Mistakes:** treating GMV as money earned; ignoring that cancelled orders may still be inside GMV.
- **Prototype:** The tool exposes "monthly sales"; its exact definition (gross or net of cancellations) must be confirmed from the tool code.

### Sales (as a seller-facing figure)
Used loosely. State which one you mean: gross ordered value, delivered value or net of returns. If the tool does not say, call it "the sales figure shown in your dashboard".

### Net sales
- **Formula:** Net sales = gross sales - cancellations - returns/refunds - seller-funded discounts (if not already netted).
- **Example:** gross 50,000, cancellations 4,000, returns 3,000 gives 43,000.
- **Data needed:** cancelled and returned value. **Prototype:** Not available separately.

### Revenue (to the seller)
Money the seller actually earns from sales after marketplace fees, commissions, shipping charges and tax treatment, depending on accounting view. Not the same as GMV. Needs payment/settlement data. **Prototype:** Not available.

### Profit, gross margin, contribution margin
- **Gross margin %** = (selling price - product cost) / selling price.
- **Contribution margin per unit** = selling price - product cost - variable costs (marketplace commission, shipping/fulfilment, packaging, payment charges, returns allowance, promotion cost).
- **Example:** price 500, product cost 300, commission and fees 75, packaging 20, shipping 50: gross margin = 40%; contribution = 500 - 300 - 75 - 20 - 50 = 55 (11%).
- **Meaning:** a sales rise with a falling contribution margin can reduce profit.
- **Data needed:** cost price, fee structure, shipping cost. **Prototype:** Not available.
- **Mistake:** confusing gross margin with profit; ignoring returns and cancellations cost.

## Volume and value per order

### Order count
Number of orders (or order items) placed in the period. Confirm whether the tool counts orders or items and whether cancelled orders are included. **Prototype:** Available.

### Average Order Value (AOV)
- **Formula:** AOV = total order value / number of orders (per period).
- **Example:** 54,000 / 120 orders = 450.
- **Meaning:** rises with bundles or higher-priced items; falls with discounting or cheaper mix.
- **Mistake:** equating AOV with ASP. AOV is per order (may hold multiple items); ASP is per unit or item.

### Average Selling Price (ASP)
- **Formula:** ASP = sales value / units (or items) sold. In the prototype, ASP is returned by tools; confirm whether it is sales divided by orders.
- **Example:** 60,000 / 150 units = 400.
- **Meaning:** a fall can mean price cuts, discount usage or a shift toward cheaper products; flat ASP with lower orders points to volume problems.
- **Related:** product mix, discount depth, AOV.
- **Mistake:** assuming ASP fell because prices were cut; mix shift is equally possible.
- **Prototype:** Available.

## Reliability metrics

### Cancellation rate
- **Definition:** share of orders cancelled. **Formula (state denominator):** cancelled orders / total orders placed in the same month.
- **Example:** 18 cancelled of 150 placed = 12%.
- **Meaning of increase:** possible stock mismatch, slow dispatch, buyer-side cancellations or logistics issues. The rate alone does not show who cancelled or why.
- **Data needed:** cancellation reason and initiator per order (seller, buyer, logistics, system); timestamps.
- **Mistake:** assuming all cancellations are the seller's fault.
- **Prototype:** Available (rate only; no reason codes).

### Return rate
- **Formula:** returned units / delivered units over a stated cohort window. Choose delivered units as denominator, not orders placed.
- **Example:** 9 returns of 120 delivered = 7.5%.
- **Data needed:** return reasons, delivery dates. **Prototype:** Not available.

### RTO (Return to Origin) rate
- **Definition:** shipments that could not be delivered and came back to the seller. **Formula:** RTO shipments / shipments handed to courier.
- **Example:** 6 of 100 shipped = 6%.
- **Meaning:** address issues, buyer refusal, logistics failures. Distinct from customer returns after delivery.
- **Prototype:** Not available.

## Inventory metrics

### Inventory turnover
- **Formula:** cost of goods sold in the period / average inventory value in the period.
- **Example:** COGS 90,000; average inventory 30,000 gives 3 turns in the period.
- **Meaning:** low turnover suggests overstock or slow sellers; very high may signal stockouts.
- **Data needed:** cost and inventory value. **Prototype:** Not available.

### Stockout rate
- **Formula:** products out of stock / total active products (state the date or period; alternatively days out of stock / days active).
- **Example:** 6 of 40 active products out of stock = 15%.
- **Prototype:** Out-of-stock **count** is available; the active-product total is needed for a rate.
- **Mistake:** treating all stockouts as equal; weigh by past demand.

### Inventory cover (days of cover)
- **Formula:** units on hand / average daily units sold.
- **Example:** 120 units / 6 per day = 20 days.
- **Needs:** current stock and recent daily sales per product. **Prototype:** Not available (historical orders for stocked-out products are available, not current stock).

### Sell-through rate
- **Formula:** units sold in a period / (units sold + units remaining at end of period) (state which base is used).
- **Example:** 80 sold, 20 remaining gives 80%.
- **Prototype:** Not available.

## Funnel metrics

### Impressions
Times a product listing was shown to shoppers in search, category or recommendation. **Prototype:** Not available.

### Clicks
Times shoppers opened the product page from impressions. **Prototype:** Not available.

### Click-through rate (CTR)
- **Formula:** clicks / impressions in the same period and placement.
- **Example:** 30 clicks / 1,500 impressions = 2%.
- **Meaning:** low CTR may reflect weak title, image, price or relevance.
- **Mistake:** comparing CTR across placements or categories.

### Conversion rate
- **Formula (state it):** orders / product page visits (visit-based) or orders / clicks. Do not mix.
- **Example:** 6 orders / 200 visits = 3%.
- **Meaning:** low conversion may reflect price, content, reviews, stock or delivery promise.
- **Prototype:** Not available.

## Customer metrics

### Customer Acquisition Cost (CAC)
- **Formula:** marketing and promotion spend / new customers acquired.
- **Example:** 5,000 spend / 50 new customers = 100.
- **Prototype:** Not available. Marketplace sellers rarely see customer identity, so use cost per order as a proxy.

### Repeat purchase rate
- **Formula:** customers with 2 or more orders in a period / customers with 1 or more orders. Needs customer-level data. **Prototype:** Not available.

### Ratings and review metrics
- **Average rating:** mean of star ratings. **Rating count** and **negative-review share** (share of 1 and 2 star reviews) also matter.
- **Mistake:** relying on average without count; 4.6 from 5 ratings is weaker evidence than 4.2 from 500.
- **Prototype:** Not available.

## Cross-metric cautions
- Sales = orders x ASP (see `diagnostic_005`). Always decompose before concluding.
- Compare same-length periods and note seasonality.
- When a metric is unavailable, see `data_avail_025` and ask the seller or request the report.
