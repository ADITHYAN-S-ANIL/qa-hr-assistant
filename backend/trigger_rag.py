import requests
import json

# Try to find a valid user and session
payload = {
    "message": "Who is the CEO of QAWebPrints?",
    "session_id": None,
    "use_rag": True
}

# We need an auth token. I'll just use the test script approach again 
# because it bypasses the need for a web request and shows inner logs.

import sys
sys.path.append('c:/Users/Lenovo/Desktop/chat/backend')
from app import invoke_query_reply

print("--- START TEST ---")
result = invoke_query_reply("Who is the CEO of QAWebPrints?")
print(f"RESULT: {result}")
print("--- END TEST ---")
