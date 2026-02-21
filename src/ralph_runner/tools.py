"""Tool-call description formatting for the live display."""

from __future__ import annotations


def tool_description(name: str, inp: dict) -> str:
    """Create a compact, readable description of a tool call."""
    if name == "Task":
        desc = inp.get("description", "")
        return f"Agent: {desc}" if desc else "Agent"
    if name == "Read":
        path = inp.get("file_path", "")
        return f"Read {path.split('/')[-1]}" if path else "Read"
    if name == "Bash":
        cmd = inp.get("command", "")
        return f"$ {cmd[:60]}" if cmd else "Bash"
    if name in ("Grep", "mcp__plugin_meta_mux__search_files"):
        pattern = inp.get("pattern", "")
        return f"Search: {pattern[:50]}" if pattern else "Search"
    if name == "Glob":
        pattern = inp.get("pattern", "")
        return f"Glob: {pattern}" if pattern else "Glob"
    if name == "Edit":
        path = inp.get("file_path", "")
        return f"Edit {path.split('/')[-1]}" if path else "Edit"
    if name == "Write":
        path = inp.get("file_path", "")
        return f"Write {path.split('/')[-1]}" if path else "Write"
    if name == "WebFetch":
        url = inp.get("url", "")
        return f"Fetch: {url[:50]}" if url else "WebFetch"
    # Generic fallback — strip common MCP prefixes
    short_name = name.replace("mcp__plugin_meta_mux__", "").replace("mcp__", "")
    return short_name
