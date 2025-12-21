# Claude Model Recommendations for DD Analysis

This document outlines the recommended Claude AI models for different functions within the Due Diligence analysis system.

## Model Overview

| Model | Best For | Cost | Speed | Context |
|-------|----------|------|-------|---------|
| **claude-3-5-sonnet-20241022** | Complex analysis, synthesis | Medium | Fast | 200K |
| **claude-3-5-haiku-20241022** | Quick tasks, simple Q&A | Low | Very Fast | 200K |
| **claude-3-opus-20240229** | Highest quality analysis | High | Slower | 200K |

## Function-Specific Recommendations

### 1. Document Analysis (4-Pass Pipeline)

**Pass 1: Extract** - `claude-3-5-haiku-20241022`
- Simple extraction task
- High throughput needed for multiple documents
- Cost-effective for large document sets
- Structured output (JSON)

**Pass 2: Analyse** - `claude-3-5-sonnet-20241022`
- Requires nuanced understanding
- Legal and financial analysis
- Balances quality and cost
- Critical for accurate findings

**Pass 3: Cross-Document Analysis** - `claude-3-5-sonnet-20241022`
- Needs to correlate information across documents
- Complex reasoning required
- Important for identifying conflicts and gaps

**Pass 4: Synthesize** - `claude-3-5-sonnet-20241022` or `claude-3-opus-20240229`
- Final synthesis of all findings
- Requires highest quality output
- Use Opus for critical deals or when quality is paramount
- Use Sonnet for standard analyses

### 2. Real-Time AI Chat

**Quick Questions** - `claude-3-5-haiku-20241022`
- "What does this clause mean?"
- "Summarise this finding"
- Simple explanations
- Fast response time critical for UX

**Complex Questions** - `claude-3-5-sonnet-20241022`
- "How does this compare to market standard?"
- "What are the negotiation implications?"
- Questions requiring reasoning
- Follow-up analysis requests

### 3. Completeness Assessment

**Missing Document Importance** - `claude-3-5-sonnet-20241022`
- Requires understanding of transaction context
- Needs to assess risk of missing documents
- Legal expertise required
- Moderate frequency (once per assessment)

**Unanswered Question Importance** - `claude-3-5-sonnet-20241022`
- Same reasoning as missing documents
- Context-dependent assessment
- Quality more important than speed

### 4. Report Generation

**Preliminary Report (AI-Only)** - `claude-3-5-sonnet-20241022`
- Structured summarisation
- Clear, professional language
- Good balance of quality and cost

**Final Report (AI + Human)** - `claude-3-opus-20240229`
- Highest quality output
- Incorporates human annotations
- Client-facing document
- Worth the extra cost for final deliverable

**Request Letter Generation** - `claude-3-5-sonnet-20241022`
- Professional correspondence
- Clear, actionable requests
- Template-based with customisation

### 5. Human Review Assistance

**Finding Explanation** - `claude-3-5-haiku-20241022`
- Quick explanations for reviewers
- Simple clarifications
- High frequency, low complexity

**Reclassification Suggestions** - `claude-3-5-sonnet-20241022`
- Needs to understand severity implications
- Requires legal context
- Quality matters for accuracy

## Implementation Notes

### Environment Variables

```env
# Model configuration
CLAUDE_MODEL_EXTRACT=claude-3-5-haiku-20241022
CLAUDE_MODEL_ANALYSE=claude-3-5-sonnet-20241022
CLAUDE_MODEL_CROSSDOC=claude-3-5-sonnet-20241022
CLAUDE_MODEL_SYNTHESIZE=claude-3-5-sonnet-20241022
CLAUDE_MODEL_CHAT_QUICK=claude-3-5-haiku-20241022
CLAUDE_MODEL_CHAT_COMPLEX=claude-3-5-sonnet-20241022
CLAUDE_MODEL_COMPLETENESS=claude-3-5-sonnet-20241022
CLAUDE_MODEL_REPORT_PRELIMINARY=claude-3-5-sonnet-20241022
CLAUDE_MODEL_REPORT_FINAL=claude-3-opus-20240229
```

### Cost Estimation (Per Transaction)

Assuming 50 documents, 200 pages average:

| Function | Model | Estimated Tokens | Estimated Cost |
|----------|-------|------------------|----------------|
| Pass 1 Extract (50 docs) | Haiku | ~500K | ~$0.13 |
| Pass 2 Analyse (50 docs) | Sonnet | ~1M | ~$3.00 |
| Pass 3 Cross-Doc | Sonnet | ~200K | ~$0.60 |
| Pass 4 Synthesize | Sonnet | ~100K | ~$0.30 |
| Chat (10 questions avg) | Mixed | ~50K | ~$0.10 |
| Completeness Check | Sonnet | ~50K | ~$0.15 |
| Final Report | Opus | ~100K | ~$1.50 |
| **Total** | | | **~$5.78** |

*Costs are estimates based on typical usage. Actual costs may vary.*

### Quality vs Speed Decision Matrix

```
                    Speed Critical
                         │
            Haiku        │        Haiku
         (Simple Q&A)    │    (Extraction)
                         │
    ─────────────────────┼─────────────────────
                         │
           Sonnet        │        Opus
    (Complex Analysis)   │   (Final Reports)
                         │
                    Quality Critical
```

### Model Selection Function

```python
def select_model(task_type: str, quality_priority: str = "balanced") -> str:
    """Select appropriate Claude model based on task type and priority."""

    model_map = {
        "extract": "claude-3-5-haiku-20241022",
        "analyse": "claude-3-5-sonnet-20241022",
        "crossdoc": "claude-3-5-sonnet-20241022",
        "synthesize": "claude-3-5-sonnet-20241022",
        "chat_quick": "claude-3-5-haiku-20241022",
        "chat_complex": "claude-3-5-sonnet-20241022",
        "completeness": "claude-3-5-sonnet-20241022",
        "report_preliminary": "claude-3-5-sonnet-20241022",
        "report_final": "claude-3-opus-20240229",
    }

    # Override for quality priority
    if quality_priority == "highest":
        if task_type in ["synthesize", "report_preliminary"]:
            return "claude-3-opus-20240229"

    # Override for cost priority
    if quality_priority == "cost":
        if task_type in ["analyse", "crossdoc"]:
            return "claude-3-5-haiku-20241022"

    return model_map.get(task_type, "claude-3-5-sonnet-20241022")
```

## Best Practices

1. **Cache Responses**: Where possible, cache Claude responses for identical queries to reduce costs.

2. **Batch Processing**: Group similar requests to leverage Claude's context window efficiently.

3. **Fallback Strategy**: If Opus is unavailable or too slow, fall back to Sonnet for time-sensitive operations.

4. **Token Monitoring**: Track token usage per function to identify optimisation opportunities.

5. **Prompt Optimisation**: Shorter, more focused prompts reduce costs without sacrificing quality.

6. **Temperature Settings**:
   - Use `temperature=0` for extraction and structured outputs
   - Use `temperature=0.3` for analysis (some creativity)
   - Use `temperature=0.5` for chat responses (more natural)

## Future Considerations

- **Claude 4**: When available, evaluate for complex analysis tasks
- **Fine-tuning**: Consider fine-tuned models for domain-specific legal analysis
- **Hybrid Approach**: Combine multiple models in a single request for efficiency
