import json
import os
import re

import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")
_client = None


def _get_client():
    global _client
    if _client is None:
        # Reads ANTHROPIC_API_KEY from the environment. Never hard-code the key.
        _client = anthropic.Anthropic()
    return _client


def ask(system: str, user: str, max_tokens: int = 1000) -> str:
    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


def ask_json(system: str, user: str, max_tokens: int = 1000):
    """Ask for JSON only; strip code fences and parse. Raises ValueError if invalid."""
    raw = ask(system, user, max_tokens)
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {raw[:200]}") from e
