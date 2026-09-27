# Architecture — MF FAQ RAG Chatbot

Follows the required RAG stages exactly: **Loading → Chunking → Embedding →
Storing vector data → Retrieval → Answering**. One Python module per stage.

```
sources.csv
    │  (5 public Groww URLs + scheme/category labels)
    ▼
┌──────────┐  requests + BeautifulSoup   ┌──────────────┐
│ loader.py│ ──────────────────────────▶ │ data/raw.json│  5 docs {scheme, category, url, text}
└──────────┘                             └──────┬───────┘
                                                │ strip_noise()
                                                ▼
┌──────────┐  recursive split (600/120)  ┌────────────────┐
│chunker.py│ ──────────────────────────▶ │data/chunks.json│  ~111 chunks {id, text, scheme, category, url}
└──────────┘  + scheme prefix + dedupe   └───────┬────────┘
                                                 │ all-MiniLM-L6-v2 (384-d, CPU)
                                                 ▼
┌──────────────┐  PersistentClient        ┌──────────────┐
│embed_store.py│ ──────────────────────▶  │ data/chroma/ │  ChromaDB `mf_faqs`, cosine
└──────────────┘  metadata per vector    └──────┬───────┘
                                                │ query embedding + where{scheme} + re-rank
                                                ▼
┌──────────┐  guards → intent → extract  ┌──────────────┐
│answer.py │ ◀────────────────────────── │ top-4 chunks │  each hit carries its citation URL
└────┬─────┘                             └──────────────┘
     │ {answer, source}
     ▼
┌──────────┐  welcome + 3 examples + disclaimer
│ app.py   │  Flask, POST /ask
└──────────┘
```

## Key design decisions
1. **Recursive chunking, not semantic.** Facts are atomic one-liners
   (“Expense ratio1.21%”); semantic chunking would fuse unrelated facts
   into one vector. Recursive splitting on paragraph → line → sentence
   keeps each fact intact, deterministic and free.
2. **Noise stripped before chunking.** Holdings tables (50–300 rows),
   historical exit-load rows, returns/SIP-calculator tables and
   compare-funds tables never enter the corpus — they drown retrieval and
   returns data must never be quoted (PRD §4).
3. **Attribution inside the chunk.** Every chunk is prefixed
   `[scheme | category]` and carries `{scheme, category, url}` metadata,
   so a retrieved vector is always citable.
4. **Intent-routed extraction, not pooled matching.** The query is
   classified to one intent (expense/exit/sip/…) and only that extractor
   runs. (Looping all extractors over pooled text answered the wrong
   question — found during testing.)
5. **Hybrid retrieval.** Vector cosine top-8 → keyword-overlap re-rank to
   top-4. Pure vector search missed exact fact lines (“Expense ratio1.21%”);
   the re-rank guarantees the chunk containing the query's keywords wins.
6. **No generative LLM.** The composer is regex-extractive, so facts-only
   answers, refusals, PII rejection and the returns ban hold by
   construction, not by prompt hope.
7. **Guards run before retrieval.** PII and advice patterns short-circuit;
   the corpus is never consulted for disallowed questions.

## Data contracts
- `raw.json`: `[{scheme, category, url, text, fetched_at}]`
- `chunks.json`: `[{id, text, scheme, category, url}]`
- Chroma `mf_faqs`: ids + 384-d normalized embeddings + same metadata.
- `answer(query) -> {answer, source, refused}` — UI consumes only this.
