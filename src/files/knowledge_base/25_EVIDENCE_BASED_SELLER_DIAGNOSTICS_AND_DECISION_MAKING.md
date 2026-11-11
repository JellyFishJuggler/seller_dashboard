---
doc_id: "KB-25"
title: "Evidence-Based Seller Diagnostics and Decision Making"
domain: "kam_consultation"
doc_type: "decision_framework"
source_type: "general_and_referenced"
verification_status: "general_knowledge"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - evidence
  - hypothesis
  - correlation versus causation
  - confidence levels
  - uncertainty
  - missing data
  - safe conclusions
  - escalation
applies_to:
  - general_marketplace
---

# Evidence-Based Seller Diagnostics and Decision Making

This document teaches how to reason responsibly from incomplete business data: separate observations from interpretations, treat explanations as hypotheses until tested, state confidence, ask for the right extra data, decide when not to recommend and when to escalate. The assignment sample seller is used as an illustrative case; its figures are assignment data, not real Snapdeal data.

## 1. Observation versus interpretation

- **Observation**: a fact in the data. "Orders fell from 400 to 270." "ASP stayed ₹500." "Out-of-stock products rose from 5 to 18." "Cancellation rate rose from 8% to 14%."
- **Interpretation**: a meaning or cause attached to facts. "Stockouts caused the decline."

State observations plainly. Label interpretations as such and match the wording to the strength of evidence.

## 2. Evidence versus hypothesis

A hypothesis is a possible explanation. It becomes supported when evidence points to it and rival explanations are less consistent. Example hypotheses for the sample seller: unavailable bestsellers; seller-side cancellations from stock mismatch; lower visibility; lower conversion; demand or seasonality; promotion ended.

For each hypothesis, ask: what would we see if it were true? What would we see if it were false? What data separates it from others?

## 3. Correlation versus causation

Two things moving together do not prove one caused the other. Stockouts rose and orders fell at the same time (correlation). A third factor might cause both (for example a supplier problem, or a demand dip that left stock unsold elsewhere), or the order of events might differ. Causation needs: timing (stockout before sales loss), product-level match (lost orders come from the out-of-stock products), and absence of better explanations.

## 4. Metric limitations

- Seller-level totals hide product-level effects.
- Percent changes hide scale.
- ASP unchanged does not prove no price change at product level.
- Cancellation rate depends on the denominator definition.
- Stockout count does not show which products or for how long.
- Sales fall from period to period can include noise, calendar differences and seasonality.

## 5. Missing data

List what is missing before concluding: product-level orders; stockout dates; cancellation reasons; impressions and clicks; competitor price; promotion history; prior-year same period; cost and fee data. Say plainly: "Yeh data abhi nahi hai, isliye yeh cause pakka nahi hai."

## 6. Confidence levels

Use plain labels:
- **High**: directly observed or arithmetically certain. Example: since ASP is unchanged, the entire sales change comes from order volume.
- **Medium**: consistent with several pieces of evidence, but untested. Example: stockouts are a likely contributor.
- **Low**: plausible but with little supporting evidence. Example: a search visibility drop.
- **Unknown**: no data.

## 7. Safe versus unsafe conclusions (sample seller)

Observed: sales down, ASP unchanged, orders down, out-of-stock count up, cancellation rate up.

**Safe interpretations**
- The sales decline is explained by lower order volume, not price (arithmetic: −130 orders × ₹500 = −₹65,000 equals the total change).
- Higher stockout count and cancellation rate are potential contributing issues that deserve investigation.
- Product-level data is needed to see if the out-of-stock items were demand-heavy.

**Unsafe interpretations**
- "Stockouts definitely caused the whole sales decline."
- "The seller lost exactly ₹X because of stockouts."
- "Search ranking dropped."
- "Profit fell by Y%." (no cost data)
- "The seller caused the cancellations." (reasons unknown)
- "Price is too high." (ASP unchanged; no competitor data)

## 8. How to validate a hypothesis

1. State the hypothesis precisely.
2. Predict what data would confirm or refute it.
3. Get that data (product-level orders, stock history, cancellation reasons, impressions).
4. Check timing, magnitude and concentration.
5. Rule out rivals.
6. Update confidence.

Example: Hypothesis "newly out-of-stock bestsellers explain most of the order loss." Test: list the products that lost the most orders; compare with the list of newly out-of-stock products. If most of the 130 lost orders sit in these products, confidence rises to high-medium. If the lost orders are spread across in-stock products, the hypothesis weakens and visibility, conversion or demand deserve attention.

## 9. When to ask the seller for more information

Ask when one piece of information would change the recommendation. Ask for the most diagnostic item first; keep to one question at a time (KB-21). Do not ask for information already in tools.

## 10. When to avoid making a recommendation

Avoid recommending when:
- The data cannot distinguish between rival explanations and the recommended action would be costly or irreversible (for example a deep price cut).
- A recommendation would need figures you do not have (restock quantity, discount depth).
- The issue is platform-policy dependent and unverified (fees, penalties).
Instead, recommend an information-gathering action.

## 11. When to escalate to platform support

- Patterns that appear platform-side: unexplained cancellations or order drops across many products with no seller-side cause; payment or settlement discrepancies; unexplained account or listing restrictions.
- Questions on fees, penalties, ranking or policy that cannot be verified from official documents (KB-24).
- Technical errors in the panel or stock sync.
Escalate with evidence: order IDs, dates, screenshots, metric changes.

## 12. Communicating uncertainty without being unhelpful

Be definite about what is known, honest about what is not, and clear about the next step.

Template: "Aapke orders 400 se 270 hue (pakka). Price nahi badla, isliye gir kar order ki sankhya hi hai (pakka). Stockout 5 se 18 hue, yeh ek bada possible reason hai (abhi confirm nahi). Main yeh confirm karne ke liye check karna chahta hoon ki kaun se top products out of stock hain. Uske baad hum restock plan banayenge."

Tips: lead with what is certain; use "likely", "possible", "not yet confirmed"; always add a concrete next step; avoid long hedging.

## 13. Examples of evidence handling

**Example 1 (strong evidence):** The seller's top 3 products dropped from 220 orders to 90, all three out of stock for 12 days. Statement: "Stockout is very likely the main driver of the decline for these products." Still not a precise rupee loss claim.

**Example 2 (mixed evidence):** Stockouts in low-selling products and orders fell across all products. Statement: "These stockouts are unlikely to explain the broad drop; I'd look at visibility, conversion, season and promotions."

**Example 3 (no data):** "Is my ranking down?" Statement: "I can't see ranking data. If you can see views per product, share them; otherwise we can ask support."

## 14. Questions a KAM should ask

- What data do you have that I don't?
- Did anything change at the start of the decline?
- Which products drove most of the fall?

## 15. What not to conclude

- No causation from co-movement alone.
- No numeric loss estimates without product-level history.
- No invented benchmarks.
- No platform-policy claims without a source.

## 16. Related concepts

Health diagnostics (KB-03), sales analysis (KB-04), stockouts (KB-09), cancellations (KB-14), action planning (KB-23), platform knowledge (KB-24).
