import requests
import json

BASE_URL = "http://localhost:5000"

def test_chat():
    # We need a token. Let's try to login as the user first if possible, 
    # but we don't know passwords.
    # Alternatively, we can just call invoke_query_reply directly if we were in the same process, 
    # but we are not.
    
    # Let's try to find a user in the DB and generate a token manually, 
    # or just look for a valid token in the logs if any.
    
    # Actually, I can just create a test script that imports app and calls the function.
    import sys
    sys.path.append('c:/Users/Lenovo/Desktop/chat/backend')
    from app import invoke_query_reply
    
    print("Testing RAG query...")
    response = invoke_query_reply("workers at qawebprint")
    print("-" * 20)
    print(f"Response: {response}")
    print("-" * 20)

if __name__ == "__main__":
    test_chat()
