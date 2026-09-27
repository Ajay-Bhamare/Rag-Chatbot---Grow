"""STAGES 3+4 - EMBEDDING + STORING vector data.

Embedding model: sentence-transformers/all-MiniLM-L6-v2 (384 dims).
Why this one: FAQ retrieval over short fact chunks needs speed + small
memory on CPU, and MiniLM-L6-v2 is the standard quality/size sweet spot
for English semantic search. Multilingual or larger models add load with
no gain on this corpus.

Vector DB: ChromaDB, PersistentClient at data/chroma, collection "mf_faqs".
Each vector stores metadata {scheme, category, url} so every hit already
carries its citation link — retrieval and sourcing are one step.
"""
import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parent
MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def main() -> None:
    chunks = json.loads((BASE / "data" / "chunks.json").read_text(encoding="utf-8"))
    print(f"loading {MODEL} ...")
    model = SentenceTransformer(MODEL)
    texts = [c["text"] for c in chunks]
    print(f"embedding {len(texts)} chunks ...")
    vectors = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    client = chromadb.PersistentClient(path=str(BASE / "data" / "chroma"))
    col = client.get_or_create_collection("mf_faqs", metadata={"hnsw:space": "cosine"})
    if col.count() > 0:  # rebuild keeps the store in sync with sources.csv
        client.delete_collection("mf_faqs")
        col = client.create_collection("mf_faqs", metadata={"hnsw:space": "cosine"})
    col.add(
        ids=[c["id"] for c in chunks],
        embeddings=[v.tolist() for v in vectors],
        documents=texts,
        metadatas=[
            {"scheme": c["scheme"], "category": c["category"], "url": c["url"]}
            for c in chunks
        ],
    )
    print(f"stored {col.count()} vectors -> data/chroma")


if __name__ == "__main__":
    main()
