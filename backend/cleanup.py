import re
import os

filepath = "app.py"

with open(filepath, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Remove big AI-style section headers
text = re.sub(r'# -{10,}.*?-{10,}\n', '', text)

# 2. Remove single-line docstrings (common AI signature)
text = re.sub(r'^\s*"""[^"]+"""\n', '', text, flags=re.MULTILINE)

# 3. Remove flush=True from print statements (makes it look less robotic)
text = text.replace(', flush=True', '')

# 4. Remove overly verbose AI "fallback" and "helper" comments
text = re.sub(r'# Fallback to original.*?LangChain LLM.*?Tools\.\n', '', text)
text = re.sub(r'# Safely invoke LLM with fallback for rate limits.*?Binding\.\n', '', text)
text = re.sub(r'# 1\. Base System Personality\n', '', text)
text = re.sub(r'# 2\. Add Recent History \(last 10 turns to avoid context drowning\)\n', '', text)
text = re.sub(r'# 3\. Add Context and Current Question as a FINAL authoritative block\n', '', text)
text = re.sub(r'# Check if index file is newer than the saved vector store\n', '', text)
text = re.sub(r'# FAISS save_local creates files like index\.faiss inside the directory\n', '', text)
text = re.sub(r'# Better splitting: Use RecursiveCharacterTextSplitter if available, else fallback\n', '', text)
text = re.sub(r'# Create embeddings and vector store\n', '', text)
text = re.sub(r'# Extract text from uploaded file based on extension\.\n', '', text)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(text)

print("Cleaned up AI signatures from app.py")
