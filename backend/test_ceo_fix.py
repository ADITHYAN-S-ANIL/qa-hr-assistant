import app

# Only test the previously-failing query + a few others
tests = [
    "how many managers do we have",
    "how many users",
    "employee count",
    "total managers",
    "how many people are registered",
]

print("=== CEO FIX VERIFICATION ===")
for q in tests:
    print(f"\n>>> '{q}'")
    result = app.invoke_query_reply(q, user_role="ceo", user_id=1)
    print(result)
    print("-" * 40)
