# DD Accuracy Upgrade Implementation Plan

**Created**: 21 December 2025
**Target Accuracy**: 64% → 85%+
**Estimated Effort**: 3-4 days

---

## Executive Summary

Following evaluation of the DD tool against a Karoo Mining test case, we identified key accuracy gaps:
- Financial calculation errors (12x error on Eskom liquidated damages)
- Missing BEE/ownership analysis
- Limited financial trend analysis
- Action items instead of strategic questions
- Report duplication
- No verification pass for deal-blockers

This plan addresses all gaps through 7 coordinated upgrades.

---

## Upgrade Overview

| # | Upgrade | Impact | Effort | Dependencies |
|---|---------|--------|--------|--------------|
| 1 | BALANCED model tier | High | 1 hour | None |
| 2 | BEE/Ownership in blueprints | Medium | 2 hours | None |
| 3 | Financial trend analysis | Medium | 1 hour | None |
| 4 | Strategic questions in Pass 4 | Medium | 1 hour | None |
| 5 | Report deduplication | Low | 2 hours | None |
| 6 | Code-based calculations | **Critical** | 4-6 hours | Opus design |
| 7 | Pass 5 verification | High | 3-4 hours | #1, #6 |

---

## Phase 1: Quick Wins (Day 1 Morning)

### Upgrade 1: Change Default Model Tier to BALANCED

**Objective**: Use Opus for Pass 3 (cross-document analysis) where complex reasoning matters most.

**Files to Modify**:
```
server/opinion/api-2/dd_enhanced/core/claude_client.py
```

**Changes**:
```python
# Line 168 - Change default from COST_OPTIMIZED to BALANCED
@dataclass
class ClaudeClient:
    model_tier: ModelTier = field(default=ModelTier.BALANCED)  # Changed from COST_OPTIMIZED
```

**Alternative**: Set environment variable `DD_MODEL_TIER=balanced` in Azure Function settings.

**Verification**:
- Run a test analysis
- Check logs confirm Opus used for Pass 3
- Verify cost increase is within expected range (~$4-6 vs ~$1.60)

**Rollback**: Change back to `ModelTier.COST_OPTIMIZED` or remove env var.

---

### Upgrade 3: Financial Trend Analysis in Pass 2

**Objective**: Automatically calculate YoY trends for financial documents.

**Files to Modify**:
```
server/opinion/api-2/dd_enhanced/prompts/analysis.py
```

**Changes** (add to `_build_cot_methodology_section`):

```python
# After Step 6, add Step 7
**Step 7 - FINANCIAL TREND ANALYSIS:** For financial statements and reports:
- Calculate year-over-year revenue change: ((Current - Prior) / Prior) × 100
- Calculate margin trends: Current margin % vs Prior margin %
- Calculate cash position change
- FLAG any metric declining >10% or margin compression >5 percentage points
- FLAG going concern indicators: negative working capital, audit qualifications, cash burn

Format trends as: "Revenue: R45.2M → R38.6M (-14.6% YoY) [FLAGGED: >10% decline]"
```

**Also add to document-type specific prompts** for financial documents:

```python
FINANCIAL_TREND_PROMPT = """
MANDATORY FOR FINANCIAL DOCUMENTS:
Extract and calculate the following trends:
1. Revenue: Current year vs Prior year (calculate % change)
2. Gross Margin: Current % vs Prior % (calculate change in percentage points)
3. Net Profit: Current vs Prior (calculate % change)
4. Cash/Cash Equivalents: Current vs Prior
5. Working Capital: Current Assets - Current Liabilities (both years)
6. Debt levels: Total borrowings current vs prior

Present as a trend table with arrows (↑/↓) and flag concerning trends.
"""
```

**Verification**:
- Run analysis on AFS document
- Confirm trend calculations appear in findings
- Verify flagging works for >10% declines

---

### Upgrade 4: Strategic Questions in Pass 4

**Objective**: Generate investigative questions, not just action items.

**Files to Modify**:
```
server/opinion/api-2/dd_enhanced/prompts/synthesis.py (or equivalent)
server/opinion/api-2/dd_enhanced/core/pass4_synthesize.py
```

**Changes** (add to synthesis prompt):

