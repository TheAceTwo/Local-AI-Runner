import os
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import docker

app = FastAPI()

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434/api/chat")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5-coder:7b")

SYSTEM_PROMPT = """
You are a Windows OS Automation and File Management Assistant.
FILE ACCESS DIRECTORIES:
- Desktop: /user_data/Desktop
- Downloads: /user_data/Downloads
- Documents: /user_data/Documents
- Pictures: /user_data/Pictures
- Videos: /user_data/Videos
- Music: /user_data/Music

CRITICAL SAFETY BOUNDARIES:
1. NEVER modify, stop, or restart active Docker containers, game servers, or media servers unless explicitly commanded.
2. Exercise extreme care when running destructive deletion commands inside /user_data folders.
3. Always verify file paths before removing or modifying user files.
"""

class ChatRequest(BaseModel):
    prompt: str

@app.post("/api/chat")
async def chat(req: ChatRequest):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.prompt}
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
            
            content = res_data.get("message", {}).get("content", "No response generated.")
            return {
                "response": content,
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
    """Fetch live CPU % and Memory Usage from Docker socket."""
    try:
        client = docker.DockerClient(base_url='unix://var/run/docker.sock')
        containers = client.containers.list()
        stats_list = []

        for container in containers:
            # Stream=False fetches a single stats snapshot
            stat = container.stats(stream=False)
            
            # CPU % Calculation
            cpu_delta = stat['cpu_stats']['cpu_usage']['total_usage'] - stat['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stat['cpu_stats']['system_cpu_usage'] - stat['precpu_stats']['system_cpu_usage']
            number_cpus = stat['cpu_stats'].get('online_cpus', len(stat['cpu_stats']['cpu_usage'].get('percpu_usage', [1])))
            
            cpu_percent = 0.0
            if system_delta > 0.0 and cpu_delta > 0.0:
                cpu_percent = (cpu_delta / system_delta) * number_cpus * 100.0

            # Memory Usage Calculation (in MB)
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