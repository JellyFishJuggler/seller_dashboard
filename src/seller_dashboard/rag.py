"""RAG utilities for the Snapdeal Seller Assistant.

Importing this module does not load models or index documents.
Run `python -m seller_dashboard.rag` from the project environment to rebuild
the local ChromaDB index.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import chromadb
import joblib
import yaml
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer


MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = MODULE_PATH.parents[2]
DEFAULT_KNOWLEDGE_BASE = MODULE_PATH.parents[1] / "files" / "knowledge_base"
DEFAULT_PERSIST_DIRECTORY = PROJECT_ROOT / "data" / "vector_store"
DEFAULT_COLLECTION_NAME = "seller_knowledge_base_tfidf"
DEFAULT_SIMILARITY_THRESHOLD = 0.05
MAX_CHUNKS_PER_SOURCE = 2

# The verified knowledge corpus is English while the assistant now accepts and
# answers in Hindi. Expand common seller-business phrases to corpus vocabulary
# for lexical retrieval; this is term expansion, not a translation of the user
# message or seller-specific data.
_HINDI_RETRIEVAL_TERMS = (
    ("बिक्री", "sales revenue"),
    ("ऑर्डर", "orders order volume"),
    ("आर्डर", "orders order volume"),
    ("औसत बिक्री मूल्य", "average selling price ASP price mix"),
    ("एएसपी", "average selling price ASP"),
    ("छूट", "discount promotion pricing"),
    ("डिस्काउंट", "discount promotion pricing"),
    ("कीमत", "price pricing price positioning"),
    ("दाम", "price pricing"),
    ("मुनाफा", "profit profitability margin unit economics cost fees"),
    ("मुनाफ़ा", "profit profitability margin unit economics cost fees"),
    ("लाभ", "profit profitability margin contribution"),
    ("लागत", "cost fees shipping packaging returns contribution margin"),
    ("मार्जिन", "margin gross margin contribution margin"),
    ("स्टॉक आउट", "stockout out of stock inventory"),
    ("आउट ऑफ स्टॉक", "stockout stockouts stockout recovery out of stock inventory historical product orders restock prioritization"),
    ("स्टॉक खत्म", "stockout stockouts stockout recovery out of stock inventory historical product orders"),
    ("इन्वेंटरी", "inventory stock availability forecast replenishment reorder point safety stock"),
    ("रीस्टॉक", "restocking replenishment stockout recovery supplier lead time historical orders"),
    ("दोबारा मंगव", "replenishment restocking supplier lead time reorder point inventory forecast"),
    ("मंगाने", "replenishment restocking supplier lead time reorder point inventory forecast"),
    ("मात्रा", "quantity safety stock demand forecast reorder point inventory"),
    ("पहले किन्हें", "prioritization stockout historical product orders restock recovery"),
    ("दृश्यता", "search visibility discoverability impressions"),
    ("कम दिख", "search visibility discoverability impressions"),
    ("सर्च", "search visibility discoverability impressions"),
    ("कन्वर्ज़न", "conversion rate product page visits clicks orders"),
    ("कन्वर्शन", "conversion rate product page visits clicks orders"),
    ("व्यू", "views product page visits clicks conversion"),
    ("क्लिक", "clicks visits conversion funnel"),
    ("कैंसलेशन", "cancellation rate cancellation reasons fulfillment"),
    ("रद्द", "cancellation rate cancellation reasons order fulfillment"),
    ("रिटर्न", "returns RTO refund reverse logistics"),
    ("वापसी", "returns RTO refund reverse logistics"),
    ("आरटीओ", "RTO return to origin returns"),
    ("लिस्टिंग", "product listing catalogue title images attributes"),
    ("शीर्षक", "product title listing catalogue"),
    ("तस्वीर", "product images listing"),
    ("फोटो", "product images listing"),
    ("कपड़ों", "apparel clothing fashion size fit variants"),
    ("कपड़े", "apparel clothing fashion size fit variants"),
    ("साइज़", "apparel size chart fit variants returns"),
    ("होम डेकोर", "home decor merchandising product photography"),
    ("घर की सजावट", "home decor merchandising product photography"),
    ("मोबाइल", "mobile accessories charger cable compatibility specifications"),
    ("चार्जर", "mobile accessories charger compatibility wattage"),
    ("केबल", "mobile accessories cable connector compatibility specifications"),
    ("प्राथमिकता", "prioritization business action impact urgency effort"),
    ("पहले क्या", "prioritization business action impact urgency effort"),
    ("एक्शन", "business action planning impact urgency effort"),
    ("कार्रवाई", "business action planning impact urgency effort"),
)


def expand_retrieval_query(query: str) -> str:
    """Add English corpus terms for recognized Hindi seller-business phrases."""
    normalized = query.lower()
    expansions = [
        english_terms
        for hindi_phrase, english_terms in _HINDI_RETRIEVAL_TERMS
        if hindi_phrase in normalized
    ]
    if not expansions:
        return query
    return f"{query}\nBusiness knowledge terms: {' '.join(dict.fromkeys(expansions))}"


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Convert frontmatter values to ChromaDB-compatible metadata values."""
    safe = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            safe[key] = value
        elif isinstance(value, list):
            safe[key] = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            safe[key] = str(value)
        else:
            safe[key] = str(value)
    return safe


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse optional YAML frontmatter at the beginning of a Markdown file."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    end = next(
        (i for i in range(1, len(lines)) if lines[i].strip() in {"---", "..."}),
        None,
    )
    if end is None:
        return {}, text

    try:
        metadata = yaml.safe_load("\n".join(lines[1:end])) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid Markdown YAML frontmatter: {exc}") from exc

    if not isinstance(metadata, dict):
        raise ValueError("Markdown frontmatter must be a YAML mapping.")

    return metadata, "\n".join(lines[end + 1:]).strip()


