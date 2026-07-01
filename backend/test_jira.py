import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import invoke_query_reply

print("Testing Query: 'who is working on jira ticket 143'")
result = invoke_query_reply("who is working on jira ticket 143", user_id=1, user_role='ceo')
print("-" * 40)
print(result)
print("-" * 40)

print("Testing Query: 'status of ticket 101'")
result2 = invoke_query_reply("status of ticket 101", user_id=1, user_role='ceo')
print("-" * 40)
print(result2)
print("-" * 40)