```python
STRATEGIC_QUESTIONS_PROMPT = """
## STRATEGIC QUESTIONS FOR FURTHER INVESTIGATION

Generate 8-12 strategic questions that a senior M&A partner would ask. These should NOT be document requests - they should probe deeper issues.

Categories of questions to include:

**Valuation & Commercial:**
- Questions challenging whether the price is justified
- Questions about revenue sustainability
- Questions about customer concentration risk

**Strategic & Operational:**
- Questions about post-acquisition integration
- Questions about key person dependencies
- Questions about competitive position

**Risk & Liability:**
- Questions about worst-case exposure scenarios
- Questions about indemnity adequacy
- Questions about insurance coverage gaps

**Regulatory & Compliance:**
- Questions about pending regulatory changes
- Questions about compliance history
- Questions about license/permit renewals

FORMAT each question as:
{
  "question": "What caused the 14.5% revenue decline and is the trend continuing in 2024?",
  "category": "Valuation & Commercial",
  "priority": "critical",
  "documents_to_review": ["Management accounts 2024", "Sales pipeline"],
  "who_should_answer": "Target CFO / Management"
}

IMPORTANT: Questions should probe "WHY" not just "WHAT". They should challenge assumptions and identify information gaps.
"""
```

**Verification**:
- Run synthesis pass
- Confirm output includes `strategic_questions` array
- Verify questions are investigative, not just "obtain X document"

---

## Phase 2: Blueprint Enhancement (Day 1 Afternoon)

### Upgrade 2: BEE/Ownership Analysis in All Blueprints

**Objective**: Add ownership structure and regulatory compliance questions to all transaction blueprints.

**Files to Modify**:
```
server/opinion/api-2/dd_enhanced/config/blueprints/*.yaml (all 15 files)
```

**New Universal Section** (add to each blueprint):

```yaml
# Add to tier_1_questions in each blueprint
ownership_regulatory:
  - question: "What is the current ownership structure of the target, including all shareholders and their respective holdings?"
    cot_hint: "Map complete ownership chain. Identify any regulatory-sensitive shareholdings."

  - question: "How does this transaction change the ownership structure, and what regulatory thresholds are crossed?"
    cot_hint: "Calculate post-transaction ownership. Check if any regulatory notification/approval thresholds are triggered."

  - question: "What licenses, permits, or regulatory approvals are tied to the current ownership structure?"
    cot_hint: "List all ownership-dependent authorizations. Flag any that require re-application or notification on change of control."

  - question: "Are there any ownership restrictions in the company's constitutional documents, shareholder agreements, or regulatory conditions?"
    cot_hint: "Check MOI, SHA, license conditions for ownership caps, pre-emption rights, or prohibited transfers."

  - question: "What are the consequences of non-compliance with ownership-based regulatory requirements post-transaction?"
    cot_hint: "Identify penalties, license revocation risks, forced divestiture requirements."
```

**Mining-Specific Additions** (add to `mining_resources.yaml` and `mining_acquisition.yaml`):

```yaml
bee_mining_charter:
  - question: "What is the current HDSA/BEE ownership percentage and how is it calculated?"
    cot_hint: "Verify BEE ownership calculation methodology. Check if flow-through principles apply."

  - question: "How does this 100% acquisition affect Mining Charter compliance, given the acquirer's ownership structure?"
    cot_hint: "Post-transaction HDSA % = Acquirer's HDSA % × 100%. If acquirer is foreign/non-HDSA, target becomes 0% HDSA."

  - question: "What is the Mining Charter minimum HDSA ownership requirement for this commodity and when must it be achieved?"
    cot_hint: "Mining Charter III requires 30% HDSA for new rights. Check commodity-specific requirements."

  - question: "What mechanisms exist to restore BEE compliance post-acquisition (employee trusts, community trusts, BEE partners)?"
    cot_hint: "Identify existing BEE structures. Assess if they survive the transaction or need reconstitution."

  - question: "What are the consequences of Mining Charter non-compliance for the mining right?"
    cot_hint: "Section 47 MPRDA allows Minister to suspend/cancel rights for non-compliance. Check enforcement history."
```

**Financial Services Additions** (add to `financial_services.yaml` and `banking_finance.yaml`):

