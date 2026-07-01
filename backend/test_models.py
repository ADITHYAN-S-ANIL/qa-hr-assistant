import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
resp = requests.get(url)
print("--- v1beta Models ---")
if resp.status_code == 200:
    for m in resp.json().get("models", []):
        if "embedContent" in m.get("supportedGenerationMethods", []):
            print(f"{m['name']} supports embedContent")
else:
    print(f"Error {resp.status_code}: {resp.text}")

url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
resp = requests.get(url)
print("\n--- v1 Models ---")
if resp.status_code == 200:
    for m in resp.json().get("models", []):
        if "embedContent" in m.get("supportedGenerationMethods", []):
            print(f"{m['name']} supports embedContent")
else:
    print(f"Error {resp.status_code}: {resp.text}")
