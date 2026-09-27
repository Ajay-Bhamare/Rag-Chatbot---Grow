from answer import answer

qs = [
    "What is the expense ratio of HDFC ELSS Tax Saver?",
    "What is the exit load of HDFC Large Cap?",
    "What is the minimum SIP for HDFC Balanced Advantage?",
    "Does HDFC Small Cap have a lock-in?",
    "What is the benchmark of HDFC Flexi Cap?",
    "What is the riskometer of HDFC Large Cap?",
    "Should I buy HDFC Small Cap?",
    "Which fund is better, large cap or flexi cap?",
    "What are the 3Y returns of HDFC Flexi Cap?",
    "My PAN is ABCDE1234F, what is my tax?",
    "How do I download my capital gains statement?",
]
for q in qs:
    d = answer(q)
    print("Q:", q)
    print("A:", d["answer"])
    print("S:", d["source"])
    print("-" * 60)
