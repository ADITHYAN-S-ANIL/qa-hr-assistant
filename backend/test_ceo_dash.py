import app

print("=== Testing as CEO ===")
print(app.invoke_query_reply("employee count", user_role="ceo", user_id=1))
print()
print("=== Testing dashboard as CEO ===")
print(app.invoke_query_reply("what happened today in the company", user_role="ceo", user_id=1))
print()
print("=== Testing employee count as employee (should be restricted) ===")
print(app.invoke_query_reply("employee count", user_role="employee", user_id=5))
