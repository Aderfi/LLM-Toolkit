import json
import sys
import urllib.request

from llmtools import REGISTRY, call_tool, config, get_schemas


def call_ollama(payload):
    req = urllib.request.Request(
        config.OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    if len(sys.argv) < 2:
        print('Usage: python agent.py "your prompt"')
        sys.exit(1)
    query = " ".join(sys.argv[1:])
    print(f"\n[SYSTEM] {len(REGISTRY)} tools loaded.\n[PROMPT] {query}\n")

    messages = [{"role": "user", "content": query}]
    payload = {"model": config.MODEL, "messages": messages, "tools": get_schemas(), "stream": False}
    try:
        resp = call_ollama(payload)
    except Exception as e:
        print(f"[ERROR] Ollama call failed: {e}\nIs Ollama running with {config.MODEL} pulled?")
        return

    msg = resp.get("message", {})
    if msg.get("tool_calls"):
        messages.append(msg)
        print("[TOOL EXECUTION]")
        for tc in msg["tool_calls"]:
            name = tc["function"]["name"]
            args = tc["function"]["arguments"]
            print(f"  └── {name}({args})")
            result = call_tool(name, args)
            print(f"      → {str(result)[:200]}")
            messages.append({"role": "tool", "name": name, "content": str(result)})
        payload["messages"] = messages
        resp = call_ollama(payload)
        print("\n[RESPONSE]\n" + resp.get("message", {}).get("content", ""))
    else:
        print("[RESPONSE]\n" + msg.get("content", ""))


if __name__ == "__main__":
    main()
