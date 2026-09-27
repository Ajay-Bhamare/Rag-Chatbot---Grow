"""Tiny UI: welcome line + 3 example questions + facts-only disclaimer."""
from flask import Flask, jsonify, request

from answer import answer

app = Flask(__name__)

DISCLAIMER = "Facts-only assistant. No investment advice. Answers come only from the 5 public HDFC scheme pages listed in sources."

EXAMPLES = [
    "What is the expense ratio of HDFC ELSS Tax Saver?",
    "Does HDFC Small Cap have a lock-in?",
    "What is the minimum SIP for HDFC Balanced Advantage?",
]

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HDFC Mutual Fund FAQ Assistant</title>
<style>body{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px}
.note{background:#f4f4f4;border-left:4px solid #2b7a3d;padding:10px 14px;margin:16px 0}
.ex button{margin:4px 8px 4px 0;padding:8px 12px;cursor:pointer}
#out{border:1px solid #ddd;border-radius:8px;padding:14px;margin-top:16px;white-space:pre-wrap}
form{display:flex;gap:8px}input{flex:1;padding:10px}button{padding:10px 16px}</style>
</head><body>
<h2>HDFC Mutual Fund FAQ Assistant</h2>
<p>Ask facts about 5 HDFC schemes: large-cap, flexi-cap, ELSS, small-cap, balanced advantage.</p>
<div class="ex"><b>Try:</b><br>
<button onclick="ask(this.innerText)">What is the expense ratio of HDFC ELSS Tax Saver?</button>
<button onclick="ask(this.innerText)">Does HDFC Small Cap have a lock-in?</button>
<button onclick="ask(this.innerText)">What is the minimum SIP for HDFC Balanced Advantage?</button>
</div>
<form onsubmit="ask(document.getElementById('q').value);return false">
<input id="q" placeholder="e.g. Exit load of HDFC Large Cap?" autocomplete="off">
<button>Ask</button></form>
<div id="out">Welcome! Ask a factual question.</div>
<div class="note">DISCLAIMER</div>
<script>async function ask(q){document.getElementById('q').value=q;
const o=document.getElementById('out');o.textContent='…';
const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({q})});
const d=await r.json();o.innerHTML='';o.append(d.answer+'\\n');
const a=document.createElement('a');a.href=d.source;a.textContent='Source';a.target='_blank';o.append(a);}</script>
</body></html>""".replace("DISCLAIMER", DISCLAIMER)


@app.get("/")
def home():
    return PAGE


@app.post("/ask")
def ask():
    q = (request.get_json(force=True) or {}).get("q", "")
    if not q.strip():
        return jsonify({"answer": "Please type a question.", "source": "https://groww.in/mutual-funds"})
    d = answer(q)
    return jsonify({"answer": d["answer"], "source": d["source"]})


if __name__ == "__main__":
    import os

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
