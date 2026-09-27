# HDFC Mutual Fund FAQ RAG Chatbot

Facts-only assistant over 5 public HDFC scheme pages (Groww, Direct–Growth).
Pipeline: **Loading → Chunking → Embedding → ChromaDB → Retrieval → Answering**.
See `PRD.md`, `architecture.md`, `docs/implementation.md`.

## Setup (Windows, no system Python needed)
The project carries a portable Python 3.12 in `.python/` (the machine has no
system Python and its Windows-Installer service is wedged, so `winget`/MSI
installs fail — the embeddable zip needs no installer).

```powershell
cd mf-faq-rag
# (first time) install deps into the portable runtime
.python\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.python\python.exe -m pip install -r requirements.txt
# build the RAG store: fetch pages -> chunk -> embed -> ChromaDB
.python\python.exe build_all.py
# run the UI
.python\python.exe app.py   # http://localhost:5000
```

## Scope
HDFC Large Cap, Flexi Cap (HDFC Equity Fund), ELSS Tax Saver, Small Cap,
Balanced Advantage — Direct Growth plans. Sources: `sources.csv`.

## What it answers
Expense ratio, exit load, min SIP/lumpsum, lock-in, riskometer, benchmark,
NAV, AUM, fund manager, category, stamp duty, tax note, statement guidance —
each with one citation link. Advice, returns comparisons and PII are refused.

## Disclaimer (also shown in the UI)
> Facts-only assistant. No investment advice. Answers come only from the 5
> public HDFC scheme pages listed in sources. Figures are a snapshot of the
> fetch date (27 Sep 2026); NAV/AUM change daily.

## Known limits
- Snapshot data; statement guidance limited to registrar (CAMS) info on pages.
- English, one intent per question; no generative LLM (extractive only).
