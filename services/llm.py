"""OpenAI text models: which one each job uses, the arguments it accepts, and what a call costs.

gpt-4o and gpt-4o-mini are removed from the API on 2027-01-14. Their places:

- LIGHT (gpt-6-luna) replaces gpt-4o-mini: the query parser, player summaries, match-prediction insights.
  On 100 logged questions it parsed better than gpt-4o (scripts/dev/compare_nl_models.py) at ~1/20 of the cost.
- STRONG (gpt-6.1-sol) replaces gpt-4o where 4o was picked for following rules closely (the reel script) and
  backs up LIGHT when a call fails. Same price class as 4o.

Both are reasoning models: they take reasoning_effort and max_completion_tokens (which also covers the
reasoning) and reject temperature/max_tokens -- chat_kwargs() sends whichever the model accepts. Each can
be pinned per deploy with an env var (OPENAI_MODEL_LIGHT / OPENAI_MODEL_STRONG).

Fast mode (service_tier="fast") makes tokens come quicker at 2x the price; it is for calls a person is
waiting on.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

MODEL_LIGHT = os.getenv("OPENAI_MODEL_LIGHT", "gpt-6-luna")
MODEL_STRONG = os.getenv("OPENAI_MODEL_STRONG", "gpt-6.1-sol")
DEFAULT_REASONING_EFFORT = "low"

# List prices per token (USD), October 2026. Reasoning tokens bill as completion.
MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4o": {"prompt": 2.50 / 1_000_000, "completion": 10.00 / 1_000_000},
    "gpt-4o-mini": {"prompt": 0.15 / 1_000_000, "completion": 0.60 / 1_000_000},
    "gpt-6-luna": {"prompt": 0.10 / 1_000_000, "completion": 0.50 / 1_000_000},
    "gpt-6.1-sol": {"prompt": 2.00 / 1_000_000, "completion": 10.00 / 1_000_000},
    "gpt-5.6-luna": {"prompt": 0.20 / 1_000_000, "completion": 1.20 / 1_000_000},
    "gpt-5.4-mini": {"prompt": 0.75 / 1_000_000, "completion": 4.50 / 1_000_000},
}
FAST_TIERS = ("fast", "priority")  # "priority" is Fast mode's old name


def is_reasoning_model(model: str) -> bool:
    """gpt-5 and later reason before answering; the gpt-4 family does not."""
    return not model.startswith("gpt-4")


def chat_kwargs(model: str, max_output_tokens: int, temperature: float = 0.1,
                reasoning_effort: Optional[str] = None, service_tier: Optional[str] = None) -> Dict[str, Any]:
    """Sampling arguments for chat.completions.create that `model` accepts. A reasoning model's
    max_completion_tokens gets headroom over the visible answer, since its reasoning counts too."""
    if is_reasoning_model(model):
        kwargs: Dict[str, Any] = {"max_completion_tokens": max_output_tokens + 5000,
                                  "reasoning_effort": reasoning_effort or DEFAULT_REASONING_EFFORT}
    else:
        kwargs = {"temperature": temperature, "max_tokens": max_output_tokens}
    if service_tier:
        kwargs["service_tier"] = service_tier
    return kwargs


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int, service_tier: Optional[str] = None) -> float:
    """USD for one call at list prices (cached input billed as uncached; an unknown model as gpt-4o)."""
    costs = MODEL_COSTS.get(model, MODEL_COSTS["gpt-4o"])
    multiplier = 2.0 if service_tier in FAST_TIERS else 1.0
    return multiplier * ((prompt_tokens * costs["prompt"]) + (completion_tokens * costs["completion"]))
