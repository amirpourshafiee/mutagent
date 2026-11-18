"""LLM access: a tiny interface the agent depends on, plus the Anthropic implementation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# USD per million tokens (Claude pricing page, Sonnet 5.5): input, output.
PRICES = {"claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}


class LLM(Protocol):
    def complete(self, system: str, user: str) -> str: ...

    @property
    def cost_usd(self) -> float: ...


@dataclass
class AnthropicLLM:
    model: str = "claude-sonnet-5-5"
    max_tokens: int = 8000
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        import anthropic  # optional dependency: pip install -e ".[llm]"

        self._client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

    def complete(self, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self.model, max_tokens=self.max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        self.input_tokens += msg.usage.input_tokens
        self.output_tokens += msg.usage.output_tokens
        return "".join(b.text for b in msg.content if b.type == "text")

    @property
    def cost_usd(self) -> float:
        p_in, p_out = PRICES[self.model]
        return (self.input_tokens * p_in + self.output_tokens * p_out) / 1_000_000
