import app

queries = [
    "employee count",
    "how many managers do we have",
    "list employees",
    "what happened today",
    "show all tasks",
    "who applied for leave",
    "hi",
    "who is working on pending tickets",
    "give me a company summary",
    "company name",
]

print("=" * 60)
print("TESTING: Ollama-only, no keywords, no API keys")
print("=" * 60)
for q in queries:
    print(f"\n>>> CEO asks: '{q}'")
    try:
        result = app.invoke_query_reply(q, user_role="ceo", user_id=1)
        print(result[:400] if len(result) > 400 else result)
    except Exception as e:
        print(f"ERROR: {e}")
    print("-" * 50)
