# Seller Assistant RAG Evaluation

Generated: 2026-11-11T03:01+05:30

## Method and limits

Fifteen Hindi seller questions were sent through the production Chroma retriever. A case passes retrieval/context support when at least one expected knowledge file is in top-4 and at least half (minimum two) of its expected concepts appear in those retrieved chunks. Similarity scores are cosine similarity. The guardrail column checks prompt configuration only; this offline suite does not call Sarvam or claim that a generated answer was empirically fact-checked.

Seller metrics are not indexed in Chroma. They are loaded by existing Python tools and added to the agent context separately. Retrieved knowledge is general guidance; source examples remain illustrative.

## Repository audit

- Knowledge-base path resolves to `C:\Users\Srijan Gupta\Downloads\Developement\seller_dashboard\src\files\knowledge_base` in this checkout; 25 non-empty Markdown files produce 227 chunks (1,000 characters, 200 overlap).
- Persisted Chroma collection `seller_knowledge_base_tfidf` contains 227 chunks. Index freshness by stable source/content IDs: PASS (0 missing, 0 stale).
- Exact duplicate chunk texts: 0. Chunks missing filename metadata: 0.
- Actual embedding implementation: scikit-learn TF-IDF with English stop-word removal and 1–2 grams, stored as Chroma cosine vectors. Sentence Transformers / `all-MiniLM-L6-v2` are not used or declared in `pyproject.toml`.
- Retrieval was disconnected from neither the prompt nor graph: `generate_formatted_prompt` retrieves, includes source-labelled chunks in a `SystemMessage`, and `model.invoke` receives it. The system/RAG prompt says to use relevant chunks as general guidance. A local mock-LLM integration test verifies delivery, but only live model evaluation can prove generated answers actually follow them.
- Audit issue: English TF-IDF vocabulary returned zero-similarity arbitrary chunks for Devanagari queries because threshold was zero. Hindi term expansion and a 0.05 similarity floor now target that failure. Repeated same-file chunks were also observed, so final results cap at two chunks per file and backfill from a limited candidate window; final context remains top-4.

## Results

