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

# v1: one question, two labels (22% stance accuracy with llama3.2:3b).
# v2: topic first, then leaning, with worked examples. The topic gates the labels,
#     so a paragraph about payments or regulation cannot get a policy stance.
PROMPT_VERSION = "v2"

TOPICS = ("monetary_policy", "economy", "both", "other")

SYSTEM_PROMPT = """You label paragraphs from central bank speeches for an economic research dataset.

Answer in three steps.

1. topic: what is the paragraph mainly about?
- monetary_policy: interest rates, the policy stance, inflation, or the inflation target.
- economy: growth, output, jobs, demand, or the economic outlook, without discussing policy.
- both: monetary policy or inflation AND the state of the economy.
- other: anything else. Banking supervision, regulation, payments, financial inclusion,
  fintech, climate, institutional history, statistics, thanks to hosts, references.
  Most paragraphs in central bank speeches are "other".

2. stance (only if topic is monetary_policy or both, otherwise "none"):
- hawkish: argues for higher rates or tighter policy, or warns that inflation is too high or rising.
- dovish: argues for lower rates, looser or accommodative policy, stimulus, or warns that
  inflation is too low, demand is weak, or deflation is a risk.
- neutral: describes policy or inflation without arguing for tighter or looser policy.

3. outlook (only if topic is economy or both, otherwise "none"):
- positive: growth is solid or improving, conditions are favourable.
- negative: growth is weak or falling, a recession or crisis, risks are rising.
- neutral: mixed or no clear direction.

Judge only what the paragraph says, not what you know about the period."""

# Short invented paragraphs (not taken from the validation set) showing each case.
EXAMPLES = [
    ("Inflation has stayed well above our 2 percent target and wage growth is accelerating. "
     "The Committee therefore judged that a further increase in the policy rate was warranted.",
     {"topic": "monetary_policy", "stance": "hawkish", "outlook": "none"}),
    ("With inflation running below target and unemployment rising, we lowered the policy rate "
     "and will keep monetary conditions accommodative to support the recovery.",
     {"topic": "both", "stance": "dovish", "outlook": "negative"}),
    ("Real GDP grew by 3.1 percent last year, driven by strong exports and household "
     "consumption, and we expect a similar pace this year.",
     {"topic": "economy", "stance": "none", "outlook": "positive"}),
    ("The new capital requirements will strengthen the resilience of banks, and supervisors "
     "will monitor their implementation closely.",
     {"topic": "other", "stance": "none", "outlook": "none"}),
    ("Let me thank the organisers for inviting me to this conference on digital payments.",
     {"topic": "other", "stance": "none", "outlook": "none"}),
    ("The policy rate is set eight times a year, and the decision is explained in a press "
     "release and a monetary policy report.",
     {"topic": "monetary_policy", "stance": "neutral", "outlook": "none"}),
]

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "enum": list(TOPICS)},
        "stance": {"type": "string", "enum": list(STANCE_LABELS)},
        "outlook": {"type": "string", "enum": list(OUTLOOK_LABELS)},
    },
    "required": ["topic", "stance", "outlook"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Label:
    stance: str
    outlook: str


def parse_label(raw: str) -> Label:
    data = json.loads(raw)
    topic, stance, outlook = data.get("topic"), data.get("stance"), data.get("outlook")
    if topic not in TOPICS or stance not in STANCE_LABELS or outlook not in OUTLOOK_LABELS:
        raise ValueError(f"Unexpected labels in model output: {raw!r}")
    # The topic gates the labels, whatever the model put in the other fields.
    if topic not in ("monetary_policy", "both"):
        stance = "none"
    elif stance == "none":
        stance = "neutral"
    if topic not in ("economy", "both"):
        outlook = "none"
    elif outlook == "none":
        outlook = "neutral"
    return Label(stance, outlook)


def build_messages(paragraph: str) -> list[dict]:
    messages = []
    for text, answer in EXAMPLES:
        messages.append({"role": "user", "content": text})
        messages.append({"role": "assistant", "content": json.dumps(answer)})
    messages.append({"role": "user", "content": paragraph[:MAX_PARAGRAPH_CHARS]})
    return messages


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
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *build_messages(paragraph)],
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
            messages=build_messages(paragraph),
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
