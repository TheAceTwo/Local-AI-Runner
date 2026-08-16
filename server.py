import os
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen2.5-coder:7b"  # Or llama3.1:8b

# SYSTEM SAFETY PROFILE RULES
SYSTEM_PROMPT = """
You are a Windows OS Automation Assistant.
CRITICAL SAFETY BOUNDARIES:
1. NEVER modify, stop, or restart active Docker containers, game servers, or media servers.
2. NEVER run destructive file deletion (rmdir, Remove-Item -Recurse) outside C:\\AI_Playground.
3. If an action risks breaking system networking or core services, reject it and explain why.
4. When asked to generate PowerShell or Python scripts, present the script clearly and explain what it does.
"""

class ChatRequest(BaseModel):
    prompt: str

@app.post("/api/chat")
async def chat(req: ChatRequest):
    payload = {
        "model": MODEL_NAME,
        "prompt": req.prompt,
        "system": SYSTEM_PROMPT,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload)
        res_data = response.json()
        return {"response": res_data.get("response", "No response from model.")}
    except Exception as e:
        return {"response": f"Error communicating with Ollama: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=7860)