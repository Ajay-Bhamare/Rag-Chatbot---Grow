# PRD — Mutual Fund FAQ RAG Chatbot (HDFC, Facts-Only)

## 1. Problem
Retail users and support teams ask the same factual mutual-fund questions
over and over: expense ratio, exit load, minimum SIP, ELSS lock-in,
riskometer, benchmark, how to download statements. Answers must come from
official public pages — never from memory, blogs, or advice.

## 2. Goal
A working FAQ assistant that answers facts about 3–5 HDFC schemes using
only 5 public source pages, with one citation link in every answer.
No investment advice, ever.

## 3. Scope
- **AMC:** HDFC Mutual Fund. **Corpus (5 pages, Direct–Growth plans):**

| # | Scheme | Category | URL |
|---|--------|----------|-----|
| 1 | HDFC Large Cap Fund Direct Growth | Large Cap | https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth |
| 2 | HDFC Flexi Cap Direct Plan Growth (HDFC Equity Fund) | Flexi Cap | https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth |
| 3 | HDFC ELSS Tax Saver Fund Direct Plan Growth | ELSS | https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth |
| 4 | HDFC Small Cap Fund Direct Growth | Small Cap | https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth |
| 5 | HDFC Balanced Advantage Fund Direct Growth | Hybrid – Balanced Advantage | https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth |

- **In scope questions:** expense ratio, exit load, minimum SIP / lumpsum,
  lock-in (ELSS), riskometer, benchmark, NAV, AUM, fund manager, category,
  stamp duty, tax implication, statement download guide.
- **Out of scope:** any other AMC/scheme, returns computation or comparison,
  buy/sell/hold guidance, account-specific data.

## 4. Functional requirements
1. **Ingestion:** fetch the 5 pages live, extract readable text, save raw docs.
2. **Chunking:** recursive character splitting (~600 chars, ~120 overlap);
   each chunk tagged with scheme + category + URL; boilerplate deduped;
   holdings lists, historical load tables and returns tables stripped.
3. **Embedding:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim, CPU).
4. **Vector store:** ChromaDB persistent collection with scheme/category/URL
   metadata per vector.
5. **Retrieval:** same-model query embedding, cosine top-8 filtered to the
   named scheme, keyword-overlap re-rank to top-4.
6. **Answers:** deterministic extractive composer, ≤3 sentences, exactly one
   citation link, plus `Last updated from sources: <fetch date>`.
7. **Refusals:** advice/opinion questions → polite facts-only refusal +
   educational link. Returns questions → factsheet redirect, no numbers.
8. **PII guard:** PAN/Aadhaar/account/OTP/email/phone patterns rejected
   before retrieval; nothing personal is stored.
9. **UI:** welcome line, 3 example questions, disclaimer
   (“Facts-only. No investment advice.”).

## 5. Non-functional requirements
- CPU-only, runs on a laptop; no GPU, no paid APIs, no generative LLM.
- Reproducible: `build_all.py` rebuilds the whole store from sources.
- Public sources only; no screenshots of app back-ends; no third-party blogs.

## 6. Deliverables
1. Working prototype (local Flask app) or ≤3-min demo video.
2. `sources.csv` — the 5 URLs.
3. `README.md` — setup, scope, known limits.
4. `sample_qa.md` — 5–10 queries with answers + links.
5. Disclaimer snippet (in UI and README).

## 7. Known limits
- Facts are a snapshot of the fetch date; NAV/AUM drift daily.
- Statement-download guidance is limited to registrar info printed on the
  scheme pages (CAMS).
- English queries only; one intent per question.
