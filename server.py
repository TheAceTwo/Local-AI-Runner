import os
import json
import httpx
import docker
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from tool_parser import parse_and_execute_tools

# Extract dynamic version from container/build environment, defaulting to 'dev' locally
APP_VERSION = os.getenv("APP_VERSION", "dev")

app = FastAPI(title="AI Control Panel", version=APP_VERSION)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5-coder:7b")

SYSTEM_PROMPT = """
You are a Windows OS Automation and File Management Assistant.
FILE ACCESS DIRECTORIES (Mounted Containers):
- Desktop: /user_data/Desktop
- Downloads: /user_data/Downloads
- Documents: /user_data/Documents
- Pictures: /user_data/Pictures
- Videos: /user_data/Videos
- Music: /user_data/Music

CRITICAL INSTRUCTIONS FOR FILE OPERATIONS:
When the user asks you to create, edit, write, read, delete, or list files, DO NOT tell the user how to do it in Windows.
Instead, execute the task directly by returning ONLY a valid raw JSON tool call block in the following format:

{"tool": "write_file", "path": "/user_data/Desktop/filename.txt", "content": "file text content here"}
{"tool": "read_file", "path": "/user_data/Desktop/filename.txt"}
{"tool": "delete_file", "path": "/user_data/Desktop/filename.txt"}
{"tool": "list_files", "path": "/user_data/Desktop"}

Rules:
1. Output NOTHING except the raw JSON tool block when a file action is requested.
2. Ensure path maps to the correct /user_data directory.
3. If no file path extension is specified by the user, default to .txt or .ps1 as context dictates.
"""

class ChatRequest(BaseModel):
    message: str | None = None
    prompt: str | None = None

@app.get("/api/version")
async def get_version():
    """Returns the container version injected by GitHub / Docker builds."""
    return {"version": APP_VERSION}

@app.post("/api/chat")
async def chat(req: ChatRequest):
    user_message = req.message or req.prompt or ""
    if not user_message:
        return {"error": "No message provided."}

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ],
        "stream": False,
        "options": {"num_gpu": 99}
    }
    
    timeout = httpx.Timeout(120.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(OLLAMA_URL, json=payload)
            response.raise_for_status()
            res_data = response.json()
            
            raw_content = res_data.get("message", {}).get("content", "").strip()
            
            # Delegates all JSON parsing (raw or markdown block) directly to tool_parser.py
            cleaned_response = parse_and_execute_tools(raw_content)

            return {
                "response": cleaned_response,
                "metrics": {
                    "eval_count": res_data.get("eval_count", 0),
                    "prompt_eval_count": res_data.get("prompt_eval_count", 0)
                }
            }
    except httpx.RequestError as e:
        return {"error": f"Network connection error: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stats")
async def get_container_stats():
    try:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        containers = client.containers.list()
        stats_list = []

        for container in containers:
            stat = container.stats(stream=False)
            cpu_delta = stat['cpu_stats']['cpu_usage']['total_usage'] - stat['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stat['cpu_stats']['system_cpu_usage'] - stat['precpu_stats']['system_cpu_usage']
            number_cpus = stat['cpu_stats'].get('online_cpus', len(stat['cpu_stats']['cpu_usage'].get('percpu_usage', [1])))
            
            cpu_percent = 0.0
            if system_delta > 0.0 and cpu_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * number_cpus * 100.0

            mem_usage_bytes = stat['memory_stats'].get('usage', 0)
            mem_mb = round(mem_usage_bytes / (1024 * 1024), 2)
            
            stats_list.append({
                "name": container.name,
                "cpu_percent": round(cpu_percent, 2),
                "memory_mb": mem_mb
            })

        return {"status": "success", "containers": stats_list}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)