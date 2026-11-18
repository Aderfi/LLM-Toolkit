"""Run the local agent: `python agent.py "your prompt"` (one-shot) or `python agent.py` (REPL)."""

import sys

from llmtools.__main__ import main

if __name__ == "__main__":
    sys.exit(main(["chat", *sys.argv[1:]]))
