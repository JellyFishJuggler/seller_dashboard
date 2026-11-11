"""Offline retrieval and grounding-policy evaluation for the seller RAG flow.

Run from the project root with the application environment:
    python rag_quality_eval.py

This checks Chroma retrieval and whether the retrieved passages contain the
expected guidance. It does not call Sarvam or claim to score generated wording.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from seller_dashboard.bot import SYSTEM_PROMPT, prompt as rag_prompt
from seller_dashboard.rag import get_retriever, load_md_files, split_doc


CASES = [
    {
        "question": "ऑर्डर बढ़े हैं, लेकिन बिक्री और औसत बिक्री मूल्य घट रहे हैं। इसे कैसे समझूँ?",
        "sources": {"04_SALES_AND_DEMAND_ANALYSIS.md", "02_ECOMMERCE_METRICS_AND_FORMULAS.md", "03_SELLER_BUSINESS_HEALTH_DIAGNOSTICS.md"},
        "concepts": [("sales", "revenue"), ("orders", "order volume"), ("average selling price", "ASP"), ("product mix", "price mix")],
        "focus": "sales, orders, ASP और product mix को साथ देखकर संभावित व्याख्या; कारण निश्चित न मानें",
    },
    {
        "question": "मेरे प्रोडक्ट का औसत बिक्री मूल्य लगातार गिर रहा है। कौन से संकेत देखूँ?",
        "sources": {"02_ECOMMERCE_METRICS_AND_FORMULAS.md", "04_SALES_AND_DEMAND_ANALYSIS.md", "05_PRICING_AND_PRICE_POSITIONING.md"},
        "concepts": [("average selling price", "ASP"), ("orders", "order volume"), ("product mix", "mix"), ("price", "pricing")],
        "focus": "ASP की परिभाषा, orders और product mix की जाँच; ASP को profit न कहें",
    },
    {
        "question": "क्या बिक्री बढ़ाने के लिए मुझे छूट देनी चाहिए या कीमत बदलनी चाहिए?",
        "sources": {"05_PRICING_AND_PRICE_POSITIONING.md", "07_PROMOTIONS_AND_DISCOUNT_STRATEGY.md", "06_PROFITABILITY_AND_UNIT_ECONOMICS.md"},
        "concepts": [("discount", "promotion"), ("price", "pricing"), ("cost", "margin"), ("test", "measure")],
        "focus": "छूट से पहले मूल्य, लागत और परिणामों का मूल्यांकन; बिना margin डेटा कीमत न सुझाएँ",
    },
    {
        "question": "कुछ प्रोडक्ट आउट ऑफ स्टॉक हैं। पहले किन्हें दोबारा स्टॉक करना चाहिए?",
        "sources": {"09_STOCKOUT_ANALYSIS_AND_RECOVERY.md", "08_INVENTORY_MANAGEMENT_AND_DEMAND_FORECASTING.md", "23_BUSINESS_ACTION_PLANNING_AND_PRIORITISATION.md"},
        "concepts": [("stockout", "out of stock"), ("historical orders", "orders"), ("restock", "replenishment"), ("priority", "priorit")],
        "focus": "उपलब्ध product-level historical orders से क्रम तय करना; lost sales का दावा न करें",
    },
    {
        "question": "इन्वेंटरी दोबारा मंगाने का समय और मात्रा कैसे तय करूँ?",
        "sources": {"08_INVENTORY_MANAGEMENT_AND_DEMAND_FORECASTING.md", "09_STOCKOUT_ANALYSIS_AND_RECOVERY.md"},
        "concepts": [("inventory", "stock"), ("replenishment", "restock"), ("lead time", "supplier"), ("demand", "orders")],
        "focus": "lead time और demand के आधार पर replenishment; मात्रा डेटा के बिना न गढ़ें",
    },
    {
        "question": "सर्च में मेरी product listing कम दिखाई देती है। visibility कैसे सुधारूँ?",
        "sources": {"11_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md", "10_CATALOGUE_AND_PRODUCT_LISTING_OPTIMIZATION.md"},
        "concepts": [("search", "discoverability"), ("visibility", "impressions"), ("listing", "catalogue"), ("title", "attributes")],
        "focus": "खोज में discoverability और listing सुधार; CTR या ranking न गढ़ें",
    },
    {
        "question": "लोग product देखते हैं, लेकिन खरीदते नहीं। conversion सुधारने के लिए क्या जाँचूँ?",
        "sources": {"12_CONVERSION_AND_CUSTOMER_EXPERIENCE.md", "02_ECOMMERCE_METRICS_AND_FORMULAS.md"},
        "concepts": [("conversion rate", "conversion"), ("product page visits", "visits"), ("orders", "purchase"), ("trust", "delivery")],
        "focus": "conversion funnel और आवश्यक visit/order डेटा; उपलब्ध न होने पर स्पष्ट सीमा बताएँ",
    },
    {
        "question": "कैंसलेशन रेट बढ़ा है। कारण पता करने के लिए क्या देखना चाहिए?",
        "sources": {"14_ORDER_CANCELLATION_ROOT_CAUSE_ANALYSIS.md", "13_ORDER_MANAGEMENT_AND_FULFILMENT.md", "25_EVIDENCE_BASED_SELLER_DIAGNOSTICS_AND_DECISION_MAKING.md"},
        "concepts": [("cancellation", "cancelled"), ("root cause", "cause"), ("fulfillment", "dispatch"), ("seller", "buyer")],
        "focus": "कारण जाँचने के लिए अतिरिक्त प्रमाण; initiator या वजह न मानें",
    },
    {
        "question": "रिटर्न और RTO बढ़ रहे हैं। इन्हें कम करने के लिए क्या जाँचूँ?",
        "sources": {"15_RETURNS_RTO_AND_REFUND_MANAGEMENT.md", "14_ORDER_CANCELLATION_ROOT_CAUSE_ANALYSIS.md"},
        "concepts": [("returns", "return"), ("RTO", "return to origin"), ("refund", "reverse logistics"), ("reason", "cause")],
        "focus": "return और RTO को अलग-अलग समझना; उपलब्ध न होने पर कारण न गढ़ना",
    },
    {
        "question": "मेरे product title, फोटो और attributes बेहतर कैसे करूँ?",
        "sources": {"10_CATALOGUE_AND_PRODUCT_LISTING_OPTIMIZATION.md", "11_SEARCH_VISIBILITY_AND_PRODUCT_DISCOVERABILITY.md"},
        "concepts": [("title", "product name"), ("images", "photography"), ("attributes", "catalogue"), ("accurate", "listing")],
        "focus": "सटीक और पूरी listing content; असत्य product claims नहीं",
    },
    {
        "question": "सही profitability और margin निकालने के लिए कौन-कौन सी लागत चाहिए?",
        "sources": {"06_PROFITABILITY_AND_UNIT_ECONOMICS.md", "02_ECOMMERCE_METRICS_AND_FORMULAS.md"},
        "concepts": [("product cost", "cost"), ("fees", "commission"), ("contribution margin", "gross margin"), ("shipping", "packaging")],
        "focus": "unit economics inputs; केवल ASP से profit या margin न निकालना",
    },
    {
        "question": "कपड़ों के seller के लिए size chart, fit और returns कैसे सुधारें?",
        "sources": {"18_APPAREL_SELLER_BUSINESS_PLAYBOOK.md"},
        "concepts": [("size chart", "size"), ("fit", "fitment"), ("returns", "return"), ("variants", "colour")],
        "focus": "apparel-specific size, fit और variant guidance",
    },
    {
        "question": "होम डेकोर के प्रोडक्ट की listing और बिक्री कैसे बेहतर करूँ?",
        "sources": {"19_HOME_DECOR_SELLER_BUSINESS_PLAYBOOK.md"},
        "concepts": [("home decor", "decor"), ("photography", "images"), ("packaging", "fragile"), ("listing", "merchandising")],
        "focus": "home decor-specific merchandising, content और handling",
    },
    {
        "question": "मोबाइल accessories में compatibility और listing details कैसे बताऊँ?",
        "sources": {"20_MOBILE_ACCESSORIES_SELLER_BUSINESS_PLAYBOOK.md"},
        "concepts": [("compatibility", "compatible"), ("connector", "cable"), ("specifications", "wattage"), ("listing", "product detail")],
        "focus": "mobile accessory-specific compatibility और factual specifications",
    },
    {
        "question": "मेरे पास कई काम हैं। किस business action को पहले प्राथमिकता दूँ?",
        "sources": {"23_BUSINESS_ACTION_PLANNING_AND_PRIORITISATION.md", "03_SELLER_BUSINESS_HEALTH_DIAGNOSTICS.md"},
        "concepts": [("priorit", "priority"), ("impact", "business impact"), ("urgency", "urgent"), ("effort", "ease")],
        "focus": "impact, urgency, effort और उपलब्ध प्रमाण से क्रम तय करना",
    },
]


def run_evaluation() -> str:
    retriever = get_retriever()
    current_chunks = split_doc(load_md_files())
    expected_ids = {
        retriever.vector_store._stable_id(chunk, index)
        for index, chunk in enumerate(current_chunks)
    }
    indexed = retriever.vector_store.collection.get(include=["documents", "metadatas"])
    indexed_ids = set(indexed.get("ids", []))
    indexed_texts = indexed.get("documents", []) or []
    metadata_missing = sum(
        not (metadata or {}).get("filename")
        for metadata in (indexed.get("metadatas", []) or [])
    )
    exact_duplicates = len(indexed_texts) - len(set(indexed_texts))
    index_fresh = expected_ids == indexed_ids
    prompt_text = str(rag_prompt)
    safeguards = all(
        phrase in SYSTEM_PROMPT
        for phrase in (
            "Use Python tool results for all seller-specific metrics",
            "ASP is average selling price, not profit",
            "Do not invent",
        )
    ) and "illustrative only" in prompt_text

    rows = []
    passed = 0
    for index, case in enumerate(CASES, start=1):
        docs = retriever.retrieve(case["question"], k=4)
        matching = [
            doc for doc in docs
            if doc.get("metadata", {}).get("filename") in case["sources"]
        ]
        evidence = "\n".join(doc["content"].lower() for doc in matching)
        covered = [
            any(term.lower() in evidence for term in group)
            for group in case["concepts"]
        ]
        useful = bool(matching) and sum(covered) >= max(2, (len(covered) + 1) // 2)
        case_pass = useful and safeguards
        passed += int(case_pass)
        sources = ", ".join(
            f"{doc.get('metadata', {}).get('filename', '?')} ({doc.get('similarity_score', 0):.2f})"
            for doc in docs
        ) or "कोई chunk threshold तक नहीं पहुँचा"
        coverage = f"{sum(covered)}/{len(covered)}"
        support = "PASS: संदर्भ में अपेक्षित guidance है" if useful else "FAIL: relevant/supporting guidance अधूरी है"
        safety = "Prompt guardrails configured" if safeguards else "FAIL: grounding guardrails missing"
        rows.append(
            f"| {index} | {case['question']} | {sources} | {coverage} | {support} | {safety} |"
        )

    unrelated = retriever.retrieve("quantum entanglement in distant galaxies", k=4)
    unrelated_pass = not unrelated
    report = [
        "# Seller Assistant RAG Evaluation",
        "",
        f"Generated: {datetime.now().astimezone().isoformat(timespec='minutes')}",
        "",
        "## Method and limits",
        "",
        "Fifteen Hindi seller questions were sent through the production Chroma retriever. A case passes retrieval/context support when at least one expected knowledge file is in top-4 and at least half (minimum two) of its expected concepts appear in those retrieved chunks. Similarity scores are cosine similarity. The guardrail column checks prompt configuration only; this offline suite does not call Sarvam or claim that a generated answer was empirically fact-checked.",
        "",
        "Seller metrics are not indexed in Chroma. They are loaded by existing Python tools and added to the agent context separately. Retrieved knowledge is general guidance; source examples remain illustrative.",
        "",
        "## Repository audit",
        "",
        f"- Knowledge-base path resolves to `{retriever.vector_store.persist_directory.parent.parent / 'src' / 'files' / 'knowledge_base'}` in this checkout; {len(load_md_files())} non-empty Markdown files produce {len(current_chunks)} chunks (1,000 characters, 200 overlap).",
        f"- Persisted Chroma collection `{retriever.vector_store.collection.name}` contains {len(indexed_ids)} chunks. Index freshness by stable source/content IDs: {'PASS' if index_fresh else 'FAIL'} ({len(expected_ids - indexed_ids)} missing, {len(indexed_ids - expected_ids)} stale).",
        f"- Exact duplicate chunk texts: {exact_duplicates}. Chunks missing filename metadata: {metadata_missing}.",
        "- Actual embedding implementation: scikit-learn TF-IDF with English stop-word removal and 1–2 grams, stored as Chroma cosine vectors. Sentence Transformers / `all-MiniLM-L6-v2` are not used or declared in `pyproject.toml`.",
        "- Retrieval was disconnected from neither the prompt nor graph: `generate_formatted_prompt` retrieves, includes source-labelled chunks in a `SystemMessage`, and `model.invoke` receives it. The system/RAG prompt says to use relevant chunks as general guidance. A local mock-LLM integration test verifies delivery, but only live model evaluation can prove generated answers actually follow them.",
        "- Audit issue: English TF-IDF vocabulary returned zero-similarity arbitrary chunks for Devanagari queries because threshold was zero. Hindi term expansion and a 0.05 similarity floor now target that failure. Repeated same-file chunks were also observed, so final results cap at two chunks per file and backfill from a limited candidate window; final context remains top-4.",
        "",
        "## Results",
        "",
        "| # | Hindi evaluation question | Top-4 retrieved sources (similarity) | Expected concepts found | Context support | Unsupported-assumption guardrail |",
        "|---:|---|---|---:|---|---|",
        *rows,
        "",
        f"**Summary: {passed}/{len(CASES)} cases passed.** Unrelated-query rejection: {'PASS' if unrelated_pass else 'FAIL'} ({len(unrelated)} chunks returned).",
        "",
        "## Interpretation",
        "",
        "A passing context-support result means the retrieved text contains the expected business concepts. It does not prove that the LLM follows the context in every answer. Live response grounding, natural Hindi quality, and voice delivery still require manual conversation testing with the Sarvam service.",
        "",
    ]
    return "\n".join(report)


if __name__ == "__main__":
    output_path = Path(__file__).with_name("RAG_QUALITY_EVALUATION.md")
    content = run_evaluation()
    output_path.write_text(content, encoding="utf-8")
    print(f"Wrote {output_path}")
    summary_line = next(line for line in content.splitlines() if line.startswith("**Summary:"))
    print(summary_line)
    if "Summary: 15/15 cases passed." not in content or "Unrelated-query rejection: PASS" not in content:
        raise SystemExit(1)
