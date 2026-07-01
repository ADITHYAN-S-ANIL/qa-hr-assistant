import json
import os

log_path = r"C:\Users\Lenovo\.gemini\antigravity-ide\brain\8607115a-8a62-4358-8285-34ec45ff1659\.system_generated\logs\transcript.jsonl"

steps = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            data = json.loads(line)
            steps.append(data.get("step_index"))
        except Exception:
            pass

print("Number of lines/steps parsed:", len(steps))
if steps:
    print("Min step_index:", min(steps))
    print("Max step_index:", max(steps))
    # print first 10 steps
    print("First 10 steps:", steps[:10])
    # print last 10 steps
    print("Last 10 steps:", steps[-10:])
