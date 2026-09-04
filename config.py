"""
The only file in this project that knows how Claude gets called.

Two backends:
  - "cli"  (default): shells out to the official Claude Code CLI (`claude -p`),
            authenticated with your Pro/Max subscription login (`claude login`).
            No API key, no per-token billing. Intended for local/interactive-adjacent
            use only — see the note below before wiring this into CI.
  - "api" : uses the Anthropic Python SDK with an API key, pay-per-token.
            Needed for GitHub Actions / servers / high-frequency evolve runs.

Everything else in the codebase calls `get_backend().complete(prompt)` and never
knows or cares which one is active.
"""

import os
import subprocess


class Backend:
    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        raise NotImplementedError


class ClaudeCodeCLIBackend(Backend):
    """
    Uses your existing Pro/Max subscription via the official `claude` CLI in
    non-interactive mode. This is Anthropic's own product being used as intended
    (see README) — but it shares your normal 5-hour/weekly usage pool, and it's
    meant to run on YOUR machine, not on shared CI infrastructure. Keep evolve
    runs infrequent on this backend (default: once a day).
    """

    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        # Prompt goes via stdin, not as a CLI argument - Windows caps a
        # process's full command line at ~32K characters, and this prompt
        # embeds full source files that already exceed that on their own as
        # the codebase grows. `claude -p` with no prompt argument reads from
        # stdin, which has no such limit.
        result = subprocess.run(
            ["claude", "-p"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"claude CLI failed: {result.stderr.strip()}")
        return result.stdout.strip()


class ClaudeAPIBackend(Backend):
    """
    Pay-per-token via the Anthropic API. Required for GitHub Actions, servers,
    or any run frequency beyond what your subscription quota comfortably covers.
    """

    def __init__(self):
        import anthropic  # imported lazily so the "cli" backend has zero extra deps

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("WORLD_BACKEND=api requires ANTHROPIC_API_KEY to be set")
        self.client = anthropic.Anthropic(api_key=api_key)

    def complete(self, prompt: str, max_tokens: int = 4000) -> str:
        message = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")


def get_backend() -> Backend:
    backend = os.environ.get("WORLD_BACKEND", "cli").lower()
    if backend == "cli":
        return ClaudeCodeCLIBackend()
    if backend == "api":
        return ClaudeAPIBackend()
    raise ValueError(f"Unknown WORLD_BACKEND: {backend!r} (expected 'cli' or 'api')")
