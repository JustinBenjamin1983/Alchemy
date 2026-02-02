"""
Claude API client with cost tracking, model tiering, and rate limiting.

Pass Structure (7 passes):
- Pass 1: Extract (Haiku) - structured data extraction
- Pass 2: Analyze (Sonnet) - per-document risk analysis
- [Checkpoint C] - human validation
- Pass 3: Calculate (Python) - no AI model
- Pass 4: Cross-Doc (Opus ALWAYS) - complex cross-document reasoning
- Pass 5: Aggregate (Python) - no AI model
- Pass 6: Synthesize (Sonnet) - executive summary generation
- Pass 7: Verify (Opus) - final quality control

Model Tiers (affects Pass 2 and Pass 6 only):
- COST_OPTIMIZED: Sonnet for analysis/synthesis
- BALANCED: Sonnet for analysis/synthesis (default)
- HIGH_ACCURACY: Sonnet for analysis, Opus for synthesis
- MAXIMUM_ACCURACY: Opus for analysis and synthesis

Note: Pass 4 (Cross-Doc) and Pass 7 (Verify) ALWAYS use Opus regardless of tier.
"""
import anthropic
import os
import json
import re
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)


class ModelTier(Enum):
    """Model tier options for different accuracy/cost tradeoffs.

    Note: Pass 4 (Cross-Doc) and Pass 7 (Verify) ALWAYS use Opus regardless of tier.
    Tier selection only affects Pass 2 (Analyze) and Pass 6 (Synthesize).
    """
    COST_OPTIMIZED = "cost_optimized"      # H-S-O-S-O: Sonnet for analysis/synthesis
    BALANCED = "balanced"                   # H-S-O-S-O: Default, Sonnet for analysis/synthesis
    HIGH_ACCURACY = "high_accuracy"         # H-S-O-O-O: Opus for synthesis
    MAXIMUM_ACCURACY = "maximum_accuracy"   # H-O-O-O-O: Opus for analysis and synthesis