| # | Hindi evaluation question | Top-4 retrieved sources (similarity) | Expected concepts found | Context support | Unsupported-assumption guardrail |
|---:|---|---|---:|---|---|
| 1 | ऑर्डर बढ़े हैं, लेकिन बिक्री और औसत बिक्री मूल्य घट रहे हैं। इसे कैसे समझूँ? | 02_ECOMMERCE_METRICS_AND_FORMULAS.md (0.18), 04_SALES_AND_DEMAND_ANALYSIS.md (0.18), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.17), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.15) | 3/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 2 | मेरे प्रोडक्ट का औसत बिक्री मूल्य लगातार गिर रहा है। कौन से संकेत देखूँ? | 02_ECOMMERCE_METRICS_AND_FORMULAS.md (0.17), 04_SALES_AND_DEMAND_ANALYSIS.md (0.16), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.15), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.15) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 3 | क्या बिक्री बढ़ाने के लिए मुझे छूट देनी चाहिए या कीमत बदलनी चाहिए? | 05_PRICING_AND_PRICE_POSITIONING.md (0.23), 05_PRICING_AND_PRICE_POSITIONING.md (0.09), 07_PROMOTIONS_AND_DISCOUNT_STRATEGY.md (0.07), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.07) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 4 | कुछ प्रोडक्ट आउट ऑफ स्टॉक हैं। पहले किन्हें दोबारा स्टॉक करना चाहिए? | 09_STOCKOUT_ANALYSIS_AND_RECOVERY.md (0.10), 14_ORDER_CANCELLATION_ROOT_CAUSE_ANALYSIS.md (0.09), 09_STOCKOUT_ANALYSIS_AND_RECOVERY.md (0.08), 18_APPAREL_SELLER_BUSINESS_PLAYBOOK.md (0.08) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 5 | इन्वेंटरी दोबारा मंगाने का समय और मात्रा कैसे तय करूँ? | 08_INVENTORY_MANAGEMENT_AND_DEMAND_FORECASTING.md (0.32), 08_INVENTORY_MANAGEMENT_AND_DEMAND_FORECASTING.md (0.15), 09_STOCKOUT_ANALYSIS_AND_RECOVERY.md (0.10), 09_STOCKOUT_ANALYSIS_AND_RECOVERY.md (0.09) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 6 | सर्च में मेरी product listing कम दिखाई देती है। visibility कैसे सुधारूँ? | 10_CATALOGUE_AND_PRODUCT_LISTING_OPTIMIZATION.md (0.15), 11_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md (0.14), 11_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md (0.12), 03_SELLER_BUSINESS_HEALTH_DIAGNOSTICS.md (0.10) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 7 | लोग product देखते हैं, लेकिन खरीदते नहीं। conversion सुधारने के लिए क्या जाँचूँ? | 12_CONVERSION_AND_CUSTOMER_EXPERIENCE.md (0.12), 02_ECOMMERCE_METRICS_AND_FORMULAS.md (0.12), 12_CONVERSION_AND_CUSTOMER_EXPERIENCE.md (0.11), 05_PRICING_AND_PRICE_POSITIONING.md (0.10) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 8 | कैंसलेशन रेट बढ़ा है। कारण पता करने के लिए क्या देखना चाहिए? | 14_ORDER_CANCELLATION_ROOT_CAUSE_ANALYSIS.md (0.11), 23_BUSINESS_ACTION_PLANNING_AND_PRIORITISATION.md (0.11), 02_ECOMMERCE_METRICS_AND_FORMULAS.md (0.09), 13_ORDER_MANAGEMENT_AND_FULFILMENT.md (0.09) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 9 | रिटर्न और RTO बढ़ रहे हैं। इन्हें कम करने के लिए क्या जाँचूँ? | 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.24), 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.11), 02_ECOMMERCE_METRICS_AND_FORMULAS.md (0.08), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.08) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 10 | मेरे product title, फोटो और attributes बेहतर कैसे करूँ? | 11_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md (0.13), 10_CATALOGUE_AND_PRODUCT_LISTING_OPTIMIZATION.md (0.13), 11_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md (0.12), 10_CATALOGUE_AND_PRODUCT_LISTING_OPTIMIZATION.md (0.11) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 11 | सही profitability और margin निकालने के लिए कौन-कौन सी लागत चाहिए? | 02_ECOMMERCE_METRICS_AND_FORMULAS.md (0.23), 06_PROFITABILITY_AND_UNIT_ECONOMICS.md (0.15), 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.12), 06_PROFITABILITY_AND_UNIT_ECONOMICS.md (0.12) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 12 | कपड़ों के seller के लिए size chart, fit और returns कैसे सुधारें? | 18_APPAREL_SELLER_BUSINESS_PLAYBOOK.md (0.25), 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.19), 18_APPAREL_SELLER_BUSINESS_PLAYBOOK.md (0.14), 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.12) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 13 | होम डेकोर के प्रोडक्ट की listing और बिक्री कैसे बेहतर करूँ? | 19_HOME_DECOR_SELLER_BUSINESS_PLAYBOOK.md (0.29), 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.20), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.10), 19_HOME_DECOR_SELLER_BUSINESS_PLAYBOOK.md (0.09) | 4/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 14 | मोबाइल accessories में compatibility और listing details कैसे बताऊँ? | 15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md (0.17), 20_MOBILE_ACCESSORIES_SELLER_BUSINESS_PLAYBOOK.md (0.13), 20_MOBILE_ACCESSORIES_SELLER_BUSINESS_PLAYBOOK.md (0.13), 21_SELLER_DISCOVERY_AND_BUSINESS_DIAGNOSTIC_QUESTIONS.md (0.12) | 3/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |
| 15 | मेरे पास कई काम हैं। किस business action को पहले प्राथमिकता दूँ? | 23_BUSINESS_ACTION_PLANNING_AND_PRIORITISATION.md (0.16), 23_BUSINESS_ACTION_PLANNING_AND_PRIORITISATION.md (0.16), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.06), 01_MARKETPLACE_SELLER_BUSINESS_FUNDAMENTALS.md (0.05) | 3/4 | PASS: संदर्भ में अपेक्षित guidance है | Prompt guardrails configured |

**Summary: 15/15 cases passed.** Unrelated-query rejection: PASS (0 chunks returned).

## Interpretation

A passing context-support result means the retrieved text contains the expected business concepts. It does not prove that the LLM follows the context in every answer. Live response grounding, natural Hindi quality, and voice delivery still require manual conversation testing with the Sarvam service.
