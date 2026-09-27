"""STAGE 1 - LOADING: fetch the 5 public Groww scheme pages, extract clean text.

Saves data/raw.json: [{scheme, category, url, text, fetched_at}]
Public sources only. No login, no back-end, no screenshots.
"""
import csv
import json
import re
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
HEADERS = {"User-Agent": "Mozilla/5.0 (MF-FAQ-RAG educational prototype)"}


def clean_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # collapse whitespace, drop empty lines
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    text = "\n".join(lines)
    # cut site-nav header: start at the fund title ("HDFC … Direct Growth…")
    m = re.search(r"HDFC .*? Direct (?:Plan )?Growth", text)
    if m:
        text = text[m.start() :]
    # cut link-farm footer (registrar/CAMS info sits above this marker)
    i = text.find("Contact UsDownload the App")
    if i >= 0:
        text = text[:i]
    return text


def main() -> None:
    docs = []
    with open(BASE / "sources.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            print(f"fetching {row['scheme']} ...")
            r = requests.get(row["url"], headers=HEADERS, timeout=40)
            r.raise_for_status()
            docs.append(
                {
                    "scheme": row["scheme"],
                    "category": row["category"],
                    "url": row["url"],
                    "text": clean_text(r.text),
                    "fetched_at": date.today().isoformat(),
                }
            )
    out = BASE / "data" / "raw.json"
    out.write_text(json.dumps(docs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"saved {len(docs)} pages -> {out}")


if __name__ == "__main__":
    main()
