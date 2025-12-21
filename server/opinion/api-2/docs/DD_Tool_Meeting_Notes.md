# Alchemy DD Tool - Meeting Notes
## Enhancement Summary & Next Steps

**Date:** December 2024
**Prepared for:** Developer Meeting

---

## 1. What the Tool Did Well (Before Enhancements)

- Basic document ingestion and storage
- Text extraction from multiple file formats (PDF, DOCX, XLSX, etc.)
- Simple summarization of individual documents
- User-friendly upload interface
- Cloud-based storage and retrieval

---

## 2. What the Tool Was Lacking (Critical Gaps)

### No Cross-Document Analysis
- Each document processed in complete isolation
- Could not detect conflicts between documents (e.g., MOI vs Board Resolution)
- Critical deal-blocking issues went undetected

### No Financial Calculations
- Extracted text like "24 months average monthly value" but never calculated actual amounts
- Clients received vague descriptions instead of quantified exposures (e.g., R77M)

### Poor Severity Assessment
- Hardcoded confidence scores with no business logic
- Classified critical deal-blockers as routine "Amber" issues
- No distinction between "deal cannot close" vs "manageable with negotiation"

### No Legal Reasoning
- Pure pattern matching, not analysis
- No connection of related provisions across contracts
- Multiple separate findings instead of one mapped cascade effect

### No Institutional Knowledge
- Treated mining DD identically to tech DD
- No pre-defined expectations for document types
- No standard question libraries by transaction type

### Single-Pass Architecture
- One analysis run per document set
- No iterative refinement or synthesis
- Essentially an out-of-context summary generator

### Accuracy Result: 38%

---

## 3. Enhancements Made

### 3.1 5-Step Configuration Wizard
**What:** Structured wizard capturing transaction context before analysis
**Why:** Enables context-aware analysis; AI knows what to look for
- Step 1: Transaction type (14 types supported)
- Step 2: Deal context and known concerns
- Step 3: Focus areas and priorities
- Step 4: Key parties
- Step 5: Document checklist with readability validation

### 3.2 Transaction Type Blueprints
**What:** YAML configuration files defining analysis parameters per transaction type
**Why:** Domain-specific questions find domain-specific issues
- Mining, Real Estate, Energy, PE/VC, Financial Services, etc.
- Each blueprint includes expected documents, regulators, and tiered questions

### 3.3 4-Pass AI Processing Pipeline
**What:** Multi-pass architecture mirroring how attorneys review documents
**Why:** Iterative refinement catches what single-pass missed

| Pass | Model | Purpose |
|------|-------|---------|
| Pass 1: Extract | Haiku | Structured data extraction (fast, cheap) |
| Pass 2: Analyze | Sonnet | Per-document risk assessment |
| Pass 3: Cross-Doc | Sonnet | Conflict detection across documents |
| Pass 4: Synthesize | Sonnet | Consolidate findings, recommendations |

### 3.4 Chain-of-Thought (CoT) Reasoning
**What:** AI must show reasoning steps before classifying findings
**Why:** Transparent, auditable analysis; catches classification errors
- 6-step methodology: Identify → Context → Transaction Impact → Severity Reasoning → Deal Impact Reasoning → Financial Quantification
- 300+ CoT questions across all 15 transaction types

### 3.5 Cross-Document Analysis (Pass 3)
**What:** Dedicated pass comparing documents within clusters
**Why:** Catches conflicts the old system missed
- MOI requirements vs Board Resolution scope
- SHA restrictions vs deal terms
- Cascading effects across contracts

### 3.6 Financial Calculations
**What:** AI instructed to calculate exposures, show working
**Why:** Clients need numbers, not descriptions
- "24 months × R3.2M/month = R76.8M exposure"
- Calculation field in every finding

### 3.7 Deal Impact Classification
**What:** Categorize findings by transaction impact
**Why:** Prioritize what matters for deal execution
- Deal Blocker: Transaction cannot close
- Condition Precedent: Must resolve before closing
- Price Chip: Affects purchase price
- Warranty/Indemnity: Allocate via SPA
- Post-Closing: Address after completion

### 3.8 Questions Library
**What:** Tiered question system (Critical → Important → Deep Dive)
**Why:** Focus analysis on what matters most
- Base questions common to all deals
- Transaction-type specific questions
- User-defined priorities from wizard

### 3.9 Real-Time Progress Tracking
**What:** Pipeline rings showing pass-by-pass progress
**Why:** Attorney visibility into processing status
- Per-pass percentage, documents processed, elapsed time, estimated cost

### 3.10 Process Logging
**What:** Attorney-friendly log of all processing activities
**Why:** Transparency and debugging
- Document-level status, findings count, warnings, errors

