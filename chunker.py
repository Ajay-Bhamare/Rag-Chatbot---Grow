"""STAGE 2 - CHUNKING.

Chunking-strategy decision (data-driven, as briefed):
  The 5 pages are semi-structured fact sheets: one fact per line/table row
  ("Expense ratio 1.03%", "Exit load of 1% if redeemed within 1 year",
  "Min. for SIP Rs.100"). Facts are atomic and short.

  Chosen: RECURSIVE character splitting (paragraph -> line -> sentence ->
  word), chunk_size ~600 chars, overlap ~120 chars.
  Why not semantic chunking: facts here don't span sentences, so embedding
  whole "topics" would merge unrelated facts into one vector and blur
  retrieval. Recursive is deterministic, cheap (no extra model pass), and
  the overlap keeps a fact together with its scheme context.
  Why not fixed-size: a fixed window can slice "Exit load of 1% if redeemed"
  / "within 1 year" across two chunks; recursive prefers line/sentence
  boundaries so each fact survives intact.

  Extra steps: (a) every chunk is prefixed with "[scheme | category]" so a
  retrieved vector always carries its attribution; (b) exact-duplicate
  chunks (site nav/footer boilerplate repeated on all 5 pages) are dropped.

Saves data/chunks.json: [{id, text, scheme, category, url}]
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
CHUNK_SIZE = 600
OVERLAP = 120
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def split_recursive(text: str) -> list[str]:
    """Minimal recursive splitter: try each separator in order."""
    def _split(t: str, seps: list[str]) -> list[str]:
        if len(t) <= CHUNK_SIZE:
            return [t] if t.strip() else []
        sep = next((s for s in seps if s and s in t), "")
        parts = t.split(sep) if sep else list(t)
        chunks, cur = [], ""
        for p in parts:
            piece = p if sep in ("", "\n", "\n\n") else p + sep
            if len(cur) + len(piece) <= CHUNK_SIZE:
                cur += piece
            else:
                if cur.strip():
                    chunks.append(cur.strip())
                # overlap: carry the tail of the previous chunk forward
                cur = (cur[-OVERLAP:] if len(cur) > OVERLAP else "") + piece
                if len(cur) > CHUNK_SIZE:  # single oversized piece: hard cut
                    chunks.extend(
                        cur[i : i + CHUNK_SIZE].strip()
                        for i in range(0, len(cur), CHUNK_SIZE)
                        if cur[i : i + CHUNK_SIZE].strip()
                    )
                    cur = ""
        if cur.strip():
            chunks.append(cur.strip())
        # recurse into any chunk still oversized with the next separator
        out = []
        for c in chunks:
            if len(c) > CHUNK_SIZE and len(seps) > 1:
                out.extend(_split(c, seps[1:]))
            else:
                out.append(c)
        return [c for c in out if c.strip()]

    return _split(re.sub(r"[ \t]+", " ", text), SEPARATORS)


def strip_noise(text: str) -> str:
    """Remove sections that must never enter the answer corpus:
    historical exit-load tables, holdings lists, return/calculator tables
    (brief: no performance claims, no return comparisons)."""
    text = re.sub(
        r"\d{2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\s*Exit load[^.]*\.?",
        " ",
        text,
    )
    text = re.sub(r"Holdings\s*\(\s*\d+\s*\).*?See All", " ", text, flags=re.S)
    text = re.sub(r"Returns and rankings.*?Understand terms", "Understand terms", text, flags=re.S)
    text = re.sub(r"Return calculator.*?Historic returnsReturns", " ", text, flags=re.S)
    text = re.sub(r"Check past dataCompare similar funds.*?Compare Fund management", " ", text, flags=re.S)
    return text


def main() -> None:
    raw = json.loads((BASE / "data" / "raw.json").read_text(encoding="utf-8"))
    chunks, seen = [], set()
    for doc in raw:
        for i, c in enumerate(split_recursive(strip_noise(doc["text"]))):
            norm = re.sub(r"\s+", " ", c).strip()
            if len(norm) < 40 or norm in seen:
                continue  # drop stubs + cross-page boilerplate dupes
            seen.add(norm)
            chunks.append(
                {
                    "id": f"{doc['category']}-{i}",
                    "text": f"[{doc['scheme']} | {doc['category']}] {norm}",
                    "scheme": doc["scheme"],
                    "category": doc["category"],
                    "url": doc["url"],
                }
            )
    out = BASE / "data" / "chunks.json"
    out.write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chunks)} chunks -> {out}")


if __name__ == "__main__":
    main()