def load_md_files(data_folder: str | Path | None = None) -> list[Document]:
    """Load top-level .md files and retain YAML frontmatter as metadata."""
    folder = Path(data_folder).resolve() if data_folder else DEFAULT_KNOWLEDGE_BASE
    if not folder.is_dir():
        raise FileNotFoundError(f"Knowledge-base directory not found: {folder}")

    paths = sorted(folder.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"No Markdown files found in: {folder}")

    documents = []
    for path in paths:
        raw = TextLoader(str(path), encoding="utf-8").load()[0].page_content
        metadata, body = _parse_frontmatter(raw)
        if not body.strip():
            print(f"Skipping empty Markdown file: {path.name}")
            continue

        metadata["source"] = str(path)
        metadata["filename"] = path.name
        documents.append(
            Document(page_content=body, metadata=_safe_metadata(metadata))
        )

    if not documents:
        raise ValueError(f"No non-empty Markdown documents found in: {folder}")

    print(f"Loaded {len(documents)} Markdown documents.")
    return documents


def split_doc(
    documents: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("Use chunk_size > chunk_overlap >= 0.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")
    return chunks


class EmbeddingManager:
    """Create local TF-IDF vectors without loading a machine-learning model."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )

    def fit_transform(self, texts: list[str]):
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []
        return self.vectorizer.fit_transform(texts).toarray()

    def generate_embeddings(self, texts: str | list[str]):
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []
        return self.vectorizer.transform(texts).toarray()


class VectorStore:
    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_directory: str | Path = DEFAULT_PERSIST_DIRECTORY,
    ):
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory).resolve()
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={
                "description": "Snapdeal seller Markdown knowledge base",
                "hnsw:space": "cosine",
            },
        )
        print(
            f"Vector store ready: {collection_name} "
            f"({self.collection.count()} chunks)."
        )

    def reset_collection(self) -> None:
        """Delete and recreate this collection before a clean rebuild."""
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={
                "description": "Snapdeal seller Markdown knowledge base",
                "hnsw:space": "cosine",
            },
        )

    @staticmethod
    def _stable_id(document: Document, index: int) -> str:
        source = str(document.metadata.get("source", "unknown"))
        raw = f"{source}\n{index}\n{document.page_content}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def add_documents(self, documents: list[Document], embeddings) -> None:
        if len(documents) != len(embeddings):
            raise ValueError("Documents and embeddings must have equal lengths.")
        if not documents:
            return

        ids = [self._stable_id(doc, i) for i, doc in enumerate(documents)]
        texts = [doc.page_content for doc in documents]
        metadatas = []
        for i, doc in enumerate(documents):
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = i
            metadata["content_length"] = len(doc.page_content)
            metadatas.append(_safe_metadata(metadata))

        vectors = [
            vector.tolist() if hasattr(vector, "tolist") else list(vector)
            for vector in embeddings
        ]

        batch_size = 100
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            self.collection.upsert(
                ids=ids[start:end],
                documents=texts[start:end],
                metadatas=metadatas[start:end],
                embeddings=vectors[start:end],
            )

        print(f"Indexed {len(documents)} chunks. Total: {self.collection.count()}.")


def build_vector_store(
    data_folder: str | Path | None = None,
    persist_directory: str | Path = DEFAULT_PERSIST_DIRECTORY,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    rebuild: bool = True,
) -> VectorStore:
    """Explicitly load, chunk, embed and index the knowledge base."""
    documents = load_md_files(data_folder)
    chunks = split_doc(documents, chunk_size, chunk_overlap)
    embeddings_manager = EmbeddingManager()
    embeddings = embeddings_manager.fit_transform(
        [chunk.page_content for chunk in chunks]
    )

    store = VectorStore(collection_name, persist_directory)
    if not rebuild and store.collection.count():
        raise ValueError("TF-IDF indexes must be rebuilt as a whole; use rebuild=True.")
    if rebuild:
        store.reset_collection()
    store.add_documents(chunks, embeddings)
    vectorizer_path = store.persist_directory / f"{collection_name}.vectorizer.joblib"
    joblib.dump(embeddings_manager.vectorizer, vectorizer_path)
    return store


class RAGRetriever:
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_manager: EmbeddingManager,
    ):
        self.vector_store = vector_store
        self.embedding_manager = embedding_manager

    def retrieve(
        self,
        query: str,
        k: int = 5,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> list[dict[str, Any]]:
        """Return top-k chunks; threshold is cosine similarity from 0 to 1."""
        if not query or not query.strip():
            raise ValueError("Query cannot be empty.")
        if k <= 0:
            raise ValueError("k must be greater than zero.")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1.")

        count = self.vector_store.collection.count()
        if count == 0:
            return []

        expanded_query = expand_retrieval_query(query.strip())
        query_vector = self.embedding_manager.generate_embeddings([expanded_query])[0]
        query_vector = (
            query_vector.tolist()
            if hasattr(query_vector, "tolist")
            else list(query_vector)
        )
        # The source cap below prevents the final prompt from being dominated
        # by adjacent chunks from one file. Fetch a small candidate window so
        # relevant sources can still backfill the top-k output.
        results = self.vector_store.collection.query(
            query_embeddings=[query_vector],
            n_results=min(k * 3, count),
            include=["documents", "metadatas", "distances"],
        )

        found = []
        per_source: dict[str, int] = {}
        docs = results.get("documents", [[]])[0] or []
        metas = results.get("metadatas", [[]])[0] or []
        distances = results.get("distances", [[]])[0] or []
        ids = results.get("ids", [[]])[0] or []

        for rank, (doc_id, content, metadata, distance) in enumerate(
            zip(ids, docs, metas, distances), start=1
        ):
            # Chroma cosine distance = 1 - cosine similarity.
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            if similarity < threshold:
                continue
            metadata = metadata or {}
            source = str(metadata.get("filename") or metadata.get("source") or "unknown")
            if per_source.get(source, 0) >= MAX_CHUNKS_PER_SOURCE:
                continue
            per_source[source] = per_source.get(source, 0) + 1
            found.append({
                "id": doc_id,
                "content": content,
                "metadata": metadata,
                "similarity_score": similarity,
                "distance": float(distance),
                "rank": rank,
            })
            if len(found) >= k:
                break
        return found


def get_retriever(
    persist_directory: str | Path = DEFAULT_PERSIST_DIRECTORY,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> RAGRetriever:
    """Open an already-built index. This function does not rebuild it."""
    store = VectorStore(collection_name, persist_directory)
    if store.collection.count() == 0:
        raise RuntimeError("RAG index is empty. Run build_vector_store() first.")
    vectorizer_path = store.persist_directory / f"{collection_name}.vectorizer.joblib"
    if not vectorizer_path.is_file():
        raise RuntimeError(
            f"TF-IDF vocabulary not found: {vectorizer_path}. "
            "Rebuild the index with `python -m seller_dashboard.rag`."
        )
    embeddings = EmbeddingManager()
    embeddings.vectorizer = joblib.load(vectorizer_path)
    return RAGRetriever(store, embeddings)


if __name__ == "__main__":
    build_vector_store(rebuild=True)