```yaml
fais_prudential:
  - question: "What FSP licenses does the target hold and do they have ownership change notification requirements?"
    cot_hint: "Check FAIS license conditions. Section 20 changes require FSCA notification."

  - question: "Does the transaction trigger Prudential Authority approval for significant ownership changes?"
    cot_hint: "Banks Act / Insurance Act require approval for >15%/25%/49% ownership changes."
```

**Implementation Script** (to add to all blueprints):

```python
# Create: server/opinion/api-2/dd_enhanced/config/blueprints/add_ownership_questions.py

import yaml
from pathlib import Path

UNIVERSAL_OWNERSHIP_QUESTIONS = [
    {
        "question": "What is the current ownership structure of the target?",
        "cot_hint": "Map complete ownership chain including ultimate beneficial owners."
    },
    # ... rest of questions
]

def add_to_all_blueprints():
    blueprint_dir = Path(__file__).parent
    for yaml_file in blueprint_dir.glob("*.yaml"):
        with open(yaml_file, 'r') as f:
            blueprint = yaml.safe_load(f)

        # Add ownership_regulatory to tier_1_questions
        if 'tier_1_questions' not in blueprint:
            blueprint['tier_1_questions'] = {}

        blueprint['tier_1_questions']['ownership_regulatory'] = UNIVERSAL_OWNERSHIP_QUESTIONS

        with open(yaml_file, 'w') as f:
            yaml.dump(blueprint, f, default_flow_style=False, allow_unicode=True)

        print(f"Updated: {yaml_file.name}")

if __name__ == "__main__":
    add_to_all_blueprints()
```

**Verification**:
- Run script to update all blueprints
- Run analysis on a mining transaction
- Confirm BEE questions appear in findings
- Verify ownership structure is analyzed

---

## Phase 3: Code-Based Financial Calculations (Day 2)

### Upgrade 6: Financial Calculation Engine

**Objective**: Move all arithmetic out of AI into Python code.

**Awaiting**: Opus design for formula taxonomy and architecture.

**Preliminary Architecture**:

```
New Files to Create:
server/opinion/api-2/dd_enhanced/core/calculations/
├── __init__.py
├── engine.py              # Main calculation orchestrator
├── formulas.py            # Formula definitions and implementations
├── extractor.py           # AI extraction prompts for formula components
├── validator.py           # Sanity checks and validation rules
└── schemas.py             # Pydantic models for calculation inputs/outputs
```

**Integration Points**:

```python
# In pass2_analyze.py - after AI analysis, before saving findings
from dd_enhanced.core.calculations import CalculationEngine

async def analyze_document(...):
    # Existing AI analysis
    findings = await client.complete_analysis(...)

    # NEW: Process any calculable findings through calculation engine
    calc_engine = CalculationEngine()
    for finding in findings:
        if finding.get('has_financial_exposure'):
            extraction = finding.get('calculation_extraction')
            if extraction:
                result = calc_engine.calculate(extraction)
                finding['calculated_exposure'] = result.value
                finding['calculation_audit'] = result.audit_trail
                finding['calculation_confidence'] = result.confidence
```

**Extraction Schema** (preliminary):

```python
class CalculationExtraction(BaseModel):
    """What AI extracts from document for calculation."""
    formula_type: str  # e.g., "liquidated_damages", "severance", "penalty"

    # Core values
    principal_amount: Optional[float]
    rate: Optional[float]
    rate_unit: Optional[str]  # "per_tonne", "per_month", "percentage"
    quantity: Optional[float]
    quantity_unit: Optional[str]  # "tonnes", "units", "employees"
    period: Optional[float]
    period_unit: Optional[str]  # "months", "years", "days"

    # For percentage calculations
    base_value: Optional[float]
    percentage: Optional[float]

    # For tiered calculations
    tiers: Optional[List[TierDefinition]]

    # Metadata
    source_clause: str
    document_name: str
    page_reference: Optional[str]
    currency: str = "ZAR"

    # For edge cases
    is_complex: bool = False
    complexity_reason: Optional[str]
    manual_review_required: bool = False
```

**Formula Registry** (preliminary):

