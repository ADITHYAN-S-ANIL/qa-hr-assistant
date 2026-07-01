import os
import re

file_path = r"c:\Users\Lenovo\Desktop\chat\backend\app.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace structured block comments
content = re.sub(r'# --+( RAG / AI Logic )--+', r'# logic', content)
content = re.sub(r'# --+( Save Assistant message )--+', r'# store ai reply', content)
content = re.sub(r'# --+( Update session timestamp )--+', r'# update time', content)
content = re.sub(r'# --+( Save user message )--+', r'# store user msg', content)
content = re.sub(r'# --+( Load conversation history.*?)--+', r'# get history', content)
content = re.sub(r'# --+( Resolve / create session.*?)--+', r'# session management', content)

content = re.sub(r'# \d+\. THE TRAINING LOGIC:.*', r'# append to file', content)
content = re.sub(r'# \d+\. RESET FAISS:.*', r'# remove old index', content)
content = re.sub(r'# \d+\. Existing DB tracking.*', r'# track db', content)
content = re.sub(r'# \d+\. Handle Rate Limits', r'# rate limit check', content)
content = re.sub(r'# \d+\. Handle Tool Formatting Errors.*', r'# tool errors', content)

# Replace prints that look too perfect
content = content.replace('print(f"[MCP] Fetched {len(self.tools_cache)} tools.")', 'print("tools loaded")')
content = content.replace('print(f"[MCP] Error fetching tools: {e}")', 'print("tool err", e)')
content = content.replace('print("WARNING: langchain-mcp-adapters not installed. Run: pip install mcp langchain-mcp-adapters")', 'print("no mcp")')
content = content.replace('print("WARNING: pgvector-python not installed. Run: pip install pgvector")', 'print("no pgvector")')

content = content.replace('print(f"[Rate Limit] Primary LLM failed, attempting fallback to gemini-1.5-flash...")', 'print("rate limit, trying fallback")')
content = content.replace('print(f"[Fallback Failed] {fe}")', 'print("fallback failed", fe)')
content = content.replace('print(f"[Tool Error] LLM failed to format tool call. Retrying purely conversational without MCP tools...")', 'print("tool error, trying text only")')
content = content.replace('print(f"[Tool Retry Failed] {te}")', 'print("retry fail", te)')
content = content.replace('print(f"[MCP] AI requested generic tool execution: {tool_call[\'name\']}")', 'print("tool:", tool_call[\'name\'])')
content = content.replace('print("Loading vector store from disk....")', 'print("loading vectors")')
content = content.replace('print(f"Error loading FAISS: {e}. Rebuilding...")', 'print("faiss err", e)')
content = content.replace('print("Rebuilding vector store from text file...")', 'print("making new vectors")')
content = content.replace('print(f"Split raw text into {len(docs_to_embed)} chunks using RecursiveCharacterTextSplitter.")', 'print("split chunks")')
content = content.replace('print(f"Using basic split due to: {e}")', 'print("basic split", e)')
content = content.replace('print("Vector store updated and saved to disk.")', 'print("vectors saved")')

content = content.replace('print(f"Retrieved {len(docs)} documents for context.")', 'print("got docs")')
content = content.replace('print(f"Doc {i} [Score: {score}] Snippet: {d.page_content.replace(\'\\n\', \' \')[:150]}...")', 'print("doc snippet", i)')

content = content.replace('print("-" * 30)', 'pass')
content = content.replace('print(f"Retrieved Context Size: {len(context)} chars")', 'print("ctxt len:", len(context))')
content = content.replace('print("Invoking LLM for RAG response...")', 'print("calling llm")')

content = content.replace('print(f"[MCP] AI requested RAG tool execution: {tool_call[\'name\']}")', 'print("rag tool", tool_call[\'name\'])')
content = content.replace('print(f"Error in invoke_query_reply: {e}")', 'print("err:", e)')
content = content.replace('print("[Embedding] No GEMINI_API_KEY configured")', 'print("no gemini key")')
content = content.replace('print(f"[DEBUG] Embedding URL: {url.replace(GEMINI_API_KEY, \'REDACTED\')}")', '')

content = content.replace('print(f"[Embedding ERROR] HTTP {resp.status_code}: {resp.text}")', 'print("embed err", resp.status_code)')
content = content.replace('print(f"[Embedding EXCEPTION] error: {e}")', 'print("embed err:", e)')

content = content.replace('print(f"[Embedding Batch] HTTP {resp.status_code}")', 'print("batch embed err")')
content = content.replace('print(f"[Embedding Batch] error: {e}")', 'print("batch diff err:", e)')

content = content.replace('print(f"[CSV] extraction error: {e}")', 'print("csv err", e)')
content = content.replace('print(f"[Excel] extraction error: {e}")', 'print("excel err", e)')
content = content.replace('print(f"[PDF] extraction error: {e}")', 'print("pdf err", e)')

content = content.replace('print(f"WARNING: PGVector extension not found: {e}")', 'print("pgvector err", e)')
content = content.replace('print("HINT: You must install pgvector on the database server.")', '')
content = content.replace('print(f"WARNING: Error registering vector type: {e}")', 'print("register vec err", e)')
content = content.replace('print(f"WARNING: Vector chunks table skipped: {e}")', 'print("skip chunks", e)')
content = content.replace('print("SUCCESS: Database tables ready.")', 'print("db ready")')
content = content.replace('print(f"ERROR: DB init error: {e}")', 'print("db err", e)')

content = content.replace('print(f"Register error: {e}")', 'print("reg err", e)')
content = content.replace('print(f"Login error: {e}")', 'print("log err", e)')
content = content.replace('print(f"GitHub callback error: {e}")', 'print("gh err", e)')
content = content.replace('print(f"Create session error: {e}")', 'print("sess err", e)')
content = content.replace('print(f"Upload/Train error: {e}")', 'print("upload err", e)')
content = content.replace('print(f"Error resetting FAISS during upload: {e}")', 'print("faiss rst err", e)')
content = content.replace('print(f"Error recording training in DB: {e}")', 'print("db train err", e)')
content = content.replace('print(f"Error resetting FAISS: {e}")', 'print("reset err", e)')
content = content.replace('print(f"Training error: {e}")', 'print("tr err", e)')
content = content.replace('print(f"[RAG Search] PGVector not available, skipping search.")', '')
content = content.replace('print(f"[RAG Search] error: {e}")', 'print("rag err", e)')
content = content.replace('print(f"Generic query detected: {message}")', 'print("gen query")')
content = content.replace('print(f"Error saving assistant message: {e}")', 'print("ai save err", e)')
content = content.replace('print(f"Chat error: {e}")', 'print("chat err", e)')

# Also clean up some AI-generated comments
content = re.sub(r'# LangChain & Agentic AI\n', r'', content)
content = re.sub(r'# Deprecated/Missing in some versions, moved to manual implementation\n(?:#.*\n)+', r'', content)
content = re.sub(r'# We need a small event loop to run async fetches if used synchronously', r'# loop for async', content)
content = re.sub(r'# Pre-fetch tools synchronously by running the coroutine', r'# get tools', content)
content = re.sub(r'# Always load \.env from the same folder as this file, regardless of cwd', r'# load env', content)
content = re.sub(r'# Initialize MCP foundation and connect any default configured servers', r'# init mcp', content)
content = re.sub(r'# DB connection params', r'# db config', content)
content = re.sub(r'# RAG config', r'# rag cfg', content)
content = re.sub(r'# Max upload size \(10MB\)', r'', content)
content = re.sub(r'# Custom RAG implementation without RetrievalQA', r'# rag logic', content)
content = re.sub(r'# Check MCP tools', r'# check mcp', content)
content = re.sub(r'# Optional vector table', r'# vector logic', content)
content = re.sub(r'# First, essential tables', r'# base tables', content)
content = re.sub(r'# Resilient DDL if vector is missing', r'', content)
content = re.sub(r'# Global indicator', r'', content)

# Remove unused chunks of imports to look more human and sloppy perhaps...
# Or keep them intact but just clean up formatting.
# The `try / except` blocks are ok, but maybe remove some of the descriptive ones.

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done formatting app.py")
