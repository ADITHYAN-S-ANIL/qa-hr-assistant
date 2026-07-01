import app

CEO_QUERIES = [
    # Dashboard
    "employee count",
    "what happened today in the company",
    "give me a company summary",
    "dashboard",
    # Employees
    "list employees",
    "who are our employees",
    # Tasks
    "list all tasks",
    "show pending tasks",
    # Leaves
    "list leave requests",
    "show pending leave requests",
    # Performance
    "who is not working today",
    "performance report",
    # General
    "what is the company name",
    "company name",
    # Free-form
    "hi",
    "how many managers do we have",
]

print("=" * 60)
print("COMPREHENSIVE CEO CHATBOT TEST")
print("=" * 60)
for q in CEO_QUERIES:
    print(f"\n>>> CEO asks: '{q}'")
    try:
        result = app.invoke_query_reply(q, user_role="ceo", user_id=1)
        # Truncate long responses
        if len(result) > 300:
            print(result[:300] + "... [truncated]")
        else:
            print(result)
    except Exception as e:
        print(f"ERROR: {e}")
    print("-" * 40)