```python
FORMULA_REGISTRY = {
    "liquidated_damages": {
        "formula": "quantity * rate * (period / period_divisor)",
        "variables": ["quantity", "rate", "period"],
        "period_divisor": {"months": 12, "years": 1, "days": 365},
        "validation": {
            "max_reasonable_multiple": 5,  # Flag if > 5x transaction value
        }
    },
    "severance": {
        "formula": "salary * multiplier * notice_months",
        "variables": ["salary", "multiplier", "notice_months"],
        "common_multipliers": [1, 2, 3],  # For validation
    },
    "provision_shortfall": {
        "formula": "required_amount - current_provision",
        "variables": ["required_amount", "current_provision"],
    },
    "percentage_change": {
        "formula": "((new_value - old_value) / old_value) * 100",
        "variables": ["new_value", "old_value"],
    },
    # ... more formulas from Opus design
}
```

**Validation Rules**:

```python
class CalculationValidator:
    def validate(self, result: CalculationResult, context: Dict) -> List[ValidationWarning]:
        warnings = []

        # Sanity check: exposure vs transaction value
        if context.get('transaction_value'):
            ratio = result.value / context['transaction_value']
            if ratio > 1.0:
                warnings.append(ValidationWarning(
                    level="critical",
                    message=f"Calculated exposure ({result.formatted}) exceeds transaction value",
                    suggestion="Verify calculation inputs and formula"
                ))
            elif ratio > 0.5:
                warnings.append(ValidationWarning(
                    level="high",
                    message=f"Calculated exposure is {ratio:.0%} of transaction value",
                    suggestion="Confirm this material exposure with client"
                ))

        # Unit consistency
        if result.has_unit_mismatch:
            warnings.append(ValidationWarning(
                level="medium",
                message="Possible unit mismatch in calculation",
                suggestion="Verify quantity and rate units are compatible"
            ))

        return warnings
```

**Verification**:
- Unit tests for each formula type
- Integration test with Eskom example (must produce R77.25M)
- Validation test (exposure > purchase price triggers warning)

---

## Phase 4: Pass 5 Verification (Day 3)

### Upgrade 7: Opus Verification Pass

**Objective**: Final Opus review of all deal-blockers and critical findings.

**Files to Create**:
```
server/opinion/api-2/dd_enhanced/core/pass5_verify.py
server/opinion/api-2/dd_enhanced/prompts/verification.py
```

**Architecture**:

```python
# pass5_verify.py

async def run_verification_pass(
    client: ClaudeClient,
    deal_blockers: List[Finding],
    conditions_precedent: List[Finding],
    critical_findings: List[Finding],
    transaction_context: Dict,
    calculation_results: List[CalculationResult]
) -> VerificationResult:
    """
    Pass 5: Opus verification of deal-critical items.

    This pass:
    1. Reviews each deal-blocker for correct classification
    2. Verifies all financial calculations
    3. Checks for missed deal-blockers
    4. Provides final risk assessment
    """

    prompt = build_verification_prompt(
        deal_blockers=deal_blockers,
        conditions_precedent=conditions_precedent,
        critical_findings=critical_findings,
        transaction_context=transaction_context,
        calculation_results=calculation_results
    )

    # Always use Opus for verification
    response = await client.complete_verification(
        system=VERIFICATION_SYSTEM_PROMPT,
        prompt=prompt,
        max_tokens=8000
    )

    return parse_verification_response(response)
```

**Verification Prompt**:

