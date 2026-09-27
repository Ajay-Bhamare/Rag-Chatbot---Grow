"""Groww-style chat UI: header, scheme pills, bubbles, examples, disclaimer."""
from flask import Flask, jsonify, render_template, request

from answer import answer

app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


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
