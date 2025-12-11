"""
Claude API client with cost tracking, model tiering, and rate limiting.

Model Strategy:
- Haiku: Pass 1 extraction (structured data extraction - fast and cheap)
- Sonnet: Pass 2-4 (analysis requires better reasoning)

Cost savings: ~75% reduction on Pass 1 by using Haiku
"""
import anthropic
import os
import json
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Track token usage and costs by model."""

    # Pricing per million tokens (as of Dec 2024)
    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    def __init__(self):
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.by_model: Dict[str, Dict[str, int]] = {}
        self.call_count: int = 0

    def add(self, model: str, input_tokens: int, output_tokens: int):
        """Add tokens to running total, tracked by model."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.call_count += 1

        if model not in self.by_model:
            self.by_model[model] = {"input": 0, "output": 0, "calls": 0}
        self.by_model[model]["input"] += input_tokens
        self.by_model[model]["output"] += output_tokens
        self.by_model[model]["calls"] += 1

    @property
    def cost_usd(self) -> float:
        """Calculate total cost across all models."""
        total = 0.0
        for model, tokens in self.by_model.items():
            pricing = self.PRICING.get(model, self.PRICING["claude-sonnet-4-20250514"])
            total += (tokens["input"] / 1_000_000) * pricing["input"]
            total += (tokens["output"] / 1_000_000) * pricing["output"]
        return total

    def get_breakdown(self) -> Dict[str, Any]:
        """Get detailed cost breakdown by model."""
        breakdown = {}
        for model, tokens in self.by_model.items():
            pricing = self.PRICING.get(model, self.PRICING["claude-sonnet-4-20250514"])
            input_cost = (tokens["input"] / 1_000_000) * pricing["input"]
            output_cost = (tokens["output"] / 1_000_000) * pricing["output"]
            breakdown[model] = {
                "input_tokens": tokens["input"],
                "output_tokens": tokens["output"],
                "calls": tokens["calls"],
                "input_cost_usd": input_cost,
                "output_cost_usd": output_cost,
                "total_cost_usd": input_cost + output_cost
            }
        return breakdown

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "call_count": self.call_count,
            "cost_usd": self.cost_usd,
            "by_model": self.by_model
        }


