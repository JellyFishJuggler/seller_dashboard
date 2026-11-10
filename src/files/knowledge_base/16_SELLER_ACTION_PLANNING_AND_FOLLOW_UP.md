---
doc_id: "actionplan_016"
title: "Seller Action Planning and Follow-up"
domain: "action_planning"
doc_type: "business_playbook"
source_type: "general_guidance"
verification_status: "research_based"
last_verified: "2026-11-11"
version: "1.0"
keywords:
  - action plan
  - impact effort prioritization
  - follow up schedule
  - seller agreement
  - escalation
  - conversation summary
applies_to:
  - ai_assistant
---

# Seller Action Planning and Follow-up

## Overview
After diagnosis, the assistant proposes at most 2 to 3 immediate actions, gets agreement and records follow-ups. General guidance [G001].

## Prioritizing issues
Score each candidate on:
- **Impact:** size of likely business effect.
- **Urgency:** does it worsen daily (stockouts, rising cancellations)?
- **Effort:** seller time and cost.
- **Evidence:** how well data supports the cause.
Pick high impact, high urgency, low to medium effort, strong evidence.

## Impact versus effort quick guide
| | Low effort | High effort |
|---|---|---|
| High impact | Do now | Plan and schedule |
| Low impact | Do if time | Skip |

## Short term versus long term
- Short term (this week): restock top product, reconcile stock, correct an obvious listing error.
- Long term (this quarter): assortment, catalogue upgrade, ratings improvement.
Do not mix more than 3 short-term actions.

## Recommendation template
Each recommendation should state:
- **Problem identified**
- **Supporting evidence** (from tools or the seller)
- **Recommended action**
- **Why it matters**
- **Expected outcome** (qualitative; no guaranteed numbers)
- **Required information or resources**
- **Who is responsible** (seller or assistant)
- **Follow-up date**

**Illustrative example:** Problem: top-selling kurti out of stock. Evidence: tool shows high past orders for this product; seller confirms supplier restock takes about one week. Action: place restock order for that product first. Why: likely largest lost demand. Outcome: availability returns; we will watch orders next week. Resources: supplier confirmation. Owner: seller. Follow-up: review in 7 days.

## Seller agreement
Ask for explicit consent per action: "Do you agree to do X by Y?" Record agreed, declined and undecided items separately. Do not treat silence as agreement.

## Assigning responsibilities
Assistant: analyze data, remind, check outcomes. Seller: inventory, pricing, supplier, listing edits. Snapdeal support: platform issues.

## Follow-up schedule
Set the next check based on urgency: a few days for stockouts or cancellations; one to two weeks for listing changes. Define what will be checked (for example, orders and cancellation rate for the affected period).

## Tracking outcomes
Compare the same metrics before and after for the agreed window; note external factors (festival, stockout). Avoid claiming credit for changes you cannot attribute.

## Escalation
Escalate to Snapdeal support or the Seller Panel help when the issue involves payments, penalties, account blocks, policy interpretation or technical failures (`sd_limits_024`).

## Conversation summary pattern
1. What we found (one or two facts).
2. What you agreed to do and by when.
3. What happens next (follow-up time).
Keep it under 4 sentences for voice.

## Limits
No financial outcome promises. No invented deadlines for Snapdeal processes.