### 3.11 Model Tier System
**What:** Configurable accuracy/cost tradeoff
**Why:** Balance accuracy needs with budget constraints

| Tier | Models | Accuracy | Cost/10 docs |
|------|--------|----------|--------------|
| Cost Optimized | H-S-S-S | ~89% | ~$3.50 |
| Balanced | H-S-O-S | ~92% | ~$7.50 |
| High Accuracy | H-S-O-O | ~95% | ~$11.50 |
| Maximum | H-O-O-O | ~97% | ~$35 |

### 3.12 Claude AI Migration
**What:** Moved from Azure OpenAI/Gemini to Claude (Anthropic)
**Why:**
- Superior legal reasoning and nuance detection
- 200K token context window (vs 128K)
- Better at expressing uncertainty
- More consistent structured outputs
- Less hallucination in document analysis

### Accuracy Result: 89% (up from 38%)

---

## 4. Next Steps: Increase Accuracy to 95%+

### 4.1 Implement High Accuracy Model Tier
- Use Claude Opus for Pass 3 (Cross-Doc) and Pass 4 (Synthesize)
- Projected improvement: +5-6% accuracy
- Cost increase: ~$8/10 documents

### 4.2 Optional Verification Pass (Pass 5)
- Opus-based review of critical/high severity findings only
- Catches misclassifications before report generation
- Projected improvement: +1-2% accuracy

### 4.3 Blueprint Enrichment
- Add more transaction-type specific questions based on attorney feedback
- Incorporate edge cases from real transactions
- Projected improvement: +1-2% accuracy

### 4.4 Code-Based Financial Calculations
- Move calculations from AI to deterministic code where possible
- Eliminates calculation errors
- Projected improvement: +1.5% accuracy

### 4.5 Human-AI Collaboration Model
- AI-First, Human-Verified workflow
- Mandatory attorney review for: deal blockers, critical severity, cross-doc conflicts
- Target: 98-99% accuracy with strategic human review
- Cost: 85-95% less than human-only DD

---

## 5. Next Steps: Scale to 500+ Documents

### 5.1 Current Limitation
- Context window constraints limit effective analysis to ~50-80 documents
- Larger DDs require architectural changes

### 5.2 Knowledge Graph Architecture
**What:** Structured representation of entities and relationships
**Why:** Enables targeted retrieval and cascade detection

- **Nodes:** Parties, Agreements, Obligations, Dates, Amounts
- **Edges:** requires_consent_from, references, conflicts_with, triggers
- **Benefit:** Query "all documents mentioning change of control" instead of reading everything

### 5.3 Hierarchical 5-Layer Pipeline

| Layer | Function | Output |
|-------|----------|--------|
| Layer 1 | Document extraction (parallel, 10-20 docs) | Structured JSON per doc |
| Layer 2 | Entity & relationship graph | Knowledge graph |
| Layer 3 | Smart clustering (graph-informed) | Analysis clusters |
| Layer 4 | Cluster analysis (Sonnet/Opus) | Cluster findings |
| Layer 5 | Cross-cluster synthesis (Opus) | Deal-level assessment |

### 5.4 Development Phases

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: Optimize Current | 2-3 weeks | Summary compression, enhanced clustering (150 docs) |
| Phase 2: Knowledge Graph | 4-5 weeks | Neo4j/AGE, entity extraction, relationship detection |
| Phase 3: Parallel Processing | 4-5 weeks | Job queue, 10-20 concurrent docs, incremental processing |
| Phase 4: Enterprise Features | 4-5 weeks | Graph visualization, collaboration, audit trail |

**Total Timeline:** 16-20 weeks

### 5.5 Target Metrics After Enterprise Scaling

| Metric | Current | Target |
|--------|---------|--------|
| Document capacity | 50-80 | 500+ |
| Processing time (100 docs) | N/A | 2-3 hours |
| Cost per document | ~$0.35 | ~$0.15 |
| Accuracy | 89% | 95%+ |

### 5.6 Recommended Immediate Action
- Approve Phase 1 (2-3 weeks) to validate summary compression approach
- Provides immediate value (150-document capability)
- De-risks larger architectural changes

---

## 6. Key Takeaways

1. **Accuracy improved from 38% to 89%** through architectural redesign and Claude AI
2. **CoT reasoning** ensures transparent, auditable analysis
3. **Cross-document analysis** catches conflicts the old system missed
4. **95%+ accuracy achievable** with High Accuracy tier + verification pass
5. **500+ document scale requires Knowledge Graph architecture** (16-20 week build)
6. **Phase 1 recommended** as immediate next step (2-3 weeks, 150-doc capability)

---

**Document Version:** 1.0
**Status:** Meeting Reference Document