@dataclass
class TokenUsage:
    """Track token usage and costs by model."""

    # Pricing per million tokens (as of Dec 2024)
    PRICING = {
        "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
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
        - "sonnet": claude-sonnet-4-20250514 (good reasoning, cost effective)
        - "opus": claude-opus-4-20250514 (best reasoning, premium cost)

    Pass Structure (7 passes):
        - Pass 1: Extract (Haiku) - structured data extraction
        - Pass 2: Analyze (tier-dependent) - per-document risk analysis
        - Pass 3: Calculate (Python) - no AI model
        - Pass 4: Cross-Doc (Opus ALWAYS) - cross-document reasoning
        - Pass 5: Aggregate (Python) - no AI model
        - Pass 6: Synthesize (tier-dependent) - executive summary
        - Pass 7: Verify (Opus ALWAYS) - final QC

    Model Tiers (only affects Pass 2 and Pass 6):
        - COST_OPTIMIZED: H-S-O-S-O (~$8/10 docs)
        - BALANCED: H-S-O-S-O (~$8/10 docs) - default
        - HIGH_ACCURACY: H-S-O-O-O (~$15/10 docs)
        - MAXIMUM_ACCURACY: H-O-O-O-O (~$40/10 docs)
    """

    # Model aliases for easy switching
    MODELS = {
        "haiku": "claude-3-5-haiku-20241022",
        "sonnet": "claude-sonnet-4-20250514",
        "opus": "claude-opus-4-20250514",
    }

    # Model selection by tier and pass
    # Format: tier -> {pass_name: model_alias}
    #
    # New 7-pass structure:
    # - pass1: Extract (Haiku always)
    # - pass2: Analyze (tier-dependent)
    # - pass3: Calculate (Python, no model)
    # - pass4: Cross-Doc (Opus ALWAYS - complex reasoning)
    # - pass5: Aggregate (Python, no model)
    # - pass6: Synthesize (tier-dependent)
    # - pass7: Verify (Opus ALWAYS - QC)
    #
    # Legacy keys (pass3_crossdoc, pass4_synthesis) map to new structure
    TIER_MODELS = {
        ModelTier.COST_OPTIMIZED: {
            "pass1": "haiku",
            "pass2": "sonnet",
            "pass3": "opus",    # Cross-Doc: ALWAYS Opus (legacy key)
            "pass4": "sonnet",  # Synthesis: Sonnet for cost (legacy key)
            "pass4_crossdoc": "opus",   # New key: Cross-Doc ALWAYS Opus
            "pass6_synthesize": "sonnet",
            "pass7_verify": "opus",
        },
        ModelTier.BALANCED: {
            "pass1": "haiku",
            "pass2": "sonnet",
            "pass3": "opus",    # Cross-Doc: ALWAYS Opus
            "pass4": "sonnet",  # Synthesis: Sonnet
            "pass4_crossdoc": "opus",
            "pass6_synthesize": "sonnet",
            "pass7_verify": "opus",
        },
        ModelTier.HIGH_ACCURACY: {
            "pass1": "haiku",
            "pass2": "sonnet",
            "pass3": "opus",    # Cross-Doc: ALWAYS Opus
            "pass4": "opus",    # Synthesis: Opus for accuracy
            "pass4_crossdoc": "opus",
            "pass6_synthesize": "opus",
            "pass7_verify": "opus",
        },
        ModelTier.MAXIMUM_ACCURACY: {
            "pass1": "haiku",
            "pass2": "opus",    # Analysis: Opus for max accuracy
            "pass3": "opus",    # Cross-Doc: ALWAYS Opus
            "pass4": "opus",    # Synthesis: Opus
            "pass4_crossdoc": "opus",
            "pass6_synthesize": "opus",
            "pass7_verify": "opus",
        },
    }

    # Rate limiting configuration
    MAX_RETRIES = 3
    RETRY_DELAY_BASE = 2  # seconds, will exponentially backoff

    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    usage: TokenUsage = field(default_factory=TokenUsage)
    model_tier: ModelTier = field(default=ModelTier.HIGH_ACCURACY)  # Haiku-Sonnet-Opus-Opus for accuracy testing
    _client: Any = field(default=None, repr=False)

    def __post_init__(self):
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self._client = anthropic.Anthropic(api_key=self.api_key)

        # Allow setting tier from environment variable
        tier_env = os.environ.get("DD_MODEL_TIER", "").lower()
        if tier_env:
            tier_map = {
                "cost_optimized": ModelTier.COST_OPTIMIZED,
                "balanced": ModelTier.BALANCED,
                "high_accuracy": ModelTier.HIGH_ACCURACY,
                "maximum_accuracy": ModelTier.MAXIMUM_ACCURACY,
            }
            if tier_env in tier_map:
                self.model_tier = tier_map[tier_env]
                logger.info(f"Using model tier from environment: {self.model_tier.value}")

    def get_model_for_pass(self, pass_name: str) -> str:
        """Get the appropriate model alias for a given pass based on current tier."""
        tier_config = self.TIER_MODELS.get(self.model_tier, self.TIER_MODELS[ModelTier.COST_OPTIMIZED])
        return tier_config.get(pass_name, "sonnet")

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
        import traceback

        resolved_model = self._resolve_model(model)
        messages = [{"role": "user", "content": prompt}]

        print(f"[ClaudeClient.complete] Starting API call: model={resolved_model}, prompt_len={len(prompt)}, max_tokens={max_tokens}, json_mode={json_mode}", flush=True)

        for attempt in range(self.MAX_RETRIES):
            try:
                print(f"[ClaudeClient.complete] Attempt {attempt + 1}/{self.MAX_RETRIES}...", flush=True)
                api_start = time.time()

                response = self._client.messages.create(
                    model=resolved_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system if system else "You are an expert legal analyst.",
                    messages=messages
                )

                api_elapsed = time.time() - api_start
                print(f"[ClaudeClient.complete] API response received in {api_elapsed:.2f}s", flush=True)
                print(f"[ClaudeClient.complete] Tokens: input={response.usage.input_tokens}, output={response.usage.output_tokens}", flush=True)

                # Track usage
                self.usage.add(
                    resolved_model,
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )

                content = response.content[0].text
                print(f"[ClaudeClient.complete] Response content length: {len(content)} chars", flush=True)

                if json_mode:
                    print(f"[ClaudeClient.complete] Parsing JSON response...", flush=True)
                    parsed = self._parse_json_response(content)
                    if "error" in parsed:
                        print(f"[ClaudeClient.complete] JSON parse error: {parsed.get('error')}", flush=True)
                        if attempt < self.MAX_RETRIES - 1:
                            logger.warning(f"JSON parse failed, attempt {attempt + 1}/{self.MAX_RETRIES}")
                            print(f"[ClaudeClient.complete] Raw content (first 500 chars): {content[:500]}", flush=True)
                            continue
                    else:
                        print(f"[ClaudeClient.complete] JSON parsed successfully, keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'array'}", flush=True)
                    return parsed

                return {"text": content}

            except anthropic.RateLimitError as e:
                delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                print(f"[ClaudeClient.complete] RATE LIMITED, waiting {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})", flush=True)
                logger.warning(f"Rate limited, waiting {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)
                else:
                    print(f"[ClaudeClient.complete] Rate limit exceeded after all retries", flush=True)
                    return {"error": f"Rate limit exceeded after {self.MAX_RETRIES} attempts", "raw": str(e)}

            except anthropic.APIStatusError as e:
                print(f"[ClaudeClient.complete] API STATUS ERROR: status={e.status_code}, message={str(e)}", flush=True)
                if e.status_code == 529:  # Overloaded
                    delay = self.RETRY_DELAY_BASE * (2 ** attempt)
                    print(f"[ClaudeClient.complete] API overloaded, waiting {delay}s", flush=True)
                    logger.warning(f"API overloaded, waiting {delay}s (attempt {attempt + 1}/{self.MAX_RETRIES})")
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(delay)
                    else:
                        return {"error": f"API overloaded after {self.MAX_RETRIES} attempts", "raw": str(e)}
                else:
                    return {"error": f"API error ({e.status_code}): {str(e)}", "raw": ""}

            except anthropic.APIError as e:
                print(f"[ClaudeClient.complete] API ERROR: {str(e)}", flush=True)
                print(f"[ClaudeClient.complete] Traceback:\n{traceback.format_exc()}", flush=True)
                return {"error": f"API error: {str(e)}", "raw": ""}
            except Exception as e:
                print(f"[ClaudeClient.complete] UNEXPECTED ERROR: {str(e)}", flush=True)
                print(f"[ClaudeClient.complete] Traceback:\n{traceback.format_exc()}", flush=True)
                logger.exception(f"Unexpected error in Claude API call: {e}")
                return {"error": f"Unexpected error: {str(e)}", "raw": ""}

        print(f"[ClaudeClient.complete] Max retries exceeded", flush=True)
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
    # Pass-specific methods with tier-based model selection
    # =========================================================================

    def complete_extraction(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 4096,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pass 1: Extraction.

        Default: Haiku (75% cheaper than Sonnet, fast response times)
        All tiers use Haiku for extraction - structured data extraction
        doesn't benefit significantly from more powerful models.
        """
        model = self.get_model_for_pass("pass1")
        logger.debug(f"Pass 1 (extraction) using model: {model}")
        # Remove json_mode from kwargs if passed to avoid duplicate argument error
        kwargs.pop('json_mode', None)
        return self.complete(
            prompt=prompt,
            system=system,
            model=model,
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
        Pass 2: Per-document analysis.

        Default: Sonnet (good reasoning, cost effective)
        MAXIMUM_ACCURACY tier: Opus (best reasoning for complex risk assessment)

        This pass benefits from better reasoning for:
        - Complex legal interpretation
        - Nuanced risk assessment
        - Understanding context and implications
        """
        model = self.get_model_for_pass("pass2")
        logger.debug(f"Pass 2 (analysis) using model: {model}")
        # Remove json_mode from kwargs if passed to avoid duplicate argument error
        kwargs.pop('json_mode', None)
        return self.complete(
            prompt=prompt,
            system=system,
            model=model,
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
        Pass 4: Cross-document analysis.

        ALWAYS uses Opus regardless of tier - this is fundamental complex reasoning.

        This is the HIGHEST IMPACT pass because it requires:
        - Complex multi-document reasoning
        - Identifying subtle conflicts between documents
        - Understanding cascade effects
        - Multi-hop logical inference

        Opus significantly outperforms Sonnet on cross-document conflict detection.
        """
        model = self.get_model_for_pass("pass3")  # Legacy key, always returns Opus now
        logger.debug(f"Pass 4 (cross-doc) using model: {model}")
        # Remove json_mode from kwargs if passed to avoid duplicate argument error
        kwargs.pop('json_mode', None)
        return self.complete(
            prompt=prompt,
            system=system,
            model=model,
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
        Pass 6: Final synthesis and recommendations.

        Tier-dependent model selection:
        - COST_OPTIMIZED/BALANCED: Sonnet
        - HIGH_ACCURACY/MAXIMUM: Opus

        This pass benefits from Opus for:
        - Comprehensive executive summaries
        - Nuanced deal impact assessment
        - Prioritizing and connecting findings
        - Generating actionable recommendations
        """
        model = self.get_model_for_pass("pass4")  # Legacy key maps to pass6 behavior
        logger.debug(f"Pass 6 (synthesis) using model: {model}")
        # Remove json_mode from kwargs if passed to avoid duplicate argument error
        kwargs.pop('json_mode', None)
        return self.complete(
            prompt=prompt,
            system=system,
            model=model,
            max_tokens=max_tokens,
            json_mode=True,
            **kwargs
        )

    def complete_verification(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 8192,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pass 7: Final verification and quality control.

        ALWAYS uses Opus regardless of tier for maximum accuracy.

        This pass:
        - Double-checks severity classification
        - Validates financial calculations
        - Confirms cross-document conflict analysis
        - Reduces false positives on critical issues
        """
        logger.debug("Pass 7 (verification) using model: opus")
        # Remove json_mode from kwargs if passed to avoid duplicate argument error
        kwargs.pop('json_mode', None)
        return self.complete(
            prompt=prompt,
            system=system,
            model="opus",
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
        Always uses Opus regardless of tier setting.
        """
        # Remove json_mode from kwargs if passed to avoid duplicate argument error
        kwargs.pop('json_mode', None)
        return self.complete(
            prompt=prompt,
            system=system,
            model="opus",
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
            "model_tier": self.model_tier.value,
            "breakdown": self.usage.get_breakdown()
        }

    def get_tier_info(self) -> Dict[str, Any]:
        """Get information about current tier and expected accuracy/cost.

        Pass structure:
        - Pass 1: Extract (Haiku always)
        - Pass 2: Analyze (tier-dependent)
        - Pass 3: Calculate (Python)
        - Pass 4: Cross-Doc (Opus always)
        - Pass 5: Aggregate (Python)
        - Pass 6: Synthesize (tier-dependent)
        - Pass 7: Verify (Opus always)
        """
        tier_info = {
            ModelTier.COST_OPTIMIZED: {
                "name": "Cost Optimized",
                "models": "Haiku → Sonnet → [Python] → Opus → [Python] → Sonnet → Opus",
                "expected_accuracy": "~92%",
                "expected_cost_10_docs": "$8.00",
                "description": "Sonnet for analysis/synthesis, Opus for cross-doc/verify"
            },
            ModelTier.BALANCED: {
                "name": "Balanced",
                "models": "Haiku → Sonnet → [Python] → Opus → [Python] → Sonnet → Opus",
                "expected_accuracy": "~92%",
                "expected_cost_10_docs": "$8.00",
                "description": "Default tier - Sonnet for analysis/synthesis, Opus for cross-doc/verify"
            },
            ModelTier.HIGH_ACCURACY: {
                "name": "High Accuracy",
                "models": "Haiku → Sonnet → [Python] → Opus → [Python] → Opus → Opus",
                "expected_accuracy": "~95%",
                "expected_cost_10_docs": "$15.00",
                "description": "Opus for synthesis - recommended for complex transactions"
            },
            ModelTier.MAXIMUM_ACCURACY: {
                "name": "Maximum Accuracy",
                "models": "Haiku → Opus → [Python] → Opus → [Python] → Opus → Opus",
                "expected_accuracy": "~97%",
                "expected_cost_10_docs": "$40.00",
                "description": "Opus for analysis - premium tier for critical transactions"
            },
        }

        info = tier_info.get(self.model_tier, tier_info[ModelTier.COST_OPTIMIZED])
        info["current_tier"] = self.model_tier.value
        info["pass_models"] = {
            "pass1_extract": self.get_model_for_pass("pass1"),
            "pass2_analyze": self.get_model_for_pass("pass2"),
            "pass3_calculate": "python",
            "pass4_crossdoc": self.get_model_for_pass("pass3"),  # Legacy key, always Opus
            "pass5_aggregate": "python",
            "pass6_synthesize": self.get_model_for_pass("pass4"),
            "pass7_verify": "opus",
        }
        return info
