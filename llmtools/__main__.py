"""CLI to use the tools outside an agent, or to chat with the local agent.

python -m llmtools list [--schemas]           # list tools (or their JSON schemas)
python -m llmtools call <name> '<json args>'  # run one tool, print the result
python -m llmtools chat ["<prompt>"]          # agent: one-shot with a prompt, REPL without
python -m llmtools google-auth                # one-off Google Drive OAuth
"""

import json
import logging
import sys

from . import REGISTRY, call_tool, get_schemas


def _cmd_list(args):
    if args and args[0] == "--schemas":
        print(json.dumps(get_schemas(), indent=2, ensure_ascii=False))
    else:
        for name in sorted(REGISTRY, key=lambda n: (REGISTRY[n].group, n)):
            t = REGISTRY[name]
            print(f"{t.group:15} {name}{'  [confirm]' if t.confirm else ''}")


def _cmd_call(args):
    if not args:
        print("Usage: python -m llmtools call <tool> '<json args>'")
        return 1
    name = args[0]
    raw = args[1] if len(args) > 1 else "{}"
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON args: {e}")
        return 1
    print(call_tool(name, parsed))
    return 0


def _ask_confirmation(name: str, args: dict) -> bool:
    shown = json.dumps(args, ensure_ascii=False)
    answer = input(f"\n[CONFIRM] {name}({shown})\nRun it? [y/N] ")
    return answer.strip().lower() in ("y", "yes", "s", "si", "sí")


def _cmd_chat(args):
    from .llm import Agent

    logging.basicConfig(level=logging.INFO, format="  -> %(message)s")
    agent = Agent()
    messages: list[dict] = []
    if args:
        print(agent.run([{"role": "user", "content": " ".join(args)}], _ask_confirmation))
        return 0
    print("Local agent. Empty line or Ctrl-D to quit.")
    while True:
        try:
            prompt = input("\n> ").strip()
        except EOFError:
            return 0
        if not prompt:
            return 0
        messages.append({"role": "user", "content": prompt})
        print("\n" + agent.run(messages, _ask_confirmation))


def _cmd_google_auth(args):
    from .gdrive import authorize

    print(f"Token saved to {authorize()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    dispatch = {
        "list": _cmd_list,
        "call": _cmd_call,
        "chat": _cmd_chat,
        "google-auth": _cmd_google_auth,
    }
    if not argv or argv[0] not in dispatch:
        print(__doc__)
        return 1
    return dispatch[argv[0]](argv[1:]) or 0


if __name__ == "__main__":
    sys.exit(main())
