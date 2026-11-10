---
doc_id: "sd_limits_024"
title: "Snapdeal Policy Limitations and Escalation"
domain: "snapdeal_policy"
doc_type: "limitations_reference"
source_type: "internal"
verification_status: "maintained"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - policy uncertainty
  - escalation to Snapdeal support
  - unverified rules
  - do not guess
  - penalties
  - seller panel verification
applies_to:
  - ai_assistant
---

# Snapdeal Policy Limitations and Escalation

## Purpose
Defines where the assistant must not guess and how to say so. Prefer honest limits over invented answers.

## Items that require current Seller Panel verification
- **Penalty amounts** for marking orders out of stock, SLA breach or cancellations. The API documentation says a penalty may apply [S003] but gives no rates; third-party slide decks were not relied on [S015].
- **Commissions, fees, payment cycles and settlement timelines.** Not verified.
- **Listing image specs and rejection rules.** Source is historical [S007, S008].
- **Automated pricing availability and rules.** Source is from 2019 [S010].
- **Prohibited-seller-activity consequences.** Source is version 1.2 from 2017 [S009].
- **Seller ads and promotion programs.** Only endpoint names seen [S002].
- **Return and refund terms for specific categories.**

## Features that may vary by seller account
Fulfilment mode (Dropship, Oneship, Oneship Plus, SD+, Vendor Self) depends on product configuration [S003]. API access, ads, automated pricing and category permissions may differ. Always ask which mode or feature the seller uses.

## Category-specific restrictions
Brand authorization, banned items, combo allowance, image style and mandatory attributes vary by category [S007, S008]. Refer to the category guideline.

## Not documented in sources (do not claim)
Snapdeal's search ranking logic; impressions, clicks or conversion metrics availability; seller score or quality ratings; customer review policies beyond [S009] items; payout schedules; free-shipping rules.

## Questions to route to Snapdeal support or seller help
- Account block, listing takedown, penalty disputes, payment discrepancies.
- Brand authorization or document requirements.
- Technical failures in panel or API.
- Anything involving a specific order's dispute.

## Legal and compliance matters
Questions about tax, GST, legal metrology labels, consumer-rule obligations, or contract disputes need official guidance or a professional. Secondary summaries of consumer rules were reviewed [S011, S012] but official text was not retrieved. Say so.

## How to express uncertainty
Use short, calm statements:
- "I can explain the general process, but this particular policy should be confirmed through your current Snapdeal Seller Panel."
- "The document I have is from 2017, so I would not rely on it for the exact penalty. Please check your panel or contact seller support."
- "I do not have access to Snapdeal's ranking rules, so I will not guess. What I can do is look at stock and listing quality."
- Hinglish: "Yeh policy ka exact rule mere paas confirmed nahi hai. Aap apne Seller Panel mein ya Snapdeal support se confirm kar lijiye."

## Escalation steps for the assistant
1. State the limit plainly.
2. Offer what the assistant can do within its data.
3. Suggest the right channel (Seller Panel help, query raise, support).
4. Log a follow-up in the action summary (`actionplan_016`).

## Do not
Quote percentages, deadlines or fees from memory. Imply the assistant can contact Snapdeal for the seller (prototype cannot).