@dataclass
class ClaudeClient:
    """
    Claude API client with automatic model selection, cost tracking, and retry logic.

    Model aliases:
        - "haiku": claude-3-5-haiku-20241022 (fast, cheap - good for extraction)
        - "sonnet": claude-sonnet-4-20250514 (best reasoning)
    """

    # Model aliases for easy switching
    MODELS = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
    }

    # Rate limiting configuration
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # seconds, will exponentially backoff

    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    usage: TokenUsage = field(default_factory=TokenUsage)
    _client: Any = field(default=None, repr=False)

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=self.api_key)

    def _resolve_model(self, model: str) -> str:
        """Resolve model alias to full model name."""
        return self.MODELS.get(model, model)

    def complete(
        self,
        prompt: str,
        system: str = "",
        model: str = "sonnet",
        max_tokens: int = 4096,
        temperature: float = 0.1,
        json_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Send completion request to Claude with retry logic.

        Args:
            prompt: User message
            system: System prompt
            model: "haiku", "sonnet", or full model name
            max_tokens: Maximum response tokens
            temperature: Sampling temperature (low for consistency)
            json_mode: If True, expect JSON response and parse it

        Returns:
            Dict with either {"text": str} or parsed JSON, or {"error": str, "raw": str}
        """
        resolved_model = self._resolve_model(model)
        messages = [{"role": "user", "content": prompt}]

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self._client.messages.create(
                    model=resolved_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system if system else "You are an expert legal analyst.",
                    messages=messages
                )

                # Track usage
                self.usage.add(
                    resolved_model,
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )

                content = response.content[0].text

                if json_mode:
                    parsed = self._parse_json_response(content)
                    if "error" in parsed and attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"JSON parse failed, attempt {attempt + 1}/{self.MAX_RETRIES}")
                        continue
                    return parsed

                return {"text": content}

            except anthropic.RateLimitError as e:
                delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(f"Rate limited, waiting {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                else:
                    return {"error": f"Rate limit exceeded after {self.MAX_RETRIES} attempts", "raw": str(e)}

            except anthropic.APIStatusError as e:
                if e.status_code == 529:  # Overloaded
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    logger.warning(f"API overloaded, waiting {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"error": f"API overloaded after {self.MAX_RETRIES} attempts", "raw": str(e)}
                else:
                    return {"error": f"API error ({e.status_code}): {str(e)}", "raw": ""}

            except anthropic.APIError as e:
                return {"error": f"API error: {str(e)}", "raw": ""}
            except Exception as e:
                logger.exception(f"Unexpected error in Claude API call: {e}")
                return {"error": f"Unexpected error: {str(e)}", "raw": ""}

        return {"error": "Max retries exceeded", "raw": ""}

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Extract and parse JSON from response, handling markdown code blocks."""
        # Try direct parse first
        try:
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

    # =========================================================================
    # Pass-specific methods with appropriate model selection
    # =========================================================================

    def complete_extraction(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pass 1: Extraction using Haiku.

        Haiku is ideal for structured data extraction:
        - 75% cheaper than Sonnet
        - Faster response times
        - Good enough for extracting parties, dates, clauses
        """
        return self.complete(
            prompt=prompt,
            system=system,
            model="haiku",
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs
        )

    def complete_analysis(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pass 2: Per-document analysis using Sonnet.

        Sonnet needed for:
        - Complex legal reasoning
        - Risk assessment
        - Understanding context and implications
        """
        return self.complete(
            prompt=prompt,
            system=system,
            model="sonnet",
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs
        )

    def complete_crossdoc(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pass 3: Cross-document synthesis using Sonnet.

        Sonnet required for:
        - Comparing multiple documents
        - Finding conflicts and cascades
        - Complex multi-hop reasoning
        """
        return self.complete(
            prompt=prompt,
            system=system,
            model="sonnet",
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs
        )

    def complete_synthesis(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pass 4: Final deal synthesis using Sonnet.

        Sonnet required for:
        - Executive summary generation
        - Deal assessment
        - Prioritizing findings
        """
        return self.complete(
            prompt=prompt,
            system=system,
            model="sonnet",
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs
        )

    def complete_critical(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Critical analysis that requires best reasoning.
        Uses Sonnet with higher token limit.
        """
        return self.complete(
            prompt=prompt,
            system=system,
            model="sonnet",
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs
        )

    # =========================================================================
    # Reporting
    # =========================================================================

    def get_usage_report(self) -> str:
        """Get formatted usage report with breakdown by model."""
        breakdown = self.usage.get_breakdown()

        lines = [
            "",
            "=" * 50,
            "CLAUDE API USAGE REPORT",
            "=" * 50,
            ""
        ]

        for model, data in breakdown.items():
            model_short = model.split("-")[-1][:10] if "-" in model else model[:10]
            lines.append(f"Model: {model}")
            lines.append(f"  Calls:         {data['calls']:,}")
            lines.append(f"  Input tokens:  {data['input_tokens']:,}")
            lines.append(f"  Output tokens: {data['output_tokens']:,}")
            lines.append(f"  Cost:          ${data['total_cost_usd']:.4f}")
            lines.append("")

        lines.append("-" * 50)
        lines.append(f"TOTAL TOKENS:    {self.usage.input_tokens + self.usage.output_tokens:,}")
        lines.append(f"TOTAL CALLS:     {self.usage.call_count:,}")
        lines.append(f"TOTAL COST:      ${self.usage.cost_usd:.4f} USD")
        lines.append("=" * 50)

        return "\n".join(lines)

    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost summary as dictionary (for storage/API response)."""
        return {
            "total_input_tokens": self.usage.input_tokens,
            "total_output_tokens": self.usage.output_tokens,
            "total_calls": self.usage.call_count,
            "total_cost_usd": round(self.usage.cost_usd, 4),
            "breakdown": self.usage.get_breakdown()
        }
