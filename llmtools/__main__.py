"""Universal CLI so tools are usable outside agent.py.

    python -m llmtools list                       # list tools (+ schema JSON)
    python -m llmtools call <name> '<json args>'  # run one tool, print result
    python -m llmtools chat "<prompt>"            # interactive agent loop (autonomous)
"""
import json
import sys

from llmtools import REGISTRY, call_tool, get_schemas


def _cmd_list(args):
    if args and args[0] == "--schemas":
        print(json.dumps(get_schemas(), indent=2, ensure_ascii=False))
    else:
        for name in sorted(REGISTRY):
            print(name)


def _cmd_call(args):
    if not args:
        print("Usage: python -m llmtools call <tool> '<json args>'")
        return 1
    name = args[0]
    raw = args[1] if len(args) > 1 else "{}"
    try:
        params = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[ERROR] args must be JSON: {e}")
        return 1
    print(call_tool(name, params))
    return 0


def _cmd_chat(args):
    # Interactive/one-shot agent loop, reusing agent.py's runner.
    import agent
    sys.argv = ["agent.py", *args]
    agent.main()
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, rest = sys.argv[1], sys.argv[2:]
    dispatch = {"list": _cmd_list, "call": _cmd_call, "chat": _cmd_chat}
    if cmd not in dispatch:
        print(__doc__)
        return 1
    return dispatch[cmd](rest) or 0


if __name__ == "__main__":
    sys.exit(main())
