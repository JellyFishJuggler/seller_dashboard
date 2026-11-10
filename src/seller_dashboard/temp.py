import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

from seller_dashboard.rag import get_retriever


def main() -> None:
    load_dotenv()

    question = input("Ask a question about the seller knowledge base: ").strip()
    if not question:
        raise ValueError("Please enter a question.")

    retriever = get_retriever()
    results = retriever.retrieve(question, k=5)
    if not results:
        print("No relevant Markdown chunks were found in the RAG index.")
        return

    context = "\n\n".join(
        f"[{index}] {result['content']}"
        for index, result in enumerate(results, start=1)
    )

    print("\nRetrieved Markdown chunks:")
    for index, result in enumerate(results, start=1):
        source = result["metadata"].get("filename") or result["metadata"].get("source", "unknown")
        print(
            f"{index}. {source} "
            f"(similarity: {result['similarity_score']:.3f})"
        )

    model = ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
        temperature=0,
    )
    response = model.invoke(
        "Answer the question using only the supplied knowledge-base context. "
        "If the context does not contain the answer, say that clearly. "
        "Cite supporting chunks using their bracketed numbers.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )

    print("\nQwen answer:")
    print(response.content)


if __name__ == "__main__":
    main()