import json
import re
from pathlib import Path

def parse_and_execute_tools(response_text: str) -> str:
    pattern = r"```json\s*(\{\s*\"tool\"\s*:\s*\"write_file\".*?\})\s*```"
    matches = re.findall(pattern, response_text, re.DOTALL)
    
    if not matches:
        return response_text

    updated_text = response_text
    for json_str in matches:
        try:
            data = json.loads(json_str)
            if data.get("tool") == "write_file":
                filepath = Path(data["path"]).expanduser().resolve()
                content = data["content"]
                
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_text(content, encoding="utf-8")
                
                status_block = f"✅ **File Written:** `{filepath}`"
                updated_text = updated_text.replace(f"```json\n{json_str}\n```", status_block)
                updated_text = updated_text.replace(f"```json{json_str}```", status_block)
        except Exception as e:
            updated_text += f"\n\n⚠️ **File Execution Failed:** {str(e)}"

    return updated_text