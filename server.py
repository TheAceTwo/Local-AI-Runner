import os
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5-coder:7b")

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
    # Formatted correctly for Ollama's /api/chat endpoint
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.prompt}
        ],
        "stream": False,
        "options": {
            "num_gpu": 99
        }
    }
    
    # 120 second timeout prevents the frontend from throwing "No response from model"
    timeout = httpx.Timeout(120.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            res_data = response.json()
            
            # Extract content from chat response format
            content = res_data.get("message", {}).get("content", "No response from model.")
            return {"response": content}
            
    except httpx.RequestError as e:
        return {"response": f"Network error communicating with Ollama: {str(e)}"}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)