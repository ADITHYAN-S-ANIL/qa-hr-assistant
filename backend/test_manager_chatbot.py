import sys
import os

sys.path.append('c:/Users/Lenovo/Desktop/chat/backend')
from app import invoke_query_reply

def test_queries():
    manager_id = 15 # manager@test.com
    
    queries = [
        "Give me a dashboard summary.",
        "Give me a team metrics dashboard",
        "What tasks were completed by employee@test.com today?",
        "What is the leave status of employee@test.com?",
        "is anyone slacking off today?",
        "did anyone complete their work?",
        "what did anyone do today?",
        "is anyone on leave?",
        "show all tasks",
        "status of anyone",
        "task update",
        "list all the employee",
        "list all the task completed",
        "status of employee",
        "Who is absent today?",
        "Who is present today?",
        "Leave balance of employee@test.com",
        "How many leaves are remaining for employee 16?",
        "Show employee productivity.",
        "Show work progress.",
        "List all tasks completed by employee 16.",
        "Who is free?",
        "Who is not working properly?",
        "Which employees are overloaded?",
        "What are employees doing right now?",
        "any leave updates"
    ]
    
    for q in queries:
        print("\n" + "="*50)
        print(f"QUERY: {q}")
        print("="*50)
        try:
            response = invoke_query_reply(q, history=[], user_id=manager_id, chat_mode='general', user_role='manager')
            print(f"RESPONSE:\n{response}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_queries()
