import app

print("=== FINAL TEST: No keywords, no API, just Ollama + Live DB ===\n")

queries = [
    ("employee count", "ceo"),
    ("how many managers do we have", "ceo"),
    ("show all tasks", "ceo"),
    ("who applied for leave", "ceo"),
    ("give me a company summary", "ceo"),
    ("hi", "ceo"),
]

for q, role in queries:
    print(f">>> {role.upper()} asks: '{q}'")
    result = app.invoke_query_reply(q, user_role=role, user_id=1)
    print(result[:300] if len(result) > 300 else result)
    print("-" * 50)
