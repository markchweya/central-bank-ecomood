"""Classify central bank speech paragraphs with an LLM.

Each paragraph gets two labels:

- stance:  hawkish / dovish / neutral / none   (monetary-policy leaning)
- outlook: positive / negative / neutral / none (view of the economy)

Two backends share one prompt and one output schema:

- OllamaScorer runs a local model through Ollama (default, free, CPU-friendly)
- ClaudeScorer calls the Anthropic API (optional, needs `pip install anthropic`
  and an API key or `ant auth login` profile)
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

STANCE_LABELS = ("hawkish", "dovish", "neutral", "none")
OUTLOOK_LABELS = ("positive", "negative", "neutral", "none")

# Numeric values used when aggregating labels into an index.
STANCE_SCORE = {"hawkish": 1.0, "dovish": -1.0, "neutral": 0.0}
OUTLOOK_SCORE = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}

MAX_PARAGRAPH_CHARS = 2000

SYSTEM_PROMPT = """You label paragraphs from central bank speeches for an economic research dataset.

Return two labels.

stance: the monetary-policy leaning the paragraph expresses.
- hawkish: favours tighter policy or higher rates, or stresses upside inflation risks.
- dovish: favours looser policy or lower rates, or stresses weak demand, downside risks or slack.
- neutral: discusses monetary policy or inflation without leaning either way.
- none: the paragraph is not about monetary policy or inflation (for example banking regulation, payments, history, thanks to hosts, references).

outlook: the speaker's view of current or expected economic conditions.
- positive: growth is solid or improving, risks are receding, conditions are favourable.
- negative: growth is weak or deteriorating, risks are rising, conditions are difficult.
- neutral: describes the economy without a clear direction, or balances both sides.
- none: the paragraph does not discuss economic conditions.

Judge only what the paragraph says, not what you know about the period."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "stance": {"type": "string", "enum": list(STANCE_LABELS)},
        "outlook": {"type": "string", "enum": list(OUTLOOK_LABELS)},
    },
    "required": ["stance", "outlook"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Label:
    stance: str
    outlook: str


def parse_label(raw: str) -> Label:
    data = json.loads(raw)
    stance, outlook = data.get("stance"), data.get("outlook")
    if stance not in STANCE_LABELS or outlook not in OUTLOOK_LABELS:
        raise ValueError(f"Unexpected labels in model output: {raw!r}")
    return Label(stance, outlook)


class OllamaScorer:
    """Score paragraphs with a local Ollama model, using its JSON-schema output mode."""

    backend = "ollama"

    def __init__(self, model: str = "llama3.2:3b", host: str = "http://localhost:11434"):
        self.model = model
        self.url = f"{host.rstrip('/')}/api/chat"

    def score(self, paragraph: str) -> Label:
        body = {
            "model": self.model,
            "stream": False,
            "format": OUTPUT_SCHEMA,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": paragraph[:MAX_PARAGRAPH_CHARS]},
            ],
        }
        request = urllib.request.Request(
            self.url, json.dumps(body).encode(), {"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            reply = json.load(response)
        return parse_label(reply["message"]["content"])


class ClaudeScorer:
    """Score paragraphs with Claude through the Anthropic API, using structured outputs."""

    backend = "claude"

    def __init__(self, model: str = "claude-opus-5-5", effort: str = "low"):
        import anthropic  # optional dependency, only needed for this backend

        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort

    def score(self, paragraph: str) -> Label:
        response = self.client.beta.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            output_config={
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
            },
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": paragraph[:MAX_PARAGRAPH_CHARS]}],
        )
        if response.stop_reason == "refusal":
            raise ValueError("Model declined to label this paragraph")
        text = next(block.text for block in response.content if block.type == "text")
        return parse_label(text)


def make_scorer(backend: str, model: str | None = None):
    if backend == "ollama":
        return OllamaScorer(model or "llama3.2:3b")
    if backend == "claude":
        return ClaudeScorer(model or "claude-opus-5-5")
    raise ValueError(f"Unknown backend {backend!r}; use 'ollama' or 'claude'")
