# Snapdeal Seller Assistant

Your always-available virtual Key Account Manager — one who talks, listens,
knows your numbers, and helps you grow your business.

Load your seller ID and simply talk to **Sarika**, your AI account manager.
She reviews your sales, spots problems, explains what's going on in simple
words, and helps you plan the next step — in Hindi, English or Hinglish,
whichever you prefer.

## What you can do

### 🎙️ Talk to your account manager
- Start a voice call with one tap — just speak naturally, she listens and
  replies in a warm, human voice.
- A live transcript runs alongside the call, so you can read along.
- She replies in your language — Hindi (Devanagari), English, or Hinglish.
- End the call the way you naturally would — "बस आज के लिए इतना ही" or
  "that's all for today" — and she wraps up politely with a quick recap.
- If anything hiccups mid-call, she recovers gracefully instead of going
  silent.

### 📊 See your business at a glance
- Monthly sales, orders and average selling price, each with its change
  versus last month.
- Ask about anything — cancellation rate, out-of-stock count, pricing,
  bestsellers — and she answers from your actual numbers. No guessing.

### 🔍 Understand why orders were cancelled
- Cancellations broken down by reason — stock issues, fulfilment delays,
  customer cancellations and seller cancellations.
- Product-level view: which products were hit and how many orders each
  one lost.
- Kept clearly separate from the monthly cancellation rate, so the two
  numbers are never mixed up.

### 🧠 Proactive, practical advice
- When a call starts, she has already reviewed your numbers and opens with
  the most important observation — you don't have to repeat your story.
- Measured facts come first; possible explanations are clearly labelled as
  possibilities, never presented as conclusions.
- Recommendations are short and doable — 2-3 practical next steps, not
  generic lectures.

### 📦 Inventory awareness
- See which products are out of stock, including the ones that went out of
  stock since last month.
- Stockouts can be connected to falling sales and rising cancellations
  during the conversation.

### ✅ Reminders and follow-up actions
- Agree on a follow-up in the conversation — she confirms the details and
  the exact date with you before saving anything.
- Every action gets an ID and a deadline, and can be tracked as Pending,
  Completed or Cancelled.

### 💾 Every call is remembered
- A full transcript of every conversation, saved automatically.
- A call summary after each call: what was discussed, the key numbers, and
  the follow-ups you agreed to.
- Start a new session anytime — past conversations stay saved and easy to
  revisit.

### 🔑 Use your own API key
- The assistant runs on Sarvam AI. A demo key is already included, or you
  can add your own from Settings.
- Your saved key always takes priority over the default one.
- A saved key is never displayed again — only a masked status is shown —
  and you can clear it anytime to go back to the default.

## Try it with a demo seller

| Seller ID | Seller | Business |
|---|---|---|
| SD-48213 | Rajesh | Rajesh Garments — women's ethnic wear |
| SD-52077 | Meena | Meena Home Decor |
| SD-63190 | Arjun | Arjun Mobile Accessories |
| SD-12345 | Srijan | Srijan Apparel Studio |

Each seller tells a different story — one is fighting stockouts and rising
cancellations, one is running healthy, one is struggling with fulfilment
delays. Try them all to see how the advice changes.

## Getting started

```bash
uv sync
uv run uvicorn seller_dashboard.api:app --reload
```

Then open `src/frontend/index.html` in your browser, enter a seller ID
(for example `SD-48213`), press **Load**, and tap the mic to start talking.

> **Note:** the seller numbers in this demo are illustrative mock data and
> are clearly marked as assumed — perfect for trying the assistant, but
> not real sales records.