```python
VERIFICATION_SYSTEM_PROMPT = """You are a senior M&A partner conducting final review of a due diligence report.

Your role is to:
1. CHALLENGE each deal-blocker classification - is it truly a blocker or just a condition?
2. VERIFY all financial calculations - check the arithmetic and assumptions
3. IDENTIFY any missed deal-blockers from the findings
4. ASSESS overall transaction risk

You must be CRITICAL and SKEPTICAL. Challenge assumptions. Question classifications.

If you find an error, clearly explain:
- What is wrong
- What the correct answer should be
- Why this matters for the transaction"""

VERIFICATION_PROMPT_TEMPLATE = """
## TRANSACTION CONTEXT
- Target: {target_name}
- Transaction Type: {transaction_type}
- Purchase Price: {purchase_price}
- Key Parties: {key_parties}

## DEAL-BLOCKERS IDENTIFIED ({blocker_count})
{deal_blockers_formatted}

## CONDITIONS PRECEDENT IDENTIFIED ({cp_count})
{conditions_precedent_formatted}

## CRITICAL FINDINGS ({critical_count})
{critical_findings_formatted}

## FINANCIAL CALCULATIONS PERFORMED
{calculations_formatted}

---

## YOUR VERIFICATION TASKS

### Task 1: Deal-Blocker Review
For each deal-blocker, answer:
- Is this correctly classified as a BLOCKER (cannot close without resolution)?
- Or should it be a CONDITION PRECEDENT (must be satisfied but achievable)?
- Or is it actually just a PRICE CHIP (affects valuation, not structure)?

### Task 2: Calculation Verification
For each financial calculation:
- Is the formula correct for this type of exposure?
- Are the input values correctly extracted?
- Is the arithmetic correct?
- Is the result reasonable in context?

### Task 3: Missed Issues Check
Based on the findings, are there any DEAL-BLOCKERS that were missed?
Consider:
- Regulatory approvals that would prevent closing
- Third-party consents that are genuinely unobtainable
- Conditions that create immediate breach post-closing

### Task 4: Overall Risk Assessment
Provide:
- Total quantified exposure
- Top 3 risks by impact
- Recommended transaction structure changes
- Go/No-Go recommendation with reasoning

---

## OUTPUT FORMAT
{
  "deal_blocker_reviews": [...],
  "calculation_verifications": [...],
  "missed_issues": [...],
  "overall_assessment": {
    "total_exposure": "R___",
    "risk_rating": "HIGH/MEDIUM/LOW",
    "top_risks": [...],
    "structure_recommendations": [...],
    "go_no_go": "GO/CONDITIONAL GO/NO GO",
    "reasoning": "..."
  }
}
"""
```

**Integration into Pipeline**:

```python
# In parallel_orchestrator.py

async def run_full_analysis(self, ...):
    # Existing passes
    pass1_results = await self._run_pass1(documents)
    pass2_results = await self._run_pass2(documents, pass1_results)
    pass3_results = await self._run_pass3(pass2_results)
    pass4_results = await self._run_pass4(pass3_results)

    # NEW: Pass 5 verification (only for completed analyses)
    if self.config.enable_verification_pass:
        pass5_results = await self._run_pass5(
            deal_blockers=pass4_results.deal_blockers,
            conditions_precedent=pass4_results.conditions_precedent,
            critical_findings=pass4_results.critical_findings,
            calculation_results=self.calculation_engine.results
        )

        # Merge verification results
        final_results = self._merge_verification(pass4_results, pass5_results)
    else:
        final_results = pass4_results

    return final_results
```

**Cost Consideration**:
- Pass 5 processes only deal-blockers and critical findings (small context)
- Estimated: 2,000-5,000 input tokens, 2,000-4,000 output tokens
- Cost: ~$0.30-0.80 per analysis (Opus pricing)

**Verification**:
- Test with Karoo case - should catch Eskom calculation error
- Verify deal-blocker classifications are reviewed
- Confirm missed issues are flagged

---

## Phase 5: Report Deduplication (Day 3)

### Upgrade 5: Report Deduplication

**Objective**: Eliminate repeated findings in exported report.

**Files to Modify**:
```
server/opinion/api-2/DDExportReport/__init__.py
```

**Changes**:

```python
def deduplicate_findings(findings: List[Finding]) -> List[Finding]:
    """
    Remove duplicate findings while preserving the most detailed version.

    Deduplication criteria:
    - Same document + same clause reference = duplicate
    - Same issue description (fuzzy match) = duplicate
    """
    seen = {}
    unique = []

    for finding in findings:
        # Create dedup key
        key = (
            finding.get('document_id'),
            finding.get('clause_reference'),
            normalize_text(finding.get('description', ''))[:100]
        )

        if key not in seen:
            seen[key] = finding
            unique.append(finding)
        else:
            # Keep the more detailed version
            existing = seen[key]
            if len(finding.get('description', '')) > len(existing.get('description', '')):
                unique.remove(existing)
                unique.append(finding)
                seen[key] = finding

    return unique

def build_report_sections(findings: List[Finding]) -> Dict:
    """
    Build report with findings appearing once, referenced elsewhere.
    """
    # Deduplicate first
    unique_findings = deduplicate_findings(findings)

    # Assign unique IDs
    for i, finding in enumerate(unique_findings):
        finding['report_ref'] = f"F{i+1:03d}"

    # Executive summary references findings by ID
    exec_summary = build_executive_summary(unique_findings)  # Uses report_ref

    # Category sections contain full details (once only)
    category_sections = build_category_sections(unique_findings)

    # Severity breakdown references by ID only
    severity_breakdown = build_severity_references(unique_findings)  # Just refs

    return {
        "executive_summary": exec_summary,
        "findings_by_category": category_sections,
        "severity_index": severity_breakdown  # Reference table, not full content
    }
```

