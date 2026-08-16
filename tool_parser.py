import os
import json
import re
from pathlib import Path

def execute_tool_dict(data: dict) -> str:
    """Executes supported file system tools and returns a status string."""
    tool = data.get("tool")
    path_str = data.get("path", "")

    # Path Safety Guard matching server system prompt
    if not path_str.startswith("/user_data"):
        return "⚠️ **Error:** Path access restricted outside of mounted `/user_data` volumes."

    filepath = Path(path_str)

    try:
        if tool == "write_file":
            content = data.get("content", "")
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            return f"✅ **File Written:** `{filepath}`"

        elif tool == "read_file":
            if not filepath.exists():
                return f"⚠️ **Error:** File at `{filepath}` does not exist."
            content = filepath.read_text(encoding="utf-8")
            return f"📄 **File Content of `{filepath}`:**\n\n```text\n{content}\n```"

        elif tool == "delete_file":
            if filepath.exists():
                filepath.unlink()
                return f"🗑️ **File Deleted:** `{filepath}`"
            return f"⚠️ **Error:** File at `{filepath}` does not exist."

        elif tool == "list_files":
            if filepath.exists() and filepath.is_dir():
                items = os.listdir(filepath)
                formatted_list = "\n".join([f"- {item}" for item in items])
                return f"📂 **Directory Contents of `{filepath}`:**\n{formatted_list}"
            return f"⚠️ **Error:** Directory at `{filepath}` does not exist."

        else:
            return f"⚠️ **Error:** Unknown tool `{tool}`"

    except Exception as e:
        return f"⚠️ **Execution Failed:** {str(e)}"

def parse_and_execute_tools(response_text: str) -> str:
    """Detects raw or markdown-wrapped JSON tool calls and replaces them with execution results."""
    text = response_text.strip()

    # 1. Handle Raw JSON Responses (Single or Multi-line)
    if text.startswith("{") and text.endswith("}"):
        try:
            data = json.loads(text)
            if "tool" in data:
                return execute_tool_dict(data)
        except json.JSONDecodeError:
            pass

    # 2. Handle Markdown Code Blocks (```json ... ```)
    pattern = r"```(?:json)?\s*(\{\s*\"tool\".*?\})\s*```"
    matches = re.finditer(pattern, response_text, re.DOTALL)
    
    updated_text = response_text
    for match in matches:
        full_block = match.group(0)
        json_str = match.group(1)
        try:
            data = json.loads(json_str)
            if "tool" in data:
                result = execute_tool_dict(data)
                updated_text = updated_text.replace(full_block, result)
        except json.JSONDecodeError:
            continue

    return updated_text