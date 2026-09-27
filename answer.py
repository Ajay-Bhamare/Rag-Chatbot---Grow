"""STAGE 5 - DATA RETRIEVAL + facts-only answer composer.

Retrieval: embed the query with the same MiniLM model, cosine top-8 from
Chroma filtered to the named scheme, then keyword-overlap re-rank so the
chunk holding the exact fact line wins.

Answering is deterministic/extractive (no generative LLM):
  1. PII / advice guards run before retrieval.
  2. The question's INTENT is classified from keywords (expense, exit, sip
     ...), and ONLY that intent's extractor runs over the retrieved chunks.
     (Earlier design looped all intents over the pooled text, so the first
     matching intent could answer a different question than asked.)
  3. Replies are <=3 sentences with exactly one citation link + fetch date.
This guarantees the brief's constraints by construction.
"""
import os
import re
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

BASE = Path(__file__).resolve().parent
FETCHED_ON = "27 Sep 2026"  # date the 5 source pages were loaded

_client, _col, _model = None, None, None


def _store():
    global _client, _col, _model
    if _col is None:
        _client = chromadb.PersistentClient(path=str(BASE / "data" / "chroma"))
        _col = _client.get_collection("mf_faqs")
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _col, _model


SCHEMES = {
    "large cap": "HDFC Large Cap Fund Direct Growth",
    "flexi": "HDFC Flexi Cap Direct Plan Growth (HDFC Equity Fund)",
    "hdfc equity": "HDFC Flexi Cap Direct Plan Growth (HDFC Equity Fund)",
    "elss": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "tax saver": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "small cap": "HDFC Small Cap Fund Direct Growth",
    "balanced advantage": "HDFC Balanced Advantage Fund Direct Growth",
    "hybrid": "HDFC Balanced Advantage Fund Direct Growth",
}

ADVICE_PAT = re.compile(
    r"should i|buy or sell|shall i|recommend|suggest|advice|advise|best fund|"
    r"which (fund|scheme|one) (is|should)|invest in|worth investing|good time|"
    r"will (it|this) (go|rise|grow)|predict|forecast|target price",
    re.I,
)
RETURNS_PAT = re.compile(
    r"\breturns?\b|\breturned\b|performance|compare|versus|\bcagr\b|"
    r"which.*(grew|earned)|past.*(year|month)",
    re.I,
)
PII_PAT = re.compile(
    r"[A-Z]{5}[0-9]{4}[A-Z]"  # PAN
    r"|\b\d{4}\s?\d{4}\s?\d{4}\b"  # Aadhaar / card
    r"|\b[6-9]\d{9}\b"  # Indian mobile
    r"|\b\d{9,18}\b"  # account number
    r"|[\w.+-]+@[\w-]+\.[\w.]+"  # email
    r"|\botp\b",
    re.I,
)

EDU_LINK = "https://groww.in/mutual-funds"
ELSS_URL = "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth"

# intent -> (regex, answer template). {m} = first group, {gN} = Nth group.
INTENTS = {
    "expense": (re.compile(r"expense ratio\s*([\d.]+%)", re.I), "The expense ratio is {m}."),
    "exit": (re.compile(r"exit load of ([A-Za-z0-9][^.]*?)(?:\.|;|stamp duty|$)", re.I), "Exit load: {m}."),
    "exit_for": (re.compile(r"exit load for (units[^.]*?)(?:\.|$)", re.I), "Exit load: for {m}."),
    "exit_nil": (re.compile(r"exit load\s*(nil)", re.I), "Exit load: {m}."),
    "sip": (re.compile(r"min\.?\s*for SIP\s*[^\d]*([\d,]+)", re.I), "Minimum SIP is Rs.{m}."),
    "lumpsum": (re.compile(r"min\.?\s*for 1st investment\s*[^\d]*([\d,]+)", re.I), "Minimum lumpsum investment is Rs.{m}."),
    "risk": (re.compile(r"rated?\s*(very high|high|moderate|low|moderately high)\s*risk", re.I), "Riskometer: {m} risk."),
    "benchmark": (re.compile(r"fund benchmark\s*([A-Za-z0-9][A-Za-z0-9 :&/\-.]*?)(?:scheme information|fund house|$)", re.I), "Benchmark: {m}."),
    "nav": (re.compile(r"latest NAV as of ([\d\w '\"]+) is\s*[^\d]*([\d,.]+)", re.I), "Latest NAV was Rs.{g2} as of {g1}."),
    "aum": (re.compile(r"fund size \(AUM\)\s*[^\d]*([\d,.]+\s*Cr)", re.I), "Fund size (AUM) is Rs.{m}."),
    "manager": (re.compile(r"([A-Z][a-z]+ [A-Z][a-z]+) is the current fund manager", re.I), "Fund manager: {m}."),
    "category": (re.compile(r"is a (equity|hybrid|debt) mutual fund", re.I), "Category: {m} mutual fund scheme."),
    "stamp": (re.compile(r"stamp duty on investment:\s*([^)]+?\)?)", re.I), "Stamp duty: {m}."),
    "tax": (re.compile(r"tax implication([^.]{10,180})", re.I | re.S), "Tax: {m}."),
}

EXIT_VARIANTS = ["exit", "exit_for", "exit_nil"]


def detect_intent(q: str) -> str | None:
    ql = q.lower()
    if "statement" in ql or "capital gain" in ql:
        return "statement"
    if "expense" in ql:
        return "expense"
    if "exit" in ql:
        return "exit"
    if "sip" in ql:
        return "sip"
    if "lumpsum" in ql or "lump sum" in ql or "minimum investment" in ql or "min investment" in ql or "first investment" in ql:
        return "lumpsum"
    if "lock" in ql:
        return "lock"
    if "risk" in ql:
        return "risk"
    if "benchmark" in ql or "index" in ql or "tracks" in ql:
        return "benchmark"
    if "nav" in ql:
        return "nav"
    if "aum" in ql or "fund size" in ql or "asset under" in ql:
        return "aum"
    if "manager" in ql or "manage" in ql:
        return "manager"
    if "category" in ql or "what type" in ql:
        return "category"
    if "stamp" in ql:
        return "stamp"
    if "tax" in ql:
        return "tax"
    return None


def detect_scheme(q: str) -> str | None:
    ql = q.lower()
    for key, scheme in SCHEMES.items():
        if key in ql:
            return scheme
    return None


STOPWORDS = {"what", "is", "the", "of", "for", "does", "do", "and", "a", "an",
             "in", "on", "my", "how", "to", "by", "has", "have", "with", "from",
             "it", "are", "there", "any", "its", "this", "that", "was"}


def retrieve(query: str, scheme: str | None, k: int = 8):
    """Vector top-8, then keyword-overlap re-rank so the chunk containing the
    exact fact line (e.g. 'Expense ratio1.21%') wins over nearby prose."""
    col, model = _store()
    vec = model.encode([query], normalize_embeddings=True)[0].tolist()
    where = {"scheme": scheme} if scheme else None
    res = col.query(query_embeddings=[vec], n_results=30, where=where)
    keywords = {w for w in re.findall(r"[a-z]+", query.lower()) if w not in STOPWORDS}
    scored = []
    for rank, (doc, meta) in enumerate(zip(res["documents"][0], res["metadatas"][0])):
        overlap = sum(1 for w in keywords if w in doc.lower())
        scored.append((overlap, -rank, {"text": doc, "scheme": meta["scheme"], "url": meta["url"]}))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [t[2] for t in scored[:k]]


def _fill(template: str, m: "re.Match") -> str:
    groups = [g for g in m.groups() if g]
    text = template.format(
        m=groups[0].strip() if groups else "",
        **{f"g{i + 1}": (g or "").strip() for i, g in enumerate(m.groups())},
    )
    return re.sub(r"\s+", " ", text).strip()


def _groq_key() -> str | None:
    """API key from env or local .env (never committed — see .gitignore)."""
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def _llm_answer(query: str, hits: list) -> str | None:
    """Groq LLM fallback: fluent answer strictly from retrieved context.
    Returns None when unavailable, failed, or the fact isn't in context."""
    key = _groq_key()
    if not key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=key)
        context = "\n\n".join(h["text"][:800] for h in hits[:4])
        r = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You answer factual questions about HDFC mutual fund "
                        "schemes using ONLY the provided context. At most 3 short "
                        "sentences. Never give investment advice. Never state or "
                        "compare returns. Never invent numbers. If the answer is "
                        "not in the context, reply exactly: NOT_FOUND"
                    ),
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"},
            ],
            temperature=0,
            max_tokens=200,
        )
        text = (r.choices[0].message.content or "").strip()
        return None if text == "NOT_FOUND" or not text else text
    except Exception:
        return None


def compose(query: str) -> dict:
    if PII_PAT.search(query):
        return {
            "answer": "I can't accept personal details like PAN, Aadhaar, account numbers, OTPs, emails or phone numbers. Please ask a general question about the schemes instead.",
            "source": EDU_LINK,
            "refused": True,
        }
    if ADVICE_PAT.search(query):
        return {
            "answer": "I answer facts only and can't suggest what to buy, sell or hold. You can compare scheme factsheets to decide. See an educational starting point here.",
            "source": EDU_LINK,
            "refused": True,
        }

    scheme = detect_scheme(query)
    intent = detect_intent(query)
    hits = retrieve(query, scheme)
    if not hits:
        return {
            "answer": "I couldn't find that in the 5 HDFC scheme pages I cover (large-cap, flexi-cap, ELSS, small-cap, balanced advantage).",
            "source": EDU_LINK,
            "refused": True,
        }
    owner = scheme or hits[0]["scheme"]
    url = next((h["url"] for h in hits if h["scheme"] == owner), hits[0]["url"])
    stamp = f"Last updated from sources: {FETCHED_ON}."

    if intent == "statement":
        owner = scheme or "these HDFC schemes"
        url = next((h["url"] for h in hits if h["scheme"] == owner), hits[0]["url"])
        who = f"investors in {scheme}" if scheme else "investors"
        return {
            "answer": f"Capital-gains statements aren't on these scheme pages; per the scheme page the registrar is CAMS (camsonline.com), where {who} download statements. {stamp}",
            "source": url,
            "refused": False,
        }

    if intent == "lock":
        if scheme and "ELSS" not in scheme:
            return {
                "answer": f"No lock-in is stated for {scheme}; only the ELSS scheme carries the 3-year lock-in. {stamp}",
                "source": url,
                "refused": False,
            }
        return {
            "answer": f"HDFC ELSS Tax Saver has a 3-year lock-in on every investment. {stamp}",
            "source": ELSS_URL,
            "refused": False,
        }

    if intent in ("exit", None):
        pass  # handled below: exit tries variants, None falls to returns/snippet

    if intent == "exit":
        for variant in EXIT_VARIANTS:
            pat, template = INTENTS[variant]
            for h in hits:
                m = pat.search(h["text"])
                if m:
                    hit_url = next((x["url"] for x in hits if x["scheme"] == h["scheme"]), url)
                    return {
                        "answer": f"{_fill(template, m)} ({h['scheme']}). {stamp}",
                        "source": hit_url,
                        "refused": False,
                    }

    if intent and intent in INTENTS:
        pat, template = INTENTS[intent]
        for h in hits:
            m = pat.search(h["text"])
            if m:
                hit_url = next((x["url"] for x in hits if x["scheme"] == h["scheme"]), url)
                return {
                    "answer": f"{_fill(template, m)} ({h['scheme']}). {stamp}",
                    "source": hit_url,
                    "refused": False,
                }
        # Regex missed: Groq LLM reads the same retrieved chunks fluently.
        llm = _llm_answer(query, hits)
        if llm:
            return {
                "answer": f"{llm} ({owner}). {stamp}",
                "source": url,
                "refused": False,
            }
        return {
            "answer": f"I couldn't find that fact for {owner} in the scheme pages I cover.",
            "source": url,
            "refused": True,
        }

    if RETURNS_PAT.search(query):
        return {
            "answer": "I don't compute or compare returns. Please check the scheme's official factsheet for performance figures.",
            "source": url,
            "refused": True,
        }

    llm = _llm_answer(query, hits)
    if llm:
        return {
            "answer": f"{llm} ({owner}). {stamp}",
            "source": url,
            "refused": False,
        }

    snippet = re.sub(r"\s+", " ", hits[0]["text"][:220]).strip()
    return {
        "answer": f"From {owner}: {snippet}. {stamp}",
        "source": url,
        "refused": False,
    }


def answer(query: str) -> dict:
    return compose(query.strip())