**Report Structure Change**:

```
BEFORE (duplicated):
├── Executive Summary
│   └── [Full finding details repeated]
├── Findings by Category
│   └── [Full finding details]
├── Findings by Severity
│   └── [Full finding details repeated again]

AFTER (deduplicated):
├── Executive Summary
│   └── [Finding references: F001, F003, F007...]
├── Findings Detail (ONCE)
│   └── [Full finding details with IDs]
├── Severity Index
│   └── [Table: ID | Severity | Category | Summary]
```

---

## Testing Plan

### Regression Test Case: Karoo Mining

Run full analysis on Karoo test documents after all upgrades.

**Expected Improvements**:

| Metric | Before | After Target |
|--------|--------|--------------|
| Critical Red Flags | 65% | 85% |
| Amber Flags | 62% | 80% |
| Cross-Document | 73% | 85% |
| Intelligent Questions | 53% | 80% |
| Missing Docs Flagged | 60% | 75% |
| Calculation Accuracy | 0% (12x error) | 100% |
| Overall | 64% | 85%+ |

**Specific Validations**:

1. **Eskom Calculation**: Must show R77,250,000 (not R926.7M)
2. **BEE Analysis**: Must identify HDSA ownership impact
3. **Financial Trends**: Must calculate 14.5% revenue decline
4. **Strategic Questions**: Must include valuation challenge questions
5. **Report Length**: Should be 20-30% shorter (no duplication)

---

## Rollout Plan

### Stage 1: Development Environment
- Implement all changes
- Run Karoo regression test
- Fix any issues

### Stage 2: Staging Environment
- Deploy to staging
- Run 3-5 test transactions
- Validate costs within budget

### Stage 3: Production
- Deploy with feature flags
- Enable for internal testing first
- Monitor costs and accuracy
- Full rollout after validation

---

## Cost Impact Analysis

| Component | Current | After Upgrade | Delta |
|-----------|---------|---------------|-------|
| Pass 1 (Haiku) | $0.05 | $0.05 | - |
| Pass 2 (Sonnet) | $0.40 | $0.40 | - |
| Pass 3 (Sonnet→Opus) | $0.40 | $1.50 | +$1.10 |
| Pass 4 (Sonnet) | $0.35 | $0.35 | - |
| Pass 5 (NEW - Opus) | - | $0.50 | +$0.50 |
| Calculations | - | $0.05 | +$0.05 |
| **Total per 10 docs** | **$1.60** | **$3.25** | **+$1.65** |

**Cost Justification**:
- 2x cost for significant accuracy improvement
- Still far cheaper than human review ($500+/hour)
- Prevents professional liability from calculation errors

---

## Dependencies & Blockers

| Upgrade | Blocked By |
|---------|------------|
| 1. Model tier | None |
| 2. BEE questions | None |
| 3. Financial trends | None |
| 4. Strategic questions | None |
| 5. Deduplication | None |
| 6. Calculations | **Opus design (in progress)** |
| 7. Pass 5 | #6 (needs calculation results) |

---

## Next Steps

1. [ ] Receive Opus design for calculation engine
2. [ ] Implement Upgrade 1 (model tier) - 1 hour
3. [ ] Implement Upgrade 3 (financial trends) - 1 hour
4. [ ] Implement Upgrade 4 (strategic questions) - 1 hour
5. [ ] Implement Upgrade 2 (BEE questions) - 2 hours
6. [ ] Implement Upgrade 6 (calculations) - 4-6 hours
7. [ ] Implement Upgrade 7 (Pass 5) - 3-4 hours
8. [ ] Implement Upgrade 5 (deduplication) - 2 hours
9. [ ] Run Karoo regression test
10. [ ] Deploy to staging
