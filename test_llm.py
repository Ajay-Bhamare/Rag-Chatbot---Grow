import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from answer import answer

qs = [
    "Who manages HDFC ELSS Tax Saver?",
    "What is the AUM of HDFC Small Cap?",
    "What is the investment objective of HDFC Flexi Cap?",
    "What is the expense ratio of HDFC Balanced Advantage?",
    "Should I invest in HDFC ELSS for tax saving?",
]
for q in qs:
    d = answer(q)
    print("Q:", q)
    print("A:", d["answer"])
    print("S:", d["source"])
    print("-" * 60)
