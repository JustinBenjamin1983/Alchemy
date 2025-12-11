# DD Enhanced - Multi-Pass Due Diligence POC

A proof-of-concept demonstrating architectural improvements to the Alchemy DD system.

## Overview

The existing Alchemy DD system scored 60/100 on a benchmark test due to these limitations:

1. **Per-document isolation** - Processes documents one at a time, missing cross-document issues
2. **No conflict detection** - Cannot identify when Document A contradicts Document B
3. **No financial calculations** - Quotes clauses but doesn't calculate exposures
4. **Simple severity levels** - Only Red/Amber/Green, no deal-blocker classification
5. **No cascade analysis** - Treats related findings as separate issues

This POC addresses these limitations with a **4-pass architecture**.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DD ENHANCED ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PASS 1: EXTRACT & INDEX                                        │
│  ├─ Extract structured data (dates, amounts, parties)          │
│  ├─ Identify change of control clauses                         │
│  └─ Build searchable index                                     │
│                         ↓                                       │
│  PASS 2: PER-DOCUMENT ANALYSIS                                  │
│  ├─ Analyze each contract for risks                            │
│  ├─ Reference docs (MOI, SHA) ALWAYS in context ← KEY          │
│  └─ Classify by severity AND deal impact                       │
│                         ↓                                       │
│  PASS 3: CROSS-DOCUMENT SYNTHESIS ← THE KEY IMPROVEMENT         │
│  ├─ ALL documents in single context                            │
│  ├─ Detect CONFLICTS between documents                         │
│  ├─ Map change of control CASCADE                              │
│  ├─ Validate authorizations (MOI vs Board Resolution)          │
│  └─ Build consent matrix                                       │
│                         ↓                                       │
│  PASS 4: DEAL SYNTHESIS                                         │
│  ├─ Calculate financial exposures                              │
│  ├─ Classify deal-blockers                                     │
│  ├─ Generate CP register                                       │
│  └─ Executive summary                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Key Improvements

### 1. Cross-Document Analysis (Pass 3)

The original system processes documents in isolation. This POC puts ALL documents in a single context to find issues that only appear when comparing documents:

```python
# Original system (per-document):
for doc in documents:
    analyze(doc)  # Never sees other documents

# Enhanced system (all documents):
analyze_all(documents)  # Sees everything together
```

### 2. Deal Impact Classification

Instead of just Red/Amber/Green, findings are classified by their impact on the transaction:

| Classification | Meaning |
|---------------|---------|
| `deal_blocker` | Transaction CANNOT close without resolution |
| `condition_precedent` | Must be resolved before closing |
| `price_chip` | Should reduce purchase price or require indemnity |
| `warranty_indemnity` | Allocate risk via sale agreement |
| `post_closing` | Can be addressed after completion |
| `noted` | For information only |

### 3. Cascade Analysis

Related findings (e.g., 7 "change of control" triggers across different contracts) are linked as a single cascade with a common trigger event and aggregated financial exposure.

### 4. Financial Calculations

The system calculates exposures rather than just quoting clauses:

```
Eskom Liquidated Damages:
  Annual contract value: R463.5M
  Monthly value: R38.625M
  Clause: 24 months average monthly value
  CALCULATED EXPOSURE: R927M
```

## Usage

### Prerequisites

```bash
# Install dependencies
cd /Users/jbenjamin/Web-Dev-Projects/Alchemy/server/opinion/api-2/dd_enhanced
pip install -r requirements.txt

# Set API key
export ANTHROPIC_API_KEY="your-anthropic-api-key"
```

### Running the POC

```bash
python run_poc.py
```

### Output

The POC generates:
1. **Console output** - Real-time progress and summary
2. **JSON results** - `output/dd_results_TIMESTAMP.json`
3. **Markdown report** - `output/dd_report_TIMESTAMP.md`

## Test Cases

The POC should correctly identify these issues that the original system missed:

### 1. MOI vs Board Resolution Conflict

- **MOI Clause 5.2**: Requires 75% shareholder approval for change of control
- **Board Resolution**: Only has board approval
- **Status**: Shareholder notification "NOT YET COMPLETED"
- **Expected**: Flag as **DEAL-BLOCKER**

### 2. Eskom Liquidated Damages Calculation

- **Contract**: 500,000 tonnes × R927/tonne = R463.5M annual
- **Clause 5**: "24 months of average monthly contract value"
- **Expected**: Calculate R463.5M ÷ 12 × 24 = **R77.25M** (or R927M)

### 3. Standard Bank Covenant Breach + CoC

- **Current status**: DSCR breach (Q3 2024: 1.2x vs required 1.5x)
- **Waiver**: Expires Q1 2025
- **CoC clause**: Allows acceleration
- **Expected**: Flag as **CRITICAL** with R285M exposure

### 4. Change of Control Cascade

- **Multiple documents** have CoC triggers
- **Expected**: Link as single cascade, not separate findings

## Directory Structure

```
dd_enhanced/
├── __init__.py
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── run_poc.py                   # Main entry point
├── config/
│   ├── __init__.py
│   └── blueprints/
│       └── mining_acquisition.yaml
├── core/
│   ├── __init__.py
│   ├── claude_client.py         # Claude API wrapper
│   ├── document_loader.py       # Load .docx files
│   ├── pass1_extract.py         # Pass 1: Extract
│   ├── pass2_analyze.py         # Pass 2: Analyze
│   ├── pass3_crossdoc.py        # Pass 3: Cross-doc (KEY)
│   └── pass4_synthesize.py      # Pass 4: Synthesize
├── prompts/
│   ├── __init__.py
│   ├── extraction.py            # Pass 1 prompts
│   ├── analysis.py              # Pass 2 prompts
│   ├── crossdoc.py              # Pass 3 prompts
│   └── synthesis.py             # Pass 4 prompts
├── models/
│   ├── __init__.py
│   ├── finding.py               # Finding model
│   ├── document.py              # Document model
│   └── cascade.py               # Cascade model
└── output/
    └── .gitkeep
```

## API Cost Estimate

For the 10 Karoo Mining test documents (~50,000 words):

| Pass | Calls | Est. Tokens | Est. Cost |
|------|-------|-------------|-----------|
| Pass 1 | 10 | ~30,000 | $0.15 |
| Pass 2 | 7 | ~50,000 | $0.25 |
| Pass 3 | 4 | ~100,000 | $0.50 |
| Pass 4 | 1 | ~20,000 | $0.10 |
| **Total** | **22** | **~200,000** | **~$1.00** |

## Comparison with Original System

| Capability | Original | Enhanced |
|------------|----------|----------|
| Cross-document conflicts | ❌ | ✅ |
| Cascade analysis | ❌ | ✅ |
| Financial calculations | ❌ | ✅ |
| Deal-blocker classification | ❌ | ✅ |
| Authorization validation | ❌ | ✅ |
| Consent matrix | Partial | ✅ |
| Reference doc context | ❌ | ✅ |

## Next Steps

If this POC demonstrates value, the architecture can be integrated into the main Alchemy system:

1. **Backend integration** - Add as Azure Function endpoints
2. **Frontend integration** - New DD report views
3. **Hybrid approach** - Use enhanced analysis for critical deals
4. **Performance optimization** - Parallel processing, caching

## License

Internal use only - Alchemy Law Africa / The AI Shop
