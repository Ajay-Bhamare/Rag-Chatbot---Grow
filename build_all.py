"""Run the full ingestion pipeline: loading -> chunking -> embedding -> ChromaDB."""
import loader
import chunker
import embed_store

if __name__ == "__main__":
    loader.main()
    chunker.main()
    embed_store.main()
    print("RAG store ready. Run: python app.py")
