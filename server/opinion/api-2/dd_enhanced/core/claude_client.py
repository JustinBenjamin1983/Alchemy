"""
Claude API client with cost tracking and model selection.
Uses Sonnet for bulk processing, Opus for critical analysis.
"""
import anthropic
import os
import json
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class TokenUsage:
    """Track token usage and costs."""
    input_tokens: int = 0
    output_tokens: int = 0

    # Pricing as of Dec 2024
    SONNET_INPUT_PRICE = 3.0  # per million tokens
    SONNET_OUTPUT_PRICE = 15.0  # per million tokens
    OPUS_INPUT_PRICE = 15.0  # per million tokens
    OPUS_OUTPUT_PRICE = 75.0  # per million tokens

    @property
    def cost_usd(self) -> float:
        """Estimate cost using blended Sonnet rate (most calls use Sonnet)."""
        input_cost = (self.input_tokens / 1_000_000) * self.SONNET_INPUT_PRICE
        output_cost = (self.output_tokens / 1_000_000) * self.SONNET_OUTPUT_PRICE
        return input_cost + output_cost

    def add(self, input_tokens: int, output_tokens: int):
        """Add tokens to running total."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens


@dataclass
class ClaudeClient:
    """Claude API client with automatic model selection and cost tracking."""

    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    usage: TokenUsage = field(default_factory=TokenUsage)
    _client: Any = field(default=None, repr=False)

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def complete(
        self,
        prompt: str,
        system: str = "",
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send completion request to Claude.

        Args:
            prompt: User message
            system: System prompt
            model: claude-sonnet-4-20250514 or claude-sonnet-4-20250514
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (low for consistency)
            json_mode: If True, expect JSON response and parse it

        Returns:
            Dict with either {"text": str} or parsed JSON, or {"error": str, "raw": str}
        """
        messages = [{"role": "user", "content": prompt}]

        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else "You are an expert legal analyst.",
                messages=messages
            )

            # Track usage
            self.usage.add(
                response.usage.input_tokens,
                response.usage.output_tokens
            )

            content = response.content[0].text

            if json_mode:
                return self._parse_json_response(content)

            return {"text": content}

        except anthropic.APIError as e:
            return {"error": f"API error: {str(e)}", "raw": ""}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "raw": ""}

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from response, handling markdown code blocks."""
        try:
            # Try direct parse first
            return json.loads(content.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code block
        try:
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
                return json.loads(json_str.strip())
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
                return json.loads(json_str.strip())
        except (json.JSONDecodeError, IndexError):
            pass

        # Try finding JSON object with regex
        try:
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                return json.loads(match.group())
        except json.JSONDecodeError:
            pass

        # Try finding JSON array
        try:
            match = re.search(r'\[[\s\S]*\]', content)
            if match:
                return {"data": json.loads(match.group())}
        except json.JSONDecodeError:
            pass

        return {"error": "Failed to parse JSON", "raw": content}

    def complete_critical(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Use best model for critical analysis (Pass 3 & 4).
        Currently uses Sonnet for cost efficiency, but could upgrade to Opus.
        """
        return self.complete(
            prompt=prompt,
            system=system,
            model="claude-sonnet-4-20250514",  # Best reasoning available
            max_tokens=max_tokens,
            **kwargs
        )

    def get_usage_report(self) -> str:
        """Get formatted usage report."""
        return f"""
Token Usage Report
==================
  Input tokens:  {self.usage.input_tokens:,}
  Output tokens: {self.usage.output_tokens:,}
  Total tokens:  {self.usage.input_tokens + self.usage.output_tokens:,}

  Estimated cost: ${self.usage.cost_usd:.4f} USD
"""
