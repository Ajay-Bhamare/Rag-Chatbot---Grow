# Implementation Plan — phase-wise (for Cursor)

Read `../architecture.md` and `../PRD.md` first. Implement phases in order;
each phase lists files, steps, and a **verify** command. Do not start the
next phase until its verify passes. Python binary: `.python/python.exe`
(portable 3.12, project-local; the machine has no system Python).

## Phase 0 — Scaffold + Python environment
- **Files:** `requirements.txt`, `.gitignore`, `.python/` (portable runtime)
- **Steps:**
  1. Create project dirs (`data/`, `docs/`).
  2. Unzip `python-3.12.10-embed-amd64.zip` to `.python/`; enable `import site`
     in `python312._pth` and append the project root path to it (embedded
     builds run isolated and ignore PYTHONPATH).
  3. `get-pip.py`, then CPU torch first:
     `pip install torch --index-url https://download.pytorch.org/whl/cpu`
  4. `pip install -r requirements.txt` (`sentence-transformers`, `chromadb>=1.0`,
     `flask`, `requests`, `beautifulsoup4`, `lxml`).
     Note: `chromadb==0.6.3` does NOT build on machines without a C++
     compiler (chroma-hnswlib); use `chromadb>=1.0` (prebuilt wheels).
- **Verify:** `.python/python.exe -c "import requests, bs4, chromadb,
  sentence_transformers, flask"` prints no error.
- **Status:** ✅ done.

## Phase 1 — Sources + Loading (`loader.py`)
- **Files:** `sources.csv` (5 Groww URLs + scheme/category), `loader.py`
- **Steps:**
  1. Write `sources.csv` with the 5 Direct–Growth HDFC URLs from PRD §3.
  2. `loader.py`: GET each URL (browser User-Agent, timeout 40s), strip
     script/style/nav/footer, collapse whitespace, save
     `data/raw.json` as `[{scheme, category, url, text, fetched_at}]`.
- **Verify:** `data/raw.json` exists with 5 docs; each `text` contains its
  scheme name and an `Expense ratio` line.
- **Status:** ✅ done (5 pages, ~126KB).

## Phase 2 — Chunking (`chunker.py`)
- **Files:** `chunker.py` → `data/chunks.json`
- **Steps:**
  1. Implement `strip_noise()`: drop historical exit-load rows
     (`DD Mon YYYY` + `Exit load`, multiline-tolerant), `Holdings (…)…See All`
     blocks (header spans lines after HTML cleanup — match
     `Holdings\s*\(\s*\d+\s*\)`), returns/ranking tables, SIP-calculator
     blocks, compare-funds tables.
  2. Recursive splitter (separators paragraph → line → sentence → word),
     `CHUNK_SIZE=600`, `OVERLAP=120`, hard-cut oversized pieces.
  3. Prefix each chunk `[scheme | category]`; drop stubs (<40 chars) and
     exact cross-page duplicates (nav/footer boilerplate).
- **Verify:** `data/chunks.json` has ~110 chunks; zero chunks contain
  `Holdings (`; expense-with-number chunks exist per scheme
  (see `inspect_chunks.py` pattern).
- **Status:** ✅ done (111 chunks, 0 holdings noise).

## Phase 3 — Embedding + vector store (`embed_store.py`)
- **Files:** `embed_store.py` → `data/chroma/`
- **Steps:**
  1. Load `sentence-transformers/all-MiniLM-L6-v2` (384-dim, normalized).
  2. Embed all chunk texts; rebuild ChromaDB `PersistentClient`
     collection `mf_faqs` (cosine) with `{scheme, category, url}` metadata.
  3. Full rebuild entrypoint: `build_all.py` runs loader → chunker →
     embed_store.
- **Verify:** collection count equals chunk count; `build_all.py` ends with
  “RAG store ready”.
- **Status:** ✅ done (111 vectors).

## Phase 4 — Retrieval + answer composer (`answer.py`)
- **Files:** `answer.py` exposing `answer(query) -> {answer, source, refused}`
- **Steps:**
  1. Guards first: `PII_PAT` (PAN/Aadhaar/account/OTP/email/phone) and
     `ADVICE_PAT` (buy/sell/best/should-I…) short-circuit with refusal +
     educational link — corpus never consulted.
  2. `detect_scheme()` keyword map → Chroma `where={"scheme": …}` filter.
     Keep mapped names byte-identical to `sources.csv` (the Flexi Cap entry
     carries its “(HDFC Equity Fund)” suffix — a mismatch silently returns
     zero hits).
  3. Vector top-8 → keyword-overlap re-rank → top-4 (pure cosine missed
     exact fact lines).
  4. `detect_intent()` from query keywords; run ONLY that intent's
     extractor over hits (never loop all intents over pooled text).
     Special cases: `lock` → ELSS 3-year rule vs “no lock-in stated”;
     `statement` → CAMS registrar answer; returns-pattern → factsheet
     redirect with the scheme URL.
  5. Every answer: ≤3 sentences + `Last updated from sources: <date>` +
     exactly one citation URL.
- **Verify:** `smoke_test.py` — 11 queries: 6 facts correct with right
  scheme links, 2 advice refusals, 1 returns redirect, 1 PII refusal,
  1 statement answer.
- **Status:** ✅ done (11/11 pass).

## Phase 5 — UI + deliverables (`app.py`, docs)
- **Files:** `app.py`, `README.md`, `sample_qa.md`, this file
- **Steps:**
  1. Flask UI `/` (welcome + 3 example buttons + disclaimer) and
     `POST /ask` → `answer()`.
  2. `README.md`: setup (portable Python!), scope, limits.
  3. `sample_qa.md`: 5–10 queries with answers + links (from smoke test).
  4. Boot the app, ask 3 questions through HTTP, confirm JSON + links.
- **Verify:** `POST /ask` returns `{answer, source}` with a groww.in link.
- **Status:** ✅ done (3/3 HTTP checks: fact + citation, advice refusal, benchmark).
