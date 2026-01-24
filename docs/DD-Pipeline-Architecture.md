# Due Diligence Pipeline Architecture

## Comprehensive Technical Documentation

**Version:** 2.0 (with Human-in-the-Loop Checkpoints)
**Last Updated:** January 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Pipeline Overview](#2-pipeline-overview)
3. [Pre-Processing Phase](#3-pre-processing-phase)
   - 3.1 Wizard (4 Steps)
   - 3.2 Document Classification
   - 3.3 Checkpoint A: Missing Documents
   - 3.4 Readability Check
   - 3.5 Entity Mapping **(NEW)**
4. [Processing Phase (7-Pass Pipeline)](#4-processing-phase-7-pass-pipeline)
   - 4.1 Materiality Thresholds
   - 4.2 Pass 1: Extract (+ Document Reference Extraction)
   - 4.3 Pass 2: Analyze (+ Blueprint Q&A + Action Categories)
   - 4.4 Checkpoint C: Post-Analysis Validation (4-step wizard)
   - 4.5 Pass 3: Calculate
   - 4.6 Pass 4: Cross-Doc (Opus ALWAYS)
   - 4.7 Pass 5: Aggregate
   - 4.8 Pass 6: Synthesize
   - 4.9 Pass 7: Verify (Opus ALWAYS)
5. [Human-in-the-Loop Checkpoints](#5-human-in-the-loop-checkpoints)
6. [Post-Processing Phase](#6-post-processing-phase)
7. [Data Models & Storage](#7-data-models--storage)
8. [Blueprint System](#8-blueprint-system)
   - 8.1 Blueprint Structure
   - 8.2 Blueprint Components
   - 8.3 Question Prioritization
   - 8.4 Statutory Framework **(NEW)**
   - 8.5 Prompt Construction & Confidence Calibration **(NEW)**
9. [API Endpoints](#9-api-endpoints)
10. [UI Components](#10-ui-components)
11. [Cost & Token Management](#11-cost--token-management)
12. [Error Handling & Recovery](#12-error-handling--recovery)

---

## 1. Executive Summary

The Alchemy DD Pipeline is a multi-pass document analysis system that performs automated due diligence on legal and financial documents. It combines:

- **AI-powered analysis** using Claude (Haiku, Sonnet, Opus models)
- **Python-based calculations** for financial computations
- **Human-in-the-loop validation** for accuracy and context
- **Blueprint-driven questions** tailored to transaction types

### Key Statistics
- **7 processing passes** (5 AI + 2 Python)
- **Entity mapping** in pre-processing for preventing entity confusion
- **3 validation checkpoints** (A: Missing docs, B: Entity confirmation, C: Post-analysis)
- **Materiality thresholds** based on transaction value (classifies, doesn't filter)
- **Confidence calibration** on all findings
- **Unlimited refinement cycles** for report iteration
- **Version-controlled reports** (V1, V2, V3, etc.)

---

## 2. Pipeline Overview

### 2.1 High-Level Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PRE-PROCESSING PHASE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Wizard (4 steps)     → User enters transaction details + uploads ZIP    │
│  2. Classification       → AI categorizes documents into folders            │
│  3. Checkpoint A         → Missing docs validation                          │
│  4. Readability Check    → Validate docs + convert PPTX/DOCX/XLSX to PDF    │
│  5. Entity Mapping       → Map all entities to target, detect confusion     │
│  6. Checkpoint B         → User confirms/corrects entity relationships      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PROCESSING PHASE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Materiality Thresholds] → Set thresholds based on transaction value       │
│  Pass 1: EXTRACT         → Haiku extracts data + document references        │
│  Pass 2: ANALYZE         → Sonnet analyzes risks + answers Blueprint Q&A    │
│  ────────────────────────────────────────────────────────────────────────── │
│  Checkpoint C            → Human validates understanding + financials       │
│  ────────────────────────────────────────────────────────────────────────── │
│  Pass 3: CALCULATE       → Python computes financial exposures              │
│  Pass 4: CROSS-DOC       → Opus detects conflicts + missing doc analysis    │
│  Pass 5: AGGREGATE       → Python combines calculations                     │
│  Pass 6: SYNTHESIZE      → Sonnet generates executive summary + W&I         │
│  Pass 7: VERIFY          → Opus performs final QC                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           POST-PROCESSING PHASE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Store & Display       → Save Report V1, display in Findings Explorer       │
│  Refinement Loop       → User refines via Ask AI → V2, V3, etc.             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Model Usage by Pass

| Pass | Name | Model | Purpose |
|------|------|-------|---------|
| Pre-processing | Entity Map | Claude Haiku | Entity extraction and relationship mapping |
| Pass 1 | Extract | Claude Haiku | Fast structured data extraction |
| Pass 2 | Analyze | Claude Sonnet* | Detailed risk analysis |
| Checkpoint C | Validation | Human | 4-step confirmation wizard |
| Pass 3 | Calculate | Python | Mathematical computations |
| Pass 4 | Cross-Doc | **Claude Opus** | Complex cross-document reasoning (ALWAYS Opus) |
| Pass 5 | Aggregate | Python | Combine and summarize calculations |
| Pass 6 | Synthesize | Claude Sonnet* | Executive summary generation |
| Pass 7 | Verify | **Claude Opus** | Final quality control (ALWAYS Opus) |

*Sonnet by default; Opus for HIGH_ACCURACY/MAXIMUM_ACCURACY tiers

---

## 3. Pre-Processing Phase

### 3.1 Wizard (4 Steps)

**Purpose:** Collect transaction context from user before processing begins.

**UI Component:** `ui/src/pages/DD/Wizard/DDProjectWizard.tsx`

#### Step 1: Transaction Basics
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `transactionName` | string | Yes | Name of the DD project |
| `transactionType` | enum | Yes | mining_resources, ma_corporate, banking_finance, ip_technology |
| `clientName` | string | Yes | Name of the client |
| `targetEntityName` | string | Yes | Name of the target company |
| `clientRole` | enum | Yes | buyer, seller, investor, lender |
| `dealStructure` | enum | Yes | share_sale, asset_sale, merger, etc. |
| `estimatedValue` | number | No | Estimated transaction value (ZAR) |
| `targetClosingDate` | date | No | Expected closing date |

#### Step 2: Deal Context
| Field | Type | Description |
|-------|------|-------------|
| `dealRationale` | text | Why is this transaction happening? |
| `knownConcerns` | string[] | Tags for known issues (e.g., "environmental", "BEE compliance") |

#### Step 3: Focus Areas
| Field | Type | Description |
|-------|------|-------------|
| `criticalPriorities` | string[] | What must be thoroughly checked |
| `knownDealBreakers` | string[] | Issues that would kill the deal |
| `deprioritizedAreas` | string[] | Areas that can be given less attention |

#### Step 4: Key Stakeholders
| Field | Type | Description |
|-------|------|-------------|
| `keyIndividuals` | string[] | Important people (executives, founders) |
| `keySuppliers` | string[] | Critical suppliers |
| `keyCustomers` | {name, description, exposure}[] | Major customers with revenue exposure |
| `keyLenders` | {name, description, facilityAmount}[] | Lenders and facility details |
| `keyRegulators` | string[] | Relevant regulatory bodies |
| `shareholders` | {name, percentage}[] | Shareholder structure |

**Output:** `DDProjectSetup` object stored in `DueDiligence.project_setup` (JSON)

**Briefing String:** All wizard data is also formatted into a human-readable `briefing` string:
```
Transaction Type: mining_resources
Client Name: ABC Holdings
Target Entity: XYZ Mining (Pty) Ltd
Client Role: buyer
Deal Structure: share_sale
Estimated Value: R150,000,000
Target Closing: 2026-03-15

Deal Rationale: Strategic acquisition to expand mining portfolio...

Known Concerns: environmental liability, BEE compliance, mining rights renewal

Critical Priorities: Environmental permits, Mining rights validity
Known Deal Breakers: Unresolved environmental litigation
...
```

---

### 3.2 Document Classification

**Purpose:** Automatically categorize uploaded documents into standardized folders.

**Endpoint:** `POST /api/dd-classify-documents`
**Backend:** `DDClassifyDocuments/__init__.py`
**Model:** Claude Haiku

#### Folder Categories
| Code | Category | Example Documents |
|------|----------|-------------------|
| 01_Corporate | Corporate/Governance | MOI, Shareholders Agreement, Board Resolutions |
| 02_Commercial | Commercial Contracts | MSA, Supply Agreements, Customer Contracts |
| 03_Financial | Financial Documents | AFS, Loan Agreements, Management Accounts |
| 04_Regulatory | Regulatory/Compliance | Mining Rights, Environmental Permits, BEE Certificates |
| 05_Employment | Employment | Employment Contracts, Union Agreements |
| 06_Property | Property/Real Estate | Leases, Title Deeds, Servitudes |
| 07_Insurance | Insurance | Policies, Surety Bonds |
| 08_Litigation | Litigation | Court Documents, Legal Opinions |
| 09_Tax | Tax | Tax Returns, SARS Correspondence |
| 99_Needs_Review | Unclassified | Documents AI couldn't confidently classify |

#### Classification Output (per document)
```json
{
  "category": "04_Regulatory",
  "subcategory": "Mining Rights",
  "document_type": "Mining Right Certificate",
  "confidence": 92,
  "key_parties": ["XYZ Mining (Pty) Ltd", "DMR"],
  "reasoning": "Document contains mining right number and DMR letterhead"
}
```

---

### 3.3 Checkpoint A: Missing Documents (NEW)

**Purpose:** Compare classified documents against blueprint requirements and prompt user for missing documents.

**Trigger:** After classification completes, before readability check.

**UI Component:** `ValidationWizardModal` (modal wizard)

#### Process
1. Load blueprint for transaction type (e.g., `mining_acquisition.yaml`)
2. Extract list of expected document types from blueprint
3. Compare against classified documents
4. Generate missing docs list with importance ratings

#### Missing Docs Display
```
┌─────────────────────────────────────────────────────────────────┐
│ Document Completeness Check                        [Skip All]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Based on your Mining Acquisition transaction, we expected       │
│ these documents but didn't find them:                           │
│                                                                 │
│ ⚠️ CRITICAL                                                     │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Mining Rights Certificate                                   │ │
│ │ Expected in: 04_Regulatory                                  │ │
│ │ [Upload Now] [Don't Have It] [Not Applicable]               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ⚠️ HIGH                                                         │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Environmental Impact Assessment                             │ │
│ │ Expected in: 04_Regulatory                                  │ │
│ │ [Upload Now] [Don't Have It] [Not Applicable]               │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ [Submit & Continue]                                             │
└─────────────────────────────────────────────────────────────────┘
```

#### If User Uploads Documents
1. New documents are classified
2. Merged with existing document set
3. Continue to readability check

---

### 3.4 Readability Check

**Purpose:** Validate documents are readable and convert non-PDF formats to PDF.

**Endpoint:** `POST /api/dd-check-readability`
**Backend:** `DDCheckReadability/__init__.py`

#### Supported Conversions
| Format | Conversion Method | Libraries Used |
|--------|-------------------|----------------|
| PDF | Native (no conversion) | - |
| DOCX | Convert to PDF | python-docx + reportlab |
| XLSX | Convert to PDF | openpyxl + reportlab |
| PPTX | Convert to PDF | python-pptx + reportlab |

#### Readability Status
| Status | Description |
|--------|-------------|
| `ready` | Document is readable |
| `converted` | Document was converted to PDF |
| `failed` | Document could not be read (password-protected, corrupted) |
| `pending` | Not yet checked |

#### Output
- Updates `Document.readability_status`
- Creates `Document.converted_doc_id` if converted
- Extracts `Document.extracted_text_with_pages` with `[PAGE X]` markers

---

### 3.5 Entity Mapping Pass (NEW)

**Purpose:** Prevent entity confusion by mapping all entities mentioned across documents against the target entity from the Wizard. This addresses scenarios like "Pamish Investments appears in 47 documents but relationship to target Vanchem is unclear."

**Endpoint:** `POST /api/dd-entity-mapping`
**Backend:** `DDEntityMapping/__init__.py`
**Model:** Claude Haiku (fast entity extraction)

**Trigger:** After Readability Check, before Processing Phase begins.

#### Wizard Enhancements for Entity Context

Step 1 of the Wizard now includes additional fields to pre-populate expected entities:

| Field | Type | Description |
|-------|------|-------------|
| `targetEntityName` | string | Name of target company (existing) |
| `targetRegistrationNumber` | string | Company registration number |
| `knownSubsidiaries` | {name, relationship}[] | Known subsidiaries/related companies |
| `holdingCompany` | {name, percentage}? | Parent company if applicable |
| `expectedCounterparties` | string[] | Known counterparties (e.g., key customers, suppliers) |

#### Process

```
┌─────────────────────────────────────────────────────────────────┐
│ Entity Mapping Process                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Extract entities from each classified document              │
│     └─ Company names, registration numbers, trading names       │
│                                                                 │
│  2. Match against target entity from Wizard                     │
│     └─ Exact match, fuzzy match, registration number match      │
│                                                                 │
│  3. Auto-infer relationships from document language             │
│     └─ "wholly-owned subsidiary of"                             │
│     └─ "a company registered with number..."                    │
│     └─ "XX% shareholder in"                                     │
│                                                                 │
│  4. Build entity relationship graph                             │
│     └─ nodes: all entities found                                │
│     └─ edges: relationships (subsidiary, parent, counterparty)  │
│                                                                 │
│  5. Flag documents with unknown entities                        │
│     └─ Entities that can't be matched to target or known list   │
│                                                                 │
│  6. Human Confirmation (Checkpoint A.5 if triggered)            │
│     └─ If >3 documents flagged with unknown entities            │
│     └─ User confirms: related_party | exclude | counterparty    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Output Schema

```json
{
  "target_entity": {
    "name": "Vanchem Mining (Pty) Ltd",
    "registration_number": "2010/012345/07",
    "aliases": ["Vanchem", "Vanchem Mining", "VM Mining"],
    "source": "Wizard input + document extraction"
  },

  "entity_map": [
    {
      "entity_name": "Pamish Investments (Pty) Ltd",
      "registration_number": "2008/054321/07",
      "relationship_to_target": "related_party",
      "relationship_detail": "Ore supplier - mentioned in 47 documents",
      "confidence": 0.85,
      "documents_appearing_in": ["Supply Agreement.pdf", "Board Resolution.pdf", "..."],
      "evidence": "Document states 'supply agreement with related party Pamish Investments'",
      "inferred_from": "clause_language"
    },
    {
      "entity_name": "Vanchem Holdings Ltd",
      "registration_number": "2005/098765/06",
      "relationship_to_target": "parent",
      "relationship_detail": "100% shareholder",
      "confidence": 0.95,
      "documents_appearing_in": ["MOI.pdf", "SHA.pdf"],
      "evidence": "MOI states 'Vanchem Holdings Ltd is the sole shareholder'",
      "inferred_from": "shareholding_disclosure"
    },
    {
      "entity_name": "Unknown Mining Services CC",
      "registration_number": null,
      "relationship_to_target": "unknown",
      "relationship_detail": "Appears in 2 documents, relationship unclear",
      "confidence": 0.30,
      "documents_appearing_in": ["Invoice_2024.pdf", "Service Agreement.pdf"],
      "evidence": "No relationship context found in documents",
      "requires_human_confirmation": true
    }
  ],

  "flagged_documents": [
    {
      "document": "Service Agreement - Unknown Mining.pdf",
      "unmatched_entities": ["Unknown Mining Services CC"],
      "risk": "Document may not be relevant to target transaction",
      "recommendation": "human_review",
      "suggested_actions": [
        "Confirm if this is a counterparty contract",
        "Exclude if document uploaded in error",
        "Add to related parties if confirmed related"
      ]
    }
  ],

  "entity_relationship_graph": {
    "nodes": [
      {"id": "target", "name": "Vanchem Mining (Pty) Ltd", "type": "target"},
      {"id": "parent", "name": "Vanchem Holdings Ltd", "type": "parent"},
      {"id": "related1", "name": "Pamish Investments (Pty) Ltd", "type": "related_party"},
      {"id": "unknown1", "name": "Unknown Mining Services CC", "type": "unknown"}
    ],
    "edges": [
      {"from": "parent", "to": "target", "relationship": "100% shareholder"},
      {"from": "related1", "to": "target", "relationship": "ore supplier"}
    ]
  },

  "summary": {
    "total_entities_found": 24,
    "matched_to_target": 8,
    "known_counterparties": 12,
    "unknown_requiring_review": 4,
    "checkpoint_triggered": true
  }
}
```

#### Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `target` | The entity being acquired | Vanchem Mining (Pty) Ltd |
| `parent` | Holding company/shareholder | Vanchem Holdings Ltd |
| `subsidiary` | Owned by target | Vanchem Processing (Pty) Ltd |
| `related_party` | Related but not owned | Pamish Investments (ore supplier) |
| `counterparty` | Known contractual partner | Eskom (offtake), First National Bank (lender) |
| `unknown` | Cannot determine relationship | Requires human confirmation |

#### Human Checkpoint Trigger

If any of these conditions are met, pause for human confirmation:

1. **>3 documents flagged** with entities that can't be matched
2. **Any constitutional document** (MOI, SHA) references an unrecognized entity
3. **Entity appears in >10 documents** but relationship is unclear

#### Human Confirmation Modal

```
┌─────────────────────────────────────────────────────────────────┐
│ Entity Confirmation Required                        [Skip All]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ We found entities that we couldn't confidently link to your     │
│ target company "Vanchem Mining (Pty) Ltd":                      │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Pamish Investments (Pty) Ltd                                │ │
│ │ Appears in: 47 documents                                    │ │
│ │ AI Assessment: "Likely a related party - ore supplier"      │ │
│ │ Confidence: 85%                                             │ │
│ │                                                             │ │
│ │ This entity is:                                             │ │
│ │ ○ Related Party (supplier, customer, etc.)                  │ │
│ │ ○ Subsidiary of Target                                      │ │
│ │ ○ Parent/Holding Company                                    │ │
│ │ ○ Known Counterparty (not related)                          │ │
│ │ ○ Exclude - Documents uploaded in error                     │ │
│ │ ○ Other: [________________]                                 │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ [Confirm & Continue]                                            │
└─────────────────────────────────────────────────────────────────┘
```

#### Integration with Downstream Passes

The entity map is passed to all subsequent processing passes:

- **Pass 1 (Extract):** Validates extracted parties against entity map
- **Pass 2 (Analyze):** Uses entity relationships for conflict detection
- **Pass 3 (Cross-Doc):** Ensures cross-document analysis considers group structure
- **Pass 4 (Synthesize):** Executive summary references correct entity hierarchy

---

## 4. Processing Phase (8-Pass Pipeline)

### 4.1 Materiality Filtering (NEW)

**Purpose:** Set materiality thresholds based on transaction value to filter and prioritize findings appropriately.

**Trigger:** At the start of processing phase, before Pass 1.

#### Threshold Calculation

Materiality thresholds are calculated from `estimatedValue` in the Wizard:

| Classification | Threshold | Description |
|----------------|-----------|-------------|
| **Material** | ≥5% of transaction value | Always included in full report and executive summary |
| **Potentially Material** | 1-5% of transaction value | Included with lower priority |
| **Likely Immaterial** | <1% of transaction value | Included only if qualitatively significant |
| **Unquantified** | Amount unknown | Treated as potentially material, flagged for quantification |

#### Default Thresholds (when transaction value unknown)

If user leaves `estimatedValue` blank in the Wizard, use absolute thresholds:

| Classification | Default Threshold (ZAR) |
|----------------|------------------------|
| **Material** | >R10,000,000 |
| **Potentially Material** | R1,000,000 - R10,000,000 |
| **Likely Immaterial** | <R1,000,000 |

These defaults are configurable per transaction type via blueprint settings.

#### Example Materiality Calculation

```
Transaction Value: R150,000,000

Materiality Thresholds:
- Material:           ≥ R7,500,000   (5%)
- Potentially Material: R1,500,000 - R7,500,000 (1-5%)
- Likely Immaterial:  < R1,500,000   (1%)
```

#### Materiality Override Rules

Certain findings are **always material** regardless of financial amount:

1. **Criminal liability exposure** - Any potential criminal prosecution
2. **License/permit risk** - Risk to mining rights, environmental authorizations
3. **Regulatory non-compliance** - DMRE directives, environmental notices
4. **Reputational risk** - Material issues for listed entities
5. **ESG concerns** - Significant environmental or social governance issues
6. **Deal blockers** - Any issue classified as `deal_blocker`

#### Finding Output Enhancement

All findings now include materiality classification:

```json
{
  "finding_id": "F001",
  "description": "Potential liquidated damages under CSA",
  "quantified_exposure": {
    "amount": 8500000,
    "currency": "ZAR",
    "basis": "24 months × R354,166/month shortfall penalty"
  },
  "materiality": {
    "classification": "material",
    "ratio_to_deal": 0.057,
    "threshold_applied": "5% of R150M transaction value = R7.5M",
    "qualitative_override": null
  }
}
```

#### Filtering Rules

| Report Section | Material | Potentially Material | Likely Immaterial | Unquantified |
|---------------|----------|---------------------|-------------------|--------------|
| **Full Findings Report** | ✓ All | ✓ All | ✓ All | ✓ All |
| **Executive Summary** | ✓ Top 15-20 | ✓ If space | Only if qualitative override | ✓ Flagged |
| **Deal Blockers** | ✓ Always | ✓ Always | ✓ If qualitative | ✓ Always |
| **Financial Exposure** | ✓ Full detail | ✓ Summary | Aggregate only | ✓ Listed |

**Note:** The full findings report is NOT capped - all findings are included. Only the Executive Summary is limited to top 15-20 items by materiality.

---

### 4.2 Pass 1: EXTRACT (+ Document Reference Extraction)

**Purpose:**
1. Extract structured data from each document
2. **NEW:** Extract references to other documents for cross-reference validation

**Model:** Claude Haiku (fast, cost-effective)
**Backend:** `dd_enhanced/core/pass1_extract.py`
**Prompt:** `dd_enhanced/prompts/extraction.py`

#### Input
- Document text (with page markers)
- Document metadata (filename, type, folder category)
- Entity map from Entity Mapping Pass

#### Extracted Data
```json
{
  "parties": [
    {
      "name": "XYZ Mining (Pty) Ltd",
      "role": "seller",
      "registration_number": "2010/012345/07",
      "entity_map_match": "target"
    }
  ],
  "key_dates": [
    {
      "date": "2025-12-31",
      "description": "Mining right expiry",
      "clause_reference": "Schedule 1"
    }
  ],
  "financial_figures": [
    {
      "description": "Purchase price",
      "amount": 150000000,
      "currency": "ZAR",
      "clause_reference": "Clause 3.1"
    }
  ],
  "change_of_control_clauses": [
    {
      "clause_reference": "Clause 15.2",
      "trigger": "Change in shareholding > 50%",
      "consequence": "Automatic termination",
      "consent_required": true
    }
  ],
  "consent_requirements": [...],
  "covenant_restrictions": [...]
}
```

#### NEW: Document Reference Extraction

Pass 1 now extracts references to external documents:

```json
{
  "document_references": [
    {
      "referenced_document": "ENS Legal Opinion dated 24 November 2023",
      "reference_context": "Referenced for environmental compliance status",
      "reference_type": "legal_opinion",
      "criticality": "critical",
      "clause_reference": "Clause 8.2.1",
      "quote": "...as confirmed in the ENS Opinion...",
      "found_in_data_room": null
    },
    {
      "referenced_document": "Subordination Agreement between Seller and First National Bank",
      "reference_context": "Governs priority of security interests",
      "reference_type": "agreement",
      "criticality": "important",
      "clause_reference": "Recital C",
      "quote": "...subject to the terms of the Subordination Agreement...",
      "found_in_data_room": null
    },
    {
      "referenced_document": "Schedule 3 - Mining Area Coordinates",
      "reference_context": "Contains boundary coordinates for mining right",
      "reference_type": "schedule",
      "criticality": "critical",
      "clause_reference": "Clause 2.1",
      "quote": "...the Mining Area as defined in Schedule 3...",
      "found_in_data_room": null
    }
  ]
}
```

#### Reference Types

| Type | Description | Examples |
|------|-------------|----------|
| `agreement` | Contract or legal agreement | Subordination Agreement, Escrow Agreement |
| `legal_opinion` | Legal advice document | ENS Opinion, Werksmans Memo |
| `report` | Technical or financial report | CPR, Environmental Audit |
| `certificate` | Regulatory certificate | Tax Clearance, BEE Certificate |
| `schedule` | Attachment to main document | Schedule A, Annexure 1 |
| `correspondence` | Letters or notices | DMRE Letter, SARS Notice |
| `other` | Other document types | Board Minutes, Valuation |

#### Reference Criticality

| Criticality | Description |
|-------------|-------------|
| `critical` | Document is essential for understanding a material issue |
| `important` | Document would add significant context |
| `minor` | Document is referenced but not essential |

**Note:** Document reference extraction happens in Pass 1 (per-document). Gap analysis (which references are missing from data room) happens in Pass 3 (Cross-Doc) when all documents have been processed.

#### Performance
- ~2-5 seconds per document
- ~500-1000 tokens per document

---

### 4.3 Pass 2: ANALYZE (+ Blueprint Q&A + Action Categories)

**Purpose:**
1. Analyze each document for risks, issues, and opportunities
2. Answer Blueprint questions relevant to the document's folder category
3. **NEW:** Classify findings by action category and resolution path
4. **NEW:** Assign confidence scores to all findings and classifications

**Model:** Claude Sonnet (balanced accuracy/cost)
**Backend:** `dd_enhanced/core/pass2_analyze.py`
**Prompt:** `dd_enhanced/prompts/analysis.py`

#### Input
- Document text
- Extraction results from Pass 1
- Reference documents (MOI, SHA for validation)
- Transaction context (from wizard)
- Blueprint questions for this folder category
- Prioritized questions (Tier 1-3)
- Entity map from Entity Mapping Pass
- Materiality thresholds

#### Chain-of-Thought Analysis Steps
The prompt guides Claude through 8+ reasoning steps:

1. **Document Purpose** - What is this document trying to accomplish?
2. **Party Identification** - Who are the parties and their roles?
3. **Key Obligations** - What must each party do?
4. **Risk Identification** - What could go wrong?
5. **Cross-Reference Check** - Does this conflict with MOI/SHA?
6. **Financial Impact** - What are the monetary implications?
7. **Deal Impact Assessment** - Is this a blocker, CP, or manageable?
8. **Action Category** - How should this be resolved?
9. **Blueprint Questions** - Answer relevant checklist questions

#### Output: Enhanced Findings Schema

```json
{
  "findings": [
    {
      "finding_id": "F001",
      "category": "change_of_control",

      "severity": "critical",
      "deal_impact": {
        "classification": "deal_blocker",
        "description": "Transaction cannot close without counterparty consent"
      },

      "action_category": {
        "type": "condition_precedent",
        "description": "Consent is obtainable but requires negotiation"
      },

      "resolution_path": {
        "mechanism": "suspensive_condition",
        "description": "Include consent as CP in SPA; Seller to pursue pre-signing",
        "responsible_party": "seller",
        "timeline": "before_signing",
        "estimated_cost_to_resolve": {
          "amount": 50000,
          "currency": "ZAR",
          "confidence": 0.6,
          "basis": "Legal fees for consent negotiation"
        }
      },

      "title": "Automatic termination on change of control",
      "description": "The Mining Services Agreement terminates automatically if shareholding changes by more than 50%. This will be triggered by the acquisition.",
      "clause_reference": "Clause 15.2.1",
      "actual_page_number": 12,
      "evidence_quote": "This Agreement shall terminate automatically...",
      "source_document": "Mining Services Agreement.pdf",
      "recommended_action": "Obtain consent from counterparty or negotiate waiver",

      "financial_exposure": {
        "amount": 15000000,
        "currency": "ZAR",
        "calculation": "Annual contract value x remaining term (3 years)",
        "confidence": 0.85
      },

      "materiality": {
        "classification": "material",
        "ratio_to_deal": 0.10,
        "threshold_applied": "5% of R150M = R7.5M"
      },

      "confidence": {
        "overall": 0.90,
        "finding_exists": 0.95,
        "severity_correct": 0.85,
        "financial_amount_correct": 0.80,
        "basis": "Direct quote from contract; amount based on disclosed contract value"
      },

      "reasoning": "Step-by-step analysis of why this is a deal blocker..."
    }
  ]
}
```

#### NEW: Action Category Classification

**Purpose:** Answers "What do we do about this?" (separate from deal_impact which answers "How bad is this?")

| Action Category | Description | Typical Resolution |
|-----------------|-------------|-------------------|
| `terminal` | Issue that could kill the deal or require fundamental restructure | Walk away, major restructure |
| `valuation` | Issue that should result in purchase price adjustment | Price reduction, locked box adjustment |
| `indemnity` | Issue requiring specific indemnity protection from seller | Specific indemnity with cap/survival |
| `warranty` | Issue to be covered by standard warranty regime | General warranty schedule |
| `information` | More information needed before assessment | Document request, management Q&A |
| `condition_precedent` | Must be resolved before closing | CP in SPA, workstream before close |

#### NEW: Resolution Path

Each finding includes a recommended resolution path:

```json
{
  "resolution_path": {
    "mechanism": "suspensive_condition|price_adjustment|indemnity|warranty|disclosure|walk_away",
    "description": "Specific resolution recommendation",
    "responsible_party": "seller|buyer|both|third_party",
    "timeline": "before_signing|between_sign_and_close|post_closing|ongoing",
    "estimated_cost_to_resolve": {
      "amount": 50000,
      "currency": "ZAR",
      "confidence": 0.6,
      "basis": "How cost was estimated"
    }
  }
}
```

#### NEW: Confidence Calibration

All findings include confidence scores following these criteria:

| Score | Level | Criteria | Example |
|-------|-------|----------|---------|
| 0.9-1.0 | Very High | Direct, unambiguous quote. No interpretation. | Contract states "Termination fee of R500,000" |
| 0.7-0.89 | High | Clear inference. Minimal interpretation. | Contract references Schedule 3 which shows R500,000 |
| 0.5-0.69 | Medium | Reasonable interpretation. Some ambiguity. | "Material breach penalties" without specific amount |
| 0.3-0.49 | Low | Inference from indirect evidence. | No clause found, inferring standard terms apply |
| 0.0-0.29 | Very Low | Speculation. Very thin evidence. | Industry practice suggests X provision |

Confidence is required for:
- **Finding existence** - How certain are we this issue exists?
- **Severity classification** - How certain are we this is critical/high/medium/low?
- **Financial amounts** - How certain are we about the quantified exposure?

#### Output: Blueprint Q&A (questions_answered)
```json
{
  "questions_answered": [
    {
      "question": "Are there any change of control provisions that could be triggered?",
      "answer": "Yes. Clause 15.2 of the Mining Services Agreement contains an automatic termination provision triggered by >50% shareholding change. This will be triggered by the proposed acquisition and requires either counterparty consent or contract renegotiation.",
      "confidence": 0.95,
      "finding_refs": ["F001"],
      "source_document": "Mining Services Agreement.pdf",
      "folder_category": "02_Commercial",
      "document_id": "abc-123-def"
    }
  ]
}
```

#### Severity Levels (unchanged)
| Severity | Description | UI Color |
|----------|-------------|----------|
| `critical` | Immediate deal-blocking risk | Red |
| `high` | Significant risk requiring attention | Orange |
| `medium` | Moderate risk, manageable | Yellow |
| `low` | Minor issue, note for awareness | Blue |
| `info` | Informational, no action needed | Gray |

#### Deal Impact vs Action Category

These fields answer different questions:

| Field | Question | Example |
|-------|----------|---------|
| `deal_impact.classification` | "How bad is this?" | `deal_blocker` - cannot close without resolution |
| `action_category.type` | "What do we do about it?" | `condition_precedent` - consent obtainable, add as CP |

A finding can be:
- High `deal_impact` but simple `action_category`: "Deal blocker that just needs a warranty"
- Low `deal_impact` but complex `action_category`: "Minor issue that requires DMRE consent (6 months)"

#### Performance
- ~10-30 seconds per document
- ~2000-5000 tokens per document

---

### 4.3 Checkpoint B: Combined Validation (NEW)

**Purpose:** Human validation of AI's understanding before proceeding with calculations and synthesis.

**Trigger:** After Pass 2 (Analyze) completes, before Pass 2.5 (Calculate).

**UI Component:** `ValidationWizardModal` (4-step modal wizard)

#### Step 1 of 4: Confirm Transaction Understanding

AI generates questions about unclear aspects:

```
┌─────────────────────────────────────────────────────────────────┐
│ Confirm Our Understanding                    Step 1 of 4        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ PRELIMINARY SUMMARY:                                            │
│ "This appears to be an acquisition of XYZ Mining (Pty) Ltd      │
│ by ABC Holdings, structured as a share sale for approximately   │
│ R150 million. The target holds mining rights in Limpopo         │
│ Province expiring in 2030..."                                   │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ QUESTION 1: Is the corporate structure correct?                 │
│                                                                 │
│ We understand the structure as:                                 │
│ "ABC Holdings (Buyer) → acquiring 100% of XYZ Mining,           │
│ which has 2 subsidiaries: XYZ Operations and XYZ Minerals"      │
│                                                                 │
│ ○ Yes, this is correct                                          │
│ ○ Partially correct (please clarify below)                      │
│ ○ No, this is incorrect (please clarify below)                  │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Correction/Clarification:                                   │ │
│ │ [Free text input area]                                      │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ [Skip All & Continue]                    [Next Question →]      │
└─────────────────────────────────────────────────────────────────┘
```

#### Question Generation Logic
AI generates questions only for items that are:
- **Unclear** from documents (conflicting information)
- **Vital** to the analysis (affects deal structure, key parties, transaction type)
- **Ambiguous** (multiple interpretations possible)

**Not** a fixed list - dynamically generated based on analysis findings.

#### Step 2 of 4: Confirm Financial Foundations

```
┌─────────────────────────────────────────────────────────────────┐
│ Confirm Financial Data                       Step 2 of 4        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Please confirm these key financial figures we extracted:        │
│                                                                 │
│ 1. Revenue (FY2024): R 145,000,000                              │
│    ○ Correct                                                    │
│    ○ Incorrect → [Enter correct value: ____________]            │
│    ○ Data not available in documents                            │
│                                                                 │
│ 2. Net Profit (FY2024): R 12,500,000                            │
│    ○ Correct                                                    │
│    ○ Incorrect → [Enter correct value: ____________]            │
│    ○ Data not available in documents                            │
│                                                                 │
│ 3. Total Debt: R 85,000,000                                     │
│    ○ Correct                                                    │
│    ○ Incorrect → [Enter correct value: ____________]            │
│    ○ Data not available in documents                            │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│ Missing data for complete analysis:                             │
│ • EBITDA: [Enter value or upload doc: ____________]             │
│ • Working Capital: [Enter value or upload doc: ____________]    │
│                                                                 │
│ [← Back]                                     [Next Step →]      │
└─────────────────────────────────────────────────────────────────┘
```

**Maximum 5 financial confirmation items** - only the foundations that affect calculations.

#### Step 3 of 4: Missing Documents

```
┌─────────────────────────────────────────────────────────────────┐
│ Additional Documents Needed                  Step 3 of 4        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ Based on our analysis, these documents would help clarify       │
│ uncertain areas:                                                │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Group Structure Chart                                       │ │
│ │ Would help: Clarify subsidiary relationships                │ │
│ │ [Upload] [Don't Have]                                       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ Latest Management Accounts                                  │ │
│ │ Would help: Verify current financial position               │ │
│ │ [Upload] [Don't Have]                                       │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ [← Back]                                     [Next Step →]      │
└─────────────────────────────────────────────────────────────────┘
```

#### If User Uploads Documents
1. New documents processed through Pass 1 (Extract) and Pass 2 (Analyze)
2. Findings merged with existing findings
3. Return to Step 4 (Review & Confirm)

#### Step 4 of 4: Review & Confirm Summary

```
┌─────────────────────────────────────────────────────────────────┐
│ Review & Confirm                             Step 4 of 4        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ UPDATED SUMMARY (incorporating your corrections):               │
│                                                                 │
│ "This is an acquisition of XYZ Mining (Pty) Ltd by ABC          │
│ Holdings, structured as a share sale. [CORRECTED: ABC Holdings  │
│ is acquiring 75%, not 100%, with the remaining 25% held by      │
│ management via an employee trust.]                              │
│                                                                 │
│ Key financial metrics (confirmed):                              │
│ • Revenue: R145M (FY2024)                                       │
│ • Net Profit: R12.5M                                            │
│ • Total Debt: R85M                                              │
│ • EBITDA: R28M [USER PROVIDED]                                  │
│                                                                 │
│ The analysis will now proceed with this understanding."         │
│                                                                 │
│ ─────────────────────────────────────────────────────────────── │
│                                                                 │
│ ○ Confirm - proceed with this understanding                     │
│ ○ Go back - I need to make more corrections                     │
│                                                                 │
│ [← Back]                              [Confirm & Continue →]    │
└─────────────────────────────────────────────────────────────────┘
```

#### Data Storage
User responses stored in:
- `dd_briefing` field (merged with original wizard data)
- `validated_context` field (new - stores checkpoint responses)
- `manual_data_inputs` (user-entered financial values)

---

### 4.4 Pass 2.5: CALCULATE

**Purpose:** Compute financial exposures using validated data.

**Type:** Python computation (no AI)
**Backend:** `dd_enhanced/core/pass_calculations.py`, `dd_enhanced/core/calculation_engine.py`

#### Input
- Pass 1 extracted financial figures
- Pass 2 findings with financial exposure estimates
- User-validated financial data from Checkpoint B

#### Calculations Performed
| Calculation | Formula | Source |
|-------------|---------|--------|
| Contract termination exposure | Annual value × remaining years | CoC clauses |
| Penalty calculations | As per contract terms | Breach provisions |
| Tax exposure | Outstanding × interest × time | Tax findings |
| Environmental remediation | Estimated cleanup cost | Environmental findings |
| Litigation exposure | Claim amount × probability | Litigation findings |

#### Output
```json
{
  "calculated_exposures": [
    {
      "finding_id": "F001",
      "exposure_type": "contract_termination",
      "base_amount": 5000000,
      "multiplier": 3,
      "calculated_amount": 15000000,
      "currency": "ZAR",
      "calculation_notes": "R5M annual value × 3 years remaining",
      "confidence": "high"
    }
  ],
  "total_quantified_exposure": 45000000,
  "unquantified_risks": ["Reputational damage", "Management departure"]
}
```

---

### 4.5 Pass 3: CROSS-DOC

**Purpose:** Detect conflicts, cascades, and dependencies across documents.

**Model:** Claude Opus (most capable, for complex reasoning)
**Backend:** `dd_enhanced/core/pass3_clustered.py`
**Prompt:** `dd_enhanced/prompts/crossdoc.py`

#### Analysis Types

##### 1. Conflict Detection
Find inconsistencies between documents:
```json
{
  "conflicts": [
    {
      "conflict_id": "C001",
      "type": "date_inconsistency",
      "severity": "high",
      "documents": ["SHA.pdf", "Board Resolution.pdf"],
      "description": "SHA requires 30-day notice for share transfers, but Board Resolution approved immediate transfer",
      "resolution": "Clarify with legal counsel; Board Resolution may need amendment"
    }
  ]
}
```

##### 2. Cascade Mapping
Identify chain reactions across documents:
```json
{
  "cascades": [
    {
      "trigger": "Change of control in SHA",
      "affected_documents": [
        "Mining Services Agreement (termination)",
        "Facility Agreement (acceleration)",
        "Key Employee Contracts (retention bonuses)"
      ],
      "total_cascade_exposure": 75000000
    }
  ]
}
```

##### 3. Authorization Check
Verify required approvals exist:
```json
{
  "authorization_issues": [
    {
      "required": "Board approval for transactions > R10M",
      "source": "MOI Clause 7.2",
      "status": "not_found",
      "impact": "Transaction may be invalid without proper authorization"
    }
  ]
}
```

##### 4. Consent Matrix
Map all required consents:
```json
{
  "consent_matrix": [
    {
      "consent_type": "Lender consent",
      "required_by": "Facility Agreement Clause 12.1",
      "from_party": "First National Bank",
      "status": "required",
      "deadline": "Before closing",
      "consequence_if_not_obtained": "Loan acceleration"
    }
  ]
}
```

---

### 4.6 Pass 3.5: AGGREGATE

**Purpose:** Combine calculations and findings across all documents.

**Type:** Python computation (no AI)
**Backend:** `dd_enhanced/core/pass_calculations.py`

#### Aggregation Tasks
1. Sum total financial exposures by category
2. Deduplicate findings (same issue in multiple docs)
3. Build cross-reference index
4. Calculate completion percentages
5. Generate statistics for dashboard

#### Output
```json
{
  "aggregated_exposures": {
    "by_category": {
      "change_of_control": 45000000,
      "environmental": 13000000,
      "employment": 8500000,
      "tax": 12000000
    },
    "total": 78500000,
    "currency": "ZAR"
  },
  "finding_stats": {
    "total": 47,
    "critical": 3,
    "high": 12,
    "medium": 18,
    "low": 14,
    "deal_blockers": 2,
    "conditions_precedent": 8
  },
  "document_coverage": {
    "analyzed": 42,
    "total": 45,
    "percentage": 93.3
  }
}
```

---

### 4.7 Pass 4: SYNTHESIZE

**Purpose:** Generate executive summary, recommendations, and structured outputs.

**Model:** Claude Sonnet
**Backend:** `dd_enhanced/core/pass4_synthesize.py`
**Prompt:** `dd_enhanced/prompts/synthesis.py`

#### Input
- All findings from Pass 2
- Cross-document analysis from Pass 3
- Aggregated calculations from Pass 3.5
- Validated transaction context from Checkpoint B

#### Output Components

##### 1. Executive Summary
2-3 paragraph overview covering:
- Overall financial health assessment
- Key trends and implications
- Major risks/red flags
- Quality of earnings concerns

##### 2. Deal Assessment
```json
{
  "deal_assessment": {
    "can_proceed": true,
    "blocking_issues": ["Environmental litigation must be resolved"],
    "key_risks": ["Mining right renewal uncertainty", "Key customer concentration"],
    "overall_risk_rating": "medium"
  }
}
```

##### 3. Financial Analysis (Comprehensive)
Based on Financial DD Checklist:

**Section 1: Profitability & Performance**
- Margin Analysis (Gross, Operating, EBITDA, Net)
- Return Metrics (ROE, ROA, ROIC)
- Revenue Quality (recurring %, customer concentration)

**Section 2: Liquidity & Solvency**
- Short-term Liquidity (Current, Quick, Cash ratios)
- Leverage & Debt Service (D/E, Net Debt/EBITDA, Interest Coverage)

**Section 3: Cash Flow Health**
- Operating Cash Flow vs Net Income
- Cash Conversion Cycle (DSO, DIO, DPO)
- Free Cash Flow & CapEx analysis

**Section 4: Quality of Earnings**
- Revenue Recognition assessment
- Expense Capitalisation review
- EBITDA Adjustments table
- Related Party Transactions

**Section 5: Balance Sheet Integrity**
- Asset Quality (Goodwill, Receivables aging, Inventory)
- Off-Balance Sheet items (Leases, Guarantees, Contingent liabilities)

**Section 6: Trend Analysis**
- Historical Performance (3yr CAGR)
- Seasonality Patterns
- Forecast Credibility

##### 4. Deal Blockers
```json
{
  "deal_blockers": [
    {
      "issue": "Unresolved environmental litigation",
      "description": "Class action for R13M regarding historical pollution",
      "source": "Litigation files",
      "why_blocking": "Outcome uncertain; could exceed escrow",
      "resolution_path": "Negotiate seller indemnity or settlement",
      "resolution_timeline": "4-6 weeks",
      "owner": "Seller's counsel"
    }
  ]
}
```

##### 5. Conditions Precedent
```json
{
  "conditions_precedent": [
    {
      "cp_number": 1,
      "description": "DMR consent to mining right transfer",
      "category": "Regulatory",
      "source": "Mining Right Certificate",
      "responsible_party": "Seller",
      "target_date": "2026-02-28",
      "status": "pending",
      "is_deal_blocker": false
    }
  ]
}
```

##### 6. Warranties Register
```json
{
  "warranties_register": [
    {
      "id": "W-001",
      "category": "Title & Capacity",
      "description": "Seller has full authority to sell shares",
      "detailed_wording": "The Seller warrants that it has full legal authority...",
      "typical_cap": "Purchase price",
      "survival_period": "3 years",
      "priority": "critical",
      "is_fundamental": true,
      "dd_trigger": "F012 - Board resolution not found",
      "source_document": "SHA.pdf"
    }
  ]
}
```

##### 7. Indemnities Register
```json
{
  "indemnities_register": [
    {
      "id": "I-001",
      "category": "Environmental",
      "description": "Historical pollution liability",
      "detailed_wording": "The Seller shall indemnify the Buyer...",
      "trigger": "Any claim arising from pre-closing pollution",
      "typical_cap": "R15,000,000",
      "survival_period": "7 years",
      "priority": "critical",
      "escrow_recommendation": "R13,000,000 (15% of price)",
      "quantified_exposure": {
        "amount": 13000000,
        "currency": "ZAR",
        "calculation": "Current litigation claim amount"
      },
      "dd_trigger": "F023 - Environmental litigation",
      "source_document": "Litigation files"
    }
  ]
}
```

---

### 4.8 Pass 5: VERIFY

**Purpose:** Final quality control - skeptical review of all outputs.

**Model:** Claude Opus (most rigorous)
**Backend:** `dd_enhanced/core/pass5_verify.py`
**Prompt:** `dd_enhanced/prompts/verification.py`

#### Verification Checks
1. **Calculation verification** - Recompute all financial figures
2. **Severity validation** - Confirm critical/high ratings are justified
3. **Deal blocker review** - Challenge each blocker designation
4. **Missing issue detection** - What did we miss?
5. **Logical consistency** - Do findings contradict each other?
6. **Evidence check** - Is every claim supported by document quotes?

#### Output
```json
{
  "verification_results": {
    "calculations_verified": true,
    "calculation_adjustments": [],
    "severity_changes": [
      {
        "finding_id": "F015",
        "original_severity": "critical",
        "recommended_severity": "high",
        "reasoning": "Issue can be resolved with standard warranty"
      }
    ],
    "additional_concerns": [
      "No cyber security assessment found in IT due diligence"
    ],
    "confidence_score": 0.87
  }
}
```

---

## 5. Human-in-the-Loop Checkpoints

### 5.1 Checkpoint Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CHECKPOINT SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────┐     ┌───────────────┐     ┌───────────────┐  │
│  │ Checkpoint A  │     │ Checkpoint B  │     │ Refinement    │  │
│  │ Missing Docs  │     │ Combined      │     │ Loop          │  │
│  │               │     │ Validation    │     │               │  │
│  │ After:        │     │ After:        │     │ After:        │  │
│  │ Classification│     │ Pass 2        │     │ Pass 5        │  │
│  │               │     │               │     │               │  │
│  │ Purpose:      │     │ Purpose:      │     │ Purpose:      │  │
│  │ Doc coverage  │     │ Validate      │     │ Refine report │  │
│  │               │     │ understanding │     │ iteratively   │  │
│  └───────────────┘     └───────────────┘     └───────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Checkpoint State Machine

```
                    ┌─────────────┐
                    │   pending   │
                    └──────┬──────┘
                           │ checkpoint created
                           ▼
                    ┌─────────────┐
         ┌─────────│  awaiting   │─────────┐
         │         │  user_input │         │
         │         └──────┬──────┘         │
         │                │                │
    user skips       user responds    timeout (async)
         │                │                │
         ▼                ▼                ▼
   ┌──────────┐    ┌───────────┐    ┌──────────┐
   │  skipped │    │ completed │    │  saved   │
   └──────────┘    └───────────┘    │ (resume) │
                                    └──────────┘
```

### 5.3 Data Model

```python
class DDValidationCheckpoint(BaseModel):
    __tablename__ = "dd_validation_checkpoint"

    id = Column(UUID, primary_key=True)
    dd_id = Column(UUID, ForeignKey("due_diligence.id"))
    run_id = Column(UUID, ForeignKey("dd_analysis_run.id"))

    checkpoint_type = Column(String)  # 'missing_docs', 'post_analysis'
    status = Column(String)  # 'pending', 'awaiting_user_input', 'completed', 'skipped'

    # AI-generated content
    preliminary_summary = Column(Text)
    questions = Column(JSON)  # [{question, context, options, user_answer, correction}]
    missing_docs = Column(JSON)  # [{doc_type, importance, reason}]
    financial_confirmations = Column(JSON)  # [{metric, extracted_value, confirmed_value}]

    # User responses
    user_responses = Column(JSON)
    uploaded_doc_ids = Column(JSON)
    manual_data_inputs = Column(JSON)

    # Timestamps
    created_at = Column(DateTime)
    completed_at = Column(DateTime)
```

---

## 6. Post-Processing Phase

### 6.1 Store & Display (Report V1)

**Storage:**
- Findings → `perspective_risk_finding` table
- Synthesis data → `dd_analysis_run.synthesis_data` (JSON)
- Blueprint Q&A → `synthesis_data.blueprint_qa`

**Display:**
- Findings Explorer with multiple views
- Synthesis View (Executive Summary, Deal Blockers, W&I, Financial Analysis)
- Blueprint Answers View (3-panel Q&A display)
- Document Viewer (PDF with highlighting)

### 6.2 Refinement Loop

**Purpose:** Allow users to iteratively improve the report via AI chat.

**Flow:**
```
┌─────────────────────────────────────────────────────────────────┐
│                     REFINEMENT LOOP                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  User views Report V1                                           │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Ask AI: "Can you expand on the environmental risk?"     │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ AI Response:                                            │    │
│  │ "Based on the documents, the environmental risk stems   │    │
│  │ from... I suggest updating Section 3.2 as follows:      │    │
│  │                                                         │    │
│  │ [PROPOSED CHANGE]                                       │    │
│  │ The environmental liability exposure of R13M relates    │    │
│  │ to historical mining activities prior to 2015...        │    │
│  │                                                         │    │
│  │ Should I merge this into the report?                    │    │
│  │ [Yes, Merge] [No, Discard] [Edit First]"                │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                       │
│    [Yes, Merge]                                                 │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Report V2 Created                                       │    │
│  │ • V1 preserved in version history                       │    │
│  │ • V2 now active                                         │    │
│  │ • Change tracked in refinement log                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                       │
│         ▼                                                       │
│  User can continue refining → V3, V4, etc.                      │
│  OR download any version                                        │
│  OR view version history                                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Report Versioning

**Version Naming:** Report V1, Report V2, Report V3...

**Storage:** Each version saved as a draft document:
```json
{
  "version": 2,
  "created_at": "2026-01-23T14:30:00Z",
  "created_by": "user@example.com",
  "refinement_prompt": "Expand on environmental risk",
  "changes": [
    {
      "section": "3.2",
      "type": "expanded",
      "diff": "..."
    }
  ],
  "content": { /* full report content */ }
}
```

**Access:**
- All versions viewable in separate tabs
- All versions downloadable
- Current (latest) version shown by default

---

## 7. Data Models & Storage

### 7.1 Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `due_diligence` | DD project | id, name, briefing, project_setup, owned_by |
| `dd_analysis_run` | Processing run | id, dd_id, status, synthesis_data, started_at |
| `dd_processing_checkpoint` | Progress tracking | id, run_id, current_pass, status, progress |
| `document` | Uploaded documents | id, folder_id, type, extracted_text, readability_status |
| `folder` | Document folders | id, dd_id, name, category |
| `perspective_risk_finding` | Individual findings | id, run_id, document_id, severity, deal_impact |
| `dd_validation_checkpoint` | Human checkpoints | id, run_id, checkpoint_type, questions, responses |
| `dd_report_version` | Report versions | id, run_id, version, content, created_at |

### 7.2 JSON Structures

#### synthesis_data
```json
{
  "executive_summary": "...",
  "deal_assessment": {},
  "financial_analysis": {},
  "deal_blockers": [],
  "conditions_precedent": [],
  "warranties_register": [],
  "indemnities_register": [],
  "blueprint_qa": [],
  "recommendations": []
}
```

#### validated_context (from Checkpoint B)
```json
{
  "transaction_understanding": [
    {"question": "...", "user_answer": "correct", "correction": null}
  ],
  "financial_confirmations": [
    {"metric": "Revenue", "extracted": 145000000, "confirmed": 145000000}
  ],
  "manual_inputs": {
    "EBITDA": 28000000,
    "working_capital": 15000000
  },
  "validated_at": "2026-01-23T12:00:00Z"
}
```

---

## 8. Blueprint System

### 8.1 Blueprint Structure

**Location:** `dd_enhanced/config/blueprints/`

| File | Transaction Type | Size |
|------|------------------|------|
| `mining_acquisition.yaml` | Mining & Resources | ~1600 lines |
| `ma_corporate.yaml` | General M&A | ~800 lines |
| `banking_finance.yaml` | Banking & Finance | ~900 lines |
| `ip_technology.yaml` | IP & Technology | ~700 lines |

### 8.2 Blueprint Components

#### Transaction Type Definition
```yaml
transaction_type: mining_acquisition
name: "Mining Acquisition Due Diligence"
description: "Comprehensive DD for mining company acquisitions"
jurisdiction: "South Africa"
```

#### Folder Categories
```yaml
folder_categories:
  - id: "01_Corporate"
    name: "Corporate & Governance"
    expected_documents:
      - type: "MOI"
        importance: critical
      - type: "Shareholders Agreement"
        importance: critical
      - type: "Board Resolutions"
        importance: high
```

#### Questions by Category
```yaml
questions:
  01_Corporate:
    - id: "CORP-001"
      question: "Is the company validly incorporated?"
      tier: 1
      cot_reasoning:
        - "Check company registration documents"
        - "Verify CIPC registration status"
        - "Confirm MOI adoption"

  04_Regulatory:
    - id: "REG-001"
      question: "Are all mining rights valid and in good standing?"
      tier: 1
      cot_reasoning:
        - "Check mining right certificate"
        - "Verify DMR registration"
        - "Check renewal dates"
```

#### Deal Blockers Definition
```yaml
deal_blockers:
  - id: "DB-001"
    pattern: "mining right expired"
    severity: critical
    description: "Expired mining right makes transaction impossible"

  - id: "DB-002"
    pattern: "environmental prosecution"
    severity: critical
    description: "Active criminal prosecution for environmental breach"
```

#### Warranty Categories
```yaml
warranty_categories:
  - id: "W-TC-001"
    category: "Title & Capacity"
    description: "Seller has authority to sell"
    typical_cap: "purchase_price"
    survival: "3 years"
    is_fundamental: true
```

#### Indemnity Categories
```yaml
indemnity_categories:
  - id: "I-ENV-001"
    category: "Environmental"
    description: "Pre-closing environmental liabilities"
    typical_cap: "quantified_exposure"
    survival: "7 years"
    escrow_recommendation: "10-20% of purchase price"
```

### 8.3 Question Prioritization

**Tier 1:** Always asked (critical to transaction)
**Tier 2:** Asked if relevant documents present
**Tier 3:** Asked if time/budget permits

```python
def prioritize_questions(blueprint, transaction_context, include_tier3=False):
    questions = []

    # Always include Tier 1
    questions.extend(blueprint.get_tier1_questions())

    # Include Tier 2 if relevant docs present
    for q in blueprint.get_tier2_questions():
        if q.relevant_doc_type in available_documents:
            questions.append(q)

    # Optionally include Tier 3
    if include_tier3:
        questions.extend(blueprint.get_tier3_questions())

    return questions[:max_questions]  # Cap at 150
```

---

### 8.4 Statutory Framework (NEW)

**Purpose:** Provide transaction-type-specific statutory citations that flow into analysis prompts, enabling findings to reference specific legislation, sections, and penalties.

#### Statutory Framework Schema

Each blueprint can include a `statutory_framework` section:

```yaml
statutory_framework:
  primary_legislation:
    - act: "Mineral and Petroleum Resources Development Act 28 of 2002"
      acronym: "MPRDA"
      key_sections:
        - section: "Section 11"
          description: "Ministerial consent required for transfer/cession of mining rights"
          penalties:
            max_fine: null
            max_imprisonment: null
            other: "Transfer void without consent"
          transfer_provisions: true
        - section: "Section 47"
          description: "Social and Labour Plan requirements"
          penalties:
            max_fine: null
            max_imprisonment: null
            other: "Mining right suspension or cancellation"
        - section: "Section 93"
          description: "Power of Minister to suspend or cancel rights"
          penalties:
            max_fine: null
            max_imprisonment: null
            other: "Suspension or cancellation of mining right"
      compliance_provisions: "Sections 25-29"
      transfer_provisions: "Section 11"

    - act: "National Environmental Management Act 107 of 1998"
      acronym: "NEMA"
      key_sections:
        - section: "Section 24"
          description: "Environmental authorisation requirements"
          penalties:
            max_fine: 10000000
            max_imprisonment: 10
            other: "Rehabilitation directive"
        - section: "Section 28"
          description: "Duty of care and remediation"
          penalties:
            max_fine: 10000000
            max_imprisonment: 10
            other: "Director personal liability"
      compliance_provisions: "Section 28 duty of care"
      transfer_provisions: null

  secondary_legislation:
    - name: "Mining Charter III (2018)"
      relevance: "HDSA ownership minimum 30%"
    - name: "NEMA Financial Provision Regulations 2015"
      relevance: "Rehabilitation guarantee requirements"

  regulatory_bodies:
    - name: "Department of Mineral Resources and Energy"
      acronym: "DMRE"
      relevance: "Mining rights administration and compliance"
      consent_required_for: ["transfer", "change_of_control", "SLP_amendment"]
    - name: "Department of Water and Sanitation"
      acronym: "DWS"
      relevance: "Water use licensing"
      consent_required_for: ["WUL_transfer", "water_use_change"]

  consequences:
    criminal:
      max_fine: 10000000
      max_imprisonment_years: 10
      personal_liability: true
    civil:
      contract_voidability: true
      damages_exposure: "Unlimited"
      director_liability: "Section 77 Companies Act"
    administrative:
      licence_revocation: true
      debarment_period: "5 years"
      public_disclosure: "CIPC register"
```

#### Transaction Type Statutory Reference

| Transaction Type | Primary Legislation | Key Regulatory Bodies |
|-----------------|---------------------|----------------------|
| **Mining & Resources** | MPRDA, NEMA, NWA, MHSA, Mining Charter III | DMRE, DWS, DMR |
| **M&A / Corporate** | Companies Act 71/2008, Competition Act 89/1998 | CIPC, CompCom |
| **Banking & Finance** | Banks Act 94/1990, NCA 34/2005, FIC Act 38/2001 | SARB, PA, NCR, FIC |
| **Real Estate & Property** | DRA 47/1937, ESTA 62/1997, PIE 19/1998 | Deeds Office |
| **BEE & Transformation** | B-BBEE Act 53/2003, EE Act 55/1998 | dtic, DoL |
| **Employment & Labor** | LRA 66/1995, BCEA 75/1997, MHSA 29/1996 | CCMA, DoL, DMR |
| **Energy & Power** | ERA 4/2006, NERSA Act 40/2004, Gas Act 48/2001 | NERSA, DoE |
| **Competition & Regulatory** | Competition Act 89/1998 | CompCom, CompTrib |
| **IP & Technology** | Patents Act 57/1978, Copyright Act 98/1978, POPIA 4/2013 | CIPC, InfoReg |
| **Infrastructure & PPP** | PFMA 1/1999, MFMA 56/2003, Treasury Regulations | National Treasury |
| **Capital Markets** | FMA 19/2012, Companies Act 71/2008 | FSCA, JSE |
| **Financial Services** | FAIS 37/2002, Insurance Act 18/2017, FIC Act 38/2001 | FSCA, PA, FIC |
| **Private Equity & VC** | Companies Act 71/2008, Tax Acts | SARS, CIPC |
| **Restructuring & Insolvency** | Insolvency Act 24/1936, Companies Act 71/2008 | Master of HC, CIPC |

#### Integration with Analysis Prompts

When identifying regulatory or compliance findings, the AI is instructed to:

```
STATUTORY CITATION REQUIREMENTS:

When identifying regulatory or compliance findings:
1. Cite the specific Act and section number
   Example: "Section 52 of the National Water Act 36 of 1998"

2. Include applicable penalties from the statutory framework
   Example: "Non-compliance may result in fines up to R10M and/or 10 years imprisonment"

3. Reference the regulatory body with jurisdiction
   Example: "Requires DMRE consent under Section 11 MPRDA"

4. Note any consent or notification requirements for the transaction
   Example: "Section 11 consent required within 180 days of transfer"

5. Cite transfer/cession provisions where relevant
   Example: "Transfer void without ministerial consent per Section 11(1)"
```

#### Example Finding with Statutory Citation

```json
{
  "finding_id": "F015",
  "category": "regulatory",
  "title": "Section 11 MPRDA consent required",
  "description": "Transfer of mining right shares requires ministerial consent",
  "statutory_reference": {
    "act": "Mineral and Petroleum Resources Development Act 28 of 2002",
    "section": "Section 11",
    "provision": "No person may cede, transfer, let, sublease, assign or otherwise dispose of a mining right without the written consent of the Minister",
    "consequence": "Transfer void without consent",
    "regulatory_body": "DMRE",
    "typical_timeline": "90-180 days for processing"
  }
}
```

---

### 8.5 Prompt Construction & Confidence Calibration (NEW)

**Purpose:** Guide prompt construction to include statutory references and enforce consistent confidence calibration across all findings.

#### Prompt Construction Guidelines

When building analysis prompts, include:

1. **Transaction context** from Wizard
2. **Entity map** for party validation
3. **Materiality thresholds** for exposure classification
4. **Blueprint questions** for folder category
5. **Statutory framework** for the transaction type
6. **Confidence calibration instructions**

#### Confidence Calibration Instructions

Include this guidance in all analysis prompts:

```
CONFIDENCE CALIBRATION:

When assigning confidence scores (0.0-1.0), use these criteria:

0.9-1.0 (Very High): Direct, unambiguous quote from document. No interpretation required.
  Example: Contract states "Termination fee of R500,000 payable on 30 days notice"
  Evidence field: "Direct quote from Clause 15.2"

0.7-0.89 (High): Clear inference from document language. Minimal interpretation.
  Example: Contract references "penalty provisions in Schedule 3" and Schedule 3 shows R500,000
  Evidence field: "Clause 15.2 references Schedule 3; Schedule 3 specifies R500,000"

0.5-0.69 (Medium): Reasonable interpretation with some ambiguity. Multiple readings possible.
  Example: Contract mentions "material breach penalties" without specifying amount
  Evidence field: "Clause 15.2 mentions 'material breach penalties' - amount not specified"

0.3-0.49 (Low): Inference from indirect evidence or absence of information.
  Example: No termination clause found, inferring standard notice period applies
  Evidence field: "No termination clause found; applying default LRA notice periods"

0.0-0.29 (Very Low): Speculation or very thin evidence. Flag for verification.
  Example: Similar contracts in industry typically have X provision
  Evidence field: "No direct evidence; based on typical industry practice"

IMPORTANT:
- Always explain the basis for confidence in the finding's evidence field
- Low confidence findings should be flagged for human verification
- Never assign high confidence to inferred or speculative findings
- Financial amounts require separate confidence scores
```

#### Aggregate Confidence Reporting

The synthesis pass includes an aggregate confidence metric:

```json
{
  "report_confidence": {
    "average_finding_confidence": 0.78,
    "findings_requiring_verification": 12,
    "high_confidence_findings": 35,
    "low_confidence_findings": 8,
    "summary": "78% average confidence - 8 findings require verification"
  }
}
```

#### Automatic Flagging

Findings with confidence < 0.5 are automatically flagged:

```json
{
  "finding_id": "F042",
  "confidence": {
    "overall": 0.35,
    "finding_exists": 0.40,
    "severity_correct": 0.30,
    "basis": "Inferred from absence of documentation"
  },
  "verification_flags": [
    "LOW_CONFIDENCE: Finding based on inference, not direct evidence",
    "REQUIRES_VERIFICATION: Request source documents to confirm"
  ]
}
```

---

## 9. API Endpoints

### 9.1 Pre-Processing Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/dd-start` | POST | Create new DD project |
| `/api/dd-classify-documents` | POST | Classify documents |
| `/api/dd-check-readability` | POST | Validate documents |
| `/api/dd-validation-checkpoint` | GET | Get pending checkpoint |
| `/api/dd-validation-checkpoint/respond` | POST | Submit checkpoint response |
| `/api/dd-validation-checkpoint/upload` | POST | Upload docs during checkpoint |
| `/api/dd-validation-checkpoint/skip` | POST | Skip checkpoint |

### 9.2 Processing Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/dd-process-enhanced-start` | POST | Start processing |
| `/api/dd-progress-enhanced` | GET | Get processing progress |
| `/api/dd-process-control` | POST | Pause/resume/cancel processing |

### 9.3 Results Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/dd-risks-results` | GET | Get findings |
| `/api/dd-synthesis` | GET | Get synthesis data |
| `/api/dd-blueprint-answers` | GET | Get Q&A data |
| `/api/dd-file-serve` | GET | Serve document files |
| `/api/link` | GET | Get document download URL |

### 9.4 Refinement Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/dd-chat` | POST | Ask AI question |
| `/api/dd-refinement/propose` | POST | AI proposes change |
| `/api/dd-refinement/merge` | POST | Merge proposed change |
| `/api/dd-report-versions` | GET | List report versions |
| `/api/dd-report-versions/{version}` | GET | Get specific version |

---

## 10. UI Components

### 10.1 Processing Dashboard

**Component:** `DDProcessingDashboard.tsx`

- Pipeline rings visualization (Apple Watch style)
- Real-time progress updates via SSE
- Document processing log
- Cost tracking
- Pause/Resume/Cancel controls

### 10.2 Findings Explorer

**Component:** `FindingsExplorer.tsx`

Views available:
- **Analysis View** - Per-document findings
- **Synthesis View** - Executive summary, W&I, Deal Blockers
- **Blueprint Answers** - 3-panel Q&A layout
- **Financial Analysis** - 6-section financial dashboard

### 10.3 Validation Wizard Modal

**Component:** `ValidationWizardModal.tsx` (NEW)

- Step-by-step wizard interface
- "Query X of Y" progress indicator
- Multiple choice + free text input
- File upload capability
- Skip option always available

### 10.4 Report Version Manager

**Component:** `ReportVersionManager.tsx` (NEW)

- Version selector dropdown
- Side-by-side comparison
- Download any version
- Open in new tab

---

## 11. Cost & Token Management

### 11.1 Token Estimation

| Pass | Avg Input Tokens | Avg Output Tokens | Model |
|------|------------------|-------------------|-------|
| Extract | 2,000 | 500 | Haiku |
| Analyze | 5,000 | 2,000 | Sonnet |
| Cross-Doc | 50,000 | 5,000 | Opus |
| Synthesize | 30,000 | 8,000 | Sonnet |
| Verify | 40,000 | 3,000 | Opus |

### 11.2 Cost Calculation

```python
COST_PER_1K_TOKENS = {
    'haiku': {'input': 0.00025, 'output': 0.00125},
    'sonnet': {'input': 0.003, 'output': 0.015},
    'opus': {'input': 0.015, 'output': 0.075}
}

def calculate_cost(tokens_by_model):
    total = 0
    for model, tokens in tokens_by_model.items():
        total += (tokens['input'] / 1000) * COST_PER_1K_TOKENS[model]['input']
        total += (tokens['output'] / 1000) * COST_PER_1K_TOKENS[model]['output']
    return total
```

### 11.3 Typical DD Cost

| DD Size | Documents | Estimated Cost |
|---------|-----------|----------------|
| Small | 20-30 | $5-15 |
| Medium | 50-100 | $20-50 |
| Large | 150-300 | $75-150 |

---

## 12. Error Handling & Recovery

### 12.1 Checkpoint/Resume System

Processing state saved after each pass:
```python
checkpoint_data = {
    'status': 'processing',
    'current_pass': 'analyze',
    'documents_processed': 25,
    'total_documents': 50,
    'pass1_results': {...},
    'partial_pass2_results': {...}
}
```

### 12.2 Error Recovery

| Error Type | Recovery Action |
|------------|-----------------|
| API timeout | Retry with exponential backoff |
| Rate limit | Queue and retry after delay |
| Document parse error | Skip document, flag for review |
| Checkpoint B timeout | Save state, allow async resume |

### 12.3 Audit Trail

All actions logged:
```python
log_audit_event(
    event_type=AuditEventType.DD_PROCESSING_STARTED,
    dd_id=dd_id,
    user_email=user_email,
    details={'run_id': run_id, 'model_tier': 'balanced'}
)
```

---

## Appendix A: File Reference

### Backend Files
| Path | Purpose |
|------|---------|
| `DDProcessEnhancedStart/__init__.py` | Main processing orchestrator |
| `dd_enhanced/core/pass1_extract.py` | Pass 1 implementation |
| `dd_enhanced/core/pass2_analyze.py` | Pass 2 implementation |
| `dd_enhanced/core/pass_calculations.py` | Pass 2.5 & 3.5 calculations |
| `dd_enhanced/core/pass3_clustered.py` | Pass 3 cross-doc analysis |
| `dd_enhanced/core/pass4_synthesize.py` | Pass 4 synthesis |
| `dd_enhanced/core/pass5_verify.py` | Pass 5 verification |
| `dd_enhanced/prompts/*.py` | All Claude prompts |
| `dd_enhanced/config/blueprints/*.yaml` | Transaction blueprints |

### Frontend Files
| Path | Purpose |
|------|---------|
| `ui/src/pages/DD/Wizard/` | 4-step wizard |
| `ui/src/pages/DD/Processing/` | Processing dashboard |
| `ui/src/pages/DD/FindingsExplorer/` | Results views |
| `ui/src/hooks/useAnalysisRuns.ts` | Data fetching hooks |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Blueprint** | YAML configuration defining questions and rules for a transaction type |
| **Checkpoint** | Human validation point in the pipeline |
| **CoT** | Chain-of-Thought reasoning steps in prompts |
| **CP** | Condition Precedent |
| **Deal Blocker** | Issue that prevents deal from proceeding |
| **Finding** | Individual risk/issue identified in a document |
| **Pass** | One stage of the processing pipeline |
| **Synthesis** | Combined executive summary and recommendations |
| **W&I** | Warranties and Indemnities |

---

## Appendix C: Exact Prompts Sent to Claude

This appendix contains the complete prompts sent to Claude at each processing pass. These are the actual prompt templates from the codebase.

---

### C.1 Pass 1: EXTRACTION Prompts

**File:** `dd_enhanced/prompts/extraction.py`

#### System Prompt
```
You are a senior legal analyst specializing in M&A due diligence.
Your task is to extract structured data from legal documents.

Be precise and accurate. Only extract information that is explicitly stated.
Do not infer or speculate. If information is unclear, note it as such.

Always provide the specific clause reference when available.
```

#### User Prompt (build_extraction_prompt)
```
Extract key structured data from this {doc_type} document.

DOCUMENT: {document_name}

{document_text}

---

Extract and return as JSON:

{
    "document_summary": "2-3 sentence summary of what this document is and its key purpose",

    "parties": [
        {
            "name": "Full legal name of party",
            "role": "borrower|lender|lessor|lessee|employer|employee|supplier|customer|shareholder|company",
            "description": "Brief description of their role in this document"
        }
    ],

    "key_dates": [
        {
            "date": "YYYY-MM-DD or descriptive if exact date not given",
            "date_type": "effective|expiry|execution|deadline|renewal|termination",
            "description": "What this date relates to",
            "is_critical": true/false,
            "clause_reference": "Clause X.X if applicable"
        }
    ],

    "financial_figures": [
        {
            "amount": numeric value (no currency symbols),
            "currency": "ZAR|USD|EUR",
            "amount_type": "loan_principal|revenue|liability|fee|penalty|deposit|limit",
            "description": "What this amount represents",
            "calculation_formula": "If this can be calculated from other values, show the formula",
            "clause_reference": "Clause X.X"
        }
    ],

    "change_of_control_clauses": [
        {
            "clause_reference": "Clause X.X",
            "trigger_definition": "What constitutes change of control per this document",
            "trigger_threshold": "Percentage or condition that triggers (e.g., >50%)",
            "consequence": "What happens when triggered",
            "consent_required": true/false,
            "consent_from": "Who must consent",
            "notice_period_days": number or null,
            "termination_right": true/false,
            "financial_consequence": "Any liquidated damages, acceleration, etc.",
            "can_be_waived": true/false
        }
    ],

    "consent_requirements": [
        {
            "trigger": "What triggers the consent requirement",
            "consent_from": "Who must provide consent",
            "consent_type": "written|verbal|notification_only",
            "consequence_if_not_obtained": "What happens without consent",
            "clause_reference": "Clause X.X"
        }
    ],

    "assignment_restrictions": [
        {
            "restriction_type": "prohibited|consent_required|permitted",
            "description": "Description of the restriction",
            "clause_reference": "Clause X.X"
        }
    ],

    "governing_law": "Jurisdiction governing this document",

    "key_obligations": [
        {
            "obligor": "Party with the obligation",
            "obligation": "Description of the obligation",
            "deadline": "When it must be performed if applicable",
            "consequence_of_breach": "What happens if breached"
        }
    ],

    "covenants": [
        {
            "covenant_type": "financial|operational|reporting|restrictive",
            "description": "Description of the covenant",
            "threshold": "Specific threshold if applicable (e.g., DSCR > 1.5x)",
            "testing_frequency": "When tested",
            "current_status": "compliant|breach|waiver if mentioned in document",
            "clause_reference": "Clause X.X"
        }
    ]
}

Only include sections where you find relevant information. Empty arrays are fine.
Be precise with financial figures - include the exact numbers from the document.
```

---

### C.2 Pass 2: ANALYSIS Prompts

**File:** `dd_enhanced/prompts/analysis.py`

#### System Prompt (get_analysis_system_prompt)
```
You are a senior M&A lawyer conducting legal due diligence for a {transaction_type}.

Jurisdiction: {jurisdiction}
{legislation_if_applicable}

Your task is to identify risks, issues, and concerns that could affect the transaction.

CHAIN-OF-THOUGHT REASONING METHODOLOGY:

For EACH potential finding, you MUST reason through these steps IN ORDER before classifying:

**Step 1 - IDENTIFICATION:** What specific clause or provision triggers concern? Quote the exact language.

**Step 2 - CONTEXT:** What is the commercial significance of this document/contract? What is the surrounding contractual context?

**Step 3 - TRANSACTION IMPACT:** How does this interact with a 100% share sale / change of control? Does the transaction trigger this provision? What are the consequences if triggered?

**Step 4 - SEVERITY REASONING:** Why is this critical/high/medium/low? What is the worst-case scenario? What is the likelihood?

**Step 5 - DEAL IMPACT REASONING:** Why is this a blocker vs. condition vs. price chip? Can it be resolved before closing? Who needs to act (buyer/seller/third party)?

**Step 6 - FINANCIAL QUANTIFICATION:** Can a specific exposure be calculated? Show all working. What assumptions are being made?

**Step 7 - FINANCIAL TREND ANALYSIS (for financial documents):**
- Calculate year-over-year changes: Revenue, Gross Profit, Net Profit, Cash Position
- Format: "Revenue: R45.2M → R38.6M (-14.6% YoY)" with [FLAGGED] if decline >10%
- Calculate margin trends: "Gross Margin: 12.5% → 1.7% (-10.8pp)" with [FLAGGED] if compression >5pp
- Identify going concern indicators: negative working capital, audit qualifications, cash burn rate
- Flag any declining trend >10% or margin compression >5 percentage points

**Step 8 - DATE/EXPIRY AWARENESS (CRITICAL for regulatory documents):**
- Extract ALL dates from certificates, clearances, licenses, permits
- Calculate days until expiry from TODAY's date
- Flag as CRITICAL if:
  * ALREADY EXPIRED (negative days) - [EXPIRED: X days ago]
  * Expiring within 90 days - [EXPIRING SOON: X days]
  * Expiring before expected transaction close - [DEAL RISK: expires before close]
- Key documents to check expiry:
  * Tax clearance certificates (typically valid 12 months)
  * BEE verification certificates (typically valid 12 months)
  * Business licenses and permits
  * Professional registrations
  * Insurance policies
  * Regulatory approvals (if time-limited)
- For EACH dated document: "Issue date: [DATE], Expiry date: [DATE], Days remaining: [X]"

IMPORTANT: Only assign severity and deal_impact AFTER completing your reasoning. Your reasoning must justify your classification.

[CONDITIONAL - South Africa only]
**Step 9 - BEE/OWNERSHIP DILUTION ANALYSIS:**
- Current BEE ownership: Calculate current % held by BEE/HDSA shareholders
- Post-transaction BEE ownership: Calculate dilution from equity injection or share issuance
- BEE DILUTION CALCULATION (MANDATORY when equity is being injected):
  * Formula: New BEE % = (Current BEE Shareholding Value) / (Current Company Value + Equity Injection) × 100
  * Example: "Current BEE: 35% of R1.28B = R448M value. Post R450M injection: R448M / R1.73B = 25.9%. DILUTION: 9.1pp below 26% threshold."
  * [CRITICAL FLAG] if post-transaction BEE < 26% = REGULATORY COMPLIANCE BREACH
- Impact assessment: Loss of BEE status affects government contracts, preferential procurement, industry licenses
- Sector thresholds: Generic Codes (26%), Mining Charter (30%), Financial Services (25%), ICT (30%)

[CONDITIONAL - Acquisitions/Financing only]
**Step 10 - CONSOLIDATION ANALYSIS:**
- PRO FORMA CONSOLIDATION: Calculate combined financial position post-acquisition
  * Combined Debt: Acquirer debt + Target debt + New acquisition financing
  * Combined EBITDA: Acquirer EBITDA + Target EBITDA (less synergy costs in Year 1)
  * Leverage Ratio: Combined Debt / Combined EBITDA
- COVENANT STRESS TEST: Will combined entity meet ALL covenant requirements?
- HIDDEN EXPOSURES: Identify items that become visible only on consolidation

CLASSIFICATION DEFINITIONS:

**Severity Levels:**
- critical: Could prevent or derail the transaction entirely
- high: Significant issue requiring immediate attention before closing
- medium: Notable issue requiring resolution but manageable
- low: Minor issue for awareness only

**Deal Impact Categories:**
- deal_blocker: Transaction CANNOT close without resolution (e.g., missing shareholder approval, invalid mining right)
- condition_precedent: Must be resolved before closing but is resolvable (e.g., third party consent obtainable)
- price_chip: Should reduce purchase price or require indemnity protection
- warranty_indemnity: Allocate risk via sale agreement warranties/indemnities
- post_closing: Can be addressed after transaction completes
- noted: For information/record only

Always cite the specific clause reference when identifying an issue.
When calculating financial exposures, SHOW YOUR WORKING (e.g., "24 months × R3.2M/month = R76.8M").

PAGE NUMBER EXTRACTION (CRITICAL for human review):
- The document text contains [PAGE X] markers indicating page boundaries
- For EACH finding, you MUST identify which page(s) the relevant content appears on
- Use the actual_page_number field to specify the primary page number (integer)
- This enables reviewers to quickly navigate to the exact location in the source document
```

#### User Prompt (build_analysis_prompt)
```
Analyze this document for the transaction described below.

TRANSACTION CONTEXT:
{transaction_context}

---

REFERENCE DOCUMENTS (Constitutional/Governance - use these to validate requirements):
{reference_docs_text}

---

DOCUMENT BEING ANALYZED: {document_name} ({doc_type})
{document_text}

---
{questions_section}
---
{deal_blockers_section}
---
{cot_questions_section}
---

Conduct a thorough analysis using the Chain-of-Thought methodology. For EACH potential issue:

1. **REASON FIRST**: Complete all 6 reasoning steps before classifying
2. **THEN CLASSIFY**: Only after reasoning, assign severity and deal_impact
3. **SHOW YOUR WORK**: The reasoning field must justify your classification

For each issue found, classify:

1. **Severity**:
   - critical: Could prevent or derail the transaction
   - high: Significant issue requiring immediate attention
   - medium: Notable issue requiring resolution
   - low: Minor issue for awareness

2. **Deal Impact**:
   - deal_blocker: Transaction CANNOT close without resolution (e.g., missing shareholder approval)
   - condition_precedent: Must be resolved before closing (e.g., third party consent)
   - price_chip: Should reduce purchase price or require indemnity
   - warranty_indemnity: Allocate risk via sale agreement warranties
   - post_closing: Can be addressed after transaction completes
   - noted: For information/record only

{calculations_section}
---

Return JSON:
{
    "document_summary": "Brief summary of document and its relevance to transaction",

    "findings": [
        {
            "finding_id": "F001",
            "category": "change_of_control|consent|financial|covenant|governance|employment|regulatory|contractual|mining_rights|environmental",

            "reasoning": {
                "step_1_identification": "What specific clause triggers concern? Quote exact text: 'In the event of...'",
                "step_2_context": "What is the commercial significance? E.g., 'This is the primary surface lease covering the main mining pit...'",
                "step_3_transaction_impact": "How does 100% share sale interact with this? Does it trigger the provision?",
                "step_4_severity_reasoning": "Why this severity level? What is worst case? E.g., 'CRITICAL because loss of surface access halts operations...'",
                "step_5_deal_impact_reasoning": "Why blocker vs CP vs price chip? Can it be resolved? E.g., 'CONDITION PRECEDENT because consent is obtainable...'",
                "step_6_financial_quantification": "Show calculation: 24 months × R3.2M/month = R76.8M. State assumptions."
            },

            "description": "Clear description of the issue (derived from your reasoning)",
            "clause_reference": "Clause X.X",
            "actual_page_number": 1,
            "evidence_quote": "Exact quote from document (max 200 chars)",
            "severity": "critical|high|medium|low",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|warranty_indemnity|post_closing|noted",
            "financial_exposure": {
                "amount": number or null,
                "currency": "ZAR",
                "calculation": "Show your working: e.g., 24 months × R3.2M = R76.8M",
                "type": "liquidated_damages|acceleration|penalty|fee|rehabilitation|regulatory"
            },
            "financial_extraction": {
                "has_calculable_exposure": true,
                "formula_pattern": "PEN_001|EMP_001|LSE_001|DBT_001|etc",
                "variables": {
                    "var_name_1": {"value": 500000, "unit": "tonnes", "source_clause": "1.1"},
                    "var_name_2": {"value": 927, "unit": "ZAR", "source_clause": "2.3"}
                },
                "interpretation_notes": "How you interpreted the contract terms"
            },
            "action_required": "What needs to be done to address this",
            "responsible_party": "buyer|seller|third_party|dmre|lender",
            "deadline": "When this needs to be resolved if applicable",
            "blueprint_question_answered": "The specific question from the checklist this finding addresses (if applicable)"
        }
    ],

    "questions_answered": [
        {
            "question": "The question from the checklist",
            "answer": "Brief answer based on document analysis",
            "finding_refs": ["F001", "F002"]
        }
    ],

    "positive_confirmations": [
        {
            "description": "Positive aspect of this document for the transaction",
            "clause_reference": "Clause X.X if applicable"
        }
    ],

    "missing_information": [
        "List of information that should be in this document but is missing or unclear"
    ],

    "cross_reference_needed": [
        "Other documents that should be checked in relation to findings in this document"
    ],

    "compliance_deadlines": [
        {
            "deadline": "Date or timeframe",
            "description": "What must be done",
            "source_clause": "Clause X.X",
            "consequence_of_missing": "What happens if deadline is missed"
        }
    ]
}

Be thorough - a good lawyer would rather flag something unnecessary than miss something important.
```

---

### C.3 Pass 3: CROSS-DOCUMENT Prompts

**File:** `dd_enhanced/prompts/crossdoc.py`

#### System Prompt (get_crossdoc_system_prompt)
```
You are a senior M&A partner conducting final review of due diligence for a {transaction_type}.

Jurisdiction: {jurisdiction}

Your task is to look ACROSS all documents to find issues that only become
apparent when comparing multiple documents together:
- Conflicts: Document A says X, but Document B says Y
- Cascades: A single event (like change of control) triggers consequences across multiple contracts
- Authorization gaps: Constitutional documents require something that wasn't done
- Consent matrices: Multiple consents needed from different parties

This cross-document analysis is what separates thorough DD from checkbox DD.
```

#### Conflict Detection Prompt (build_conflict_detection_prompt)
```
Review ALL documents below and identify CONFLICTS between them.
{cross_doc_validations_section}
{deal_blockers_section}

A CONFLICT exists when:
1. Document A requires something that Document B shows wasn't done
2. Document A says X but Document B says Y or contradicts it
3. Terms or definitions differ materially between documents
4. Obligations in one document conflict with rights in another
5. Approval thresholds or processes differ between documents

This is CROSS-DOCUMENT analysis - you must compare documents against each other.

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{
    "conflicts": [
        {
            "conflict_id": "C001",
            "conflict_type": "authorization_gap|inconsistent_terms|conflicting_obligations|definitional_mismatch|procedural_conflict",
            "severity": "critical|high|medium",
            "description": "Clear description of the conflict",
            "document_a": "First document name",
            "document_a_provision": "What Document A says (with clause ref)",
            "document_b": "Second document name",
            "document_b_provision": "What Document B says or doesn't say (with clause ref)",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|requires_resolution",
            "resolution_required": "What needs to happen to resolve this conflict",
            "which_prevails": "Which document should prevail if conflicting, or 'unclear'"
        }
    ],
    "summary": "Brief summary of key conflicts found"
}

If no conflicts are found, return {"conflicts": [], "summary": "No material conflicts identified between documents."}

IMPORTANT: Look specifically for:
1. MOI/SHA approval requirements vs what Board Resolution actually approved
2. Change of control definitions that differ between contracts
3. Consent requirements that may conflict
4. Financial terms that don't reconcile
```

#### Cascade Mapping Prompt (build_cascade_mapping_prompt)
```
This is an acquisition where {trigger_event} will occur.
{deal_blockers_section}
{cp_patterns_section}
{calculation_guidance}

Map how this change of control event CASCADES through ALL contracts and documents.

For each document, identify:
1. Whether it contains a change of control trigger
2. What threshold triggers it
3. What happens when triggered (consent needed, termination right, payment, etc.)
4. The financial exposure if triggered adversely

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{
    "trigger_event": "{trigger_event}",
    "trigger_analysis": "Analysis of whether this transaction triggers change of control provisions",
    "cascade_items": [
        {
            "sequence": 1,
            "document": "Document name",
            "clause_reference": "Clause X.X",
            "trigger_threshold": "What % or event triggers this (e.g., >50% shares)",
            "is_triggered": true/false,
            "consequence": "What happens when triggered",
            "consent_required": true/false,
            "consent_from": "Who must consent",
            "notice_period_days": number or null,
            "termination_right": true/false,
            "can_refuse_consent": true/false,
            "financial_exposure": {
                "amount": number or null,
                "currency": "ZAR",
                "calculation_basis": "How the amount is calculated (show the math)",
                "exposure_type": "liquidated_damages|termination_fee|acceleration|penalty|other"
            },
            "can_be_waived": true/false,
            "waiver_obtained": true/false/null,
            "risk_level": "critical|high|medium|low",
            "deal_impact": "deal_blocker|condition_precedent|price_chip|noted"
        }
    ],
    "total_financial_exposure": {
        "amount": number,
        "currency": "ZAR",
        "breakdown": "Summary of how total was calculated"
    },
    "critical_path": [
        "Ordered list of actions/consents needed before closing can occur"
    ],
    "deal_blockers": [
        "List any items that would prevent the deal from closing if not resolved"
    ],
    "summary": "Executive summary of the cascade analysis"
}

IMPORTANT CALCULATIONS:
- For Eskom-type coal supply agreements: Calculate liquidated damages as X months × monthly contract value
- For loan facilities: Show the full acceleration amount at risk
- For leases: Calculate any early termination penalties

Show your calculation working for any financial exposure figures.
```

#### Authorization Check Prompt (build_authorization_check_prompt)
```
Verify that governance actions (Board Resolutions, shareholder actions) comply with
constitutional documents (MOI, Shareholders Agreement).
{deal_blockers_section}
{ref_docs_guidance}

This is a critical cross-document check: Does the Board Resolution properly authorize
what the MOI and Shareholders Agreement require?

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{
    "moi_requirements": {
        "for_share_sale": "What MOI requires for a change of control/share sale",
        "approval_threshold": "Required majority/percentage",
        "special_resolution_needed": true/false,
        "clause_reference": "Clause X.X"
    },
    "sha_requirements": {
        "additional_requirements": "What Shareholders Agreement adds to MOI requirements",
        "tag_along_rights": true/false,
        "drag_along_rights": true/false,
        "right_of_first_refusal": true/false,
        "clause_reference": "Clause X.X"
    },
    "board_resolution_analysis": {
        "what_was_approved": "What the Board Resolution authorizes",
        "approved_by": "Who approved (directors present/voting)",
        "date": "Date of resolution",
        "quorum_met": true/false/unknown,
        "proper_notice_given": true/false/unknown
    },
    "shareholder_resolution_analysis": {
        "exists": true/false,
        "what_was_approved": "What shareholders approved if applicable",
        "approval_percentage": "Percentage that approved",
        "date": "Date of resolution"
    },
    "authorization_gaps": [
        {
            "gap_id": "AG001",
            "description": "Clear description of what's missing or deficient",
            "required_by": "Which document requires this",
            "requirement_clause": "Clause X.X",
            "current_status": "What has been done (or not done)",
            "severity": "critical|high|medium",
            "deal_impact": "deal_blocker|condition_precedent",
            "remediation": "What needs to happen to fix this"
        }
    ],
    "summary": "Overall assessment of authorization status"
}

PAY SPECIAL ATTENTION TO:
1. Whether shareholder approval was obtained if required by MOI
2. Whether the resolution covers the specific transaction contemplated
3. Any procedural defects (quorum, notice, voting)
4. Whether conditions in the resolution have been or can be met
```

#### Consent Matrix Prompt (build_consent_matrix_prompt)
```
Build a comprehensive CONSENT MATRIX for this transaction.
{cp_patterns_section}
{deal_blockers_section}
{critical_docs_guidance}

Identify every consent, approval, or notification required across all documents.

DOCUMENTS:
{all_documents_text}

---

Return JSON:
{
    "consent_matrix": [
        {
            "consent_id": "CON001",
            "contract": "Contract/document name",
            "counterparty": "Who must provide consent",
            "consent_type": "written_consent|approval|notification|acknowledgment",
            "trigger": "What triggers this requirement",
            "clause_reference": "Clause X.X",
            "timing": "When consent must be obtained (before/after closing)",
            "deadline_days": number or null,
            "consequence_if_not_obtained": "What happens without consent",
            "is_deal_blocker": true/false,
            "likelihood_of_obtaining": "high|medium|low|unknown",
            "cost_to_obtain": "Any fee or cost associated",
            "status": "not_started|in_progress|obtained|refused|waived",
            "responsible_party": "buyer|seller",
            "notes": "Any additional relevant information"
        }
    ],
    "summary": {
        "total_consents_required": number,
        "deal_blocking_consents": number,
        "estimated_timeline": "How long to obtain all consents",
        "key_risks": ["List of key consent risks"]
    }
}

Include consents required for:
1. Change of control clauses
2. Assignment restrictions
3. Banking/loan facilities
4. Material contracts
5. Regulatory approvals (if any)
6. Employment contracts (if they require notification)
```

#### Missing Document Prompt (build_missing_document_prompt)
```
Analyze the documents below and identify documents that are REFERENCED but NOT PROVIDED.

DOCUMENTS WE HAVE (provided in data room):
{doc_list}
{expected_docs_section}

DOCUMENTS TEXT:
{all_documents_text}

---

TASK: Identify MISSING DOCUMENTS by:
1. Looking for references to other documents that we don't have
   - "as per the Subordination Agreement..."
   - "subject to the terms of the Escrow Agreement..."
   - "in accordance with the SARB approval dated..."
2. Looking for documents that SHOULD exist for this transaction type but aren't provided
3. Checking if required schedules/annexures mentioned are actually attached

Return JSON:
{
    "missing_documents": [
        {
            "doc_id": "MISS001",
            "referenced_as": "How document is referenced (e.g., 'the Subordination Agreement')",
            "referenced_in": "Which provided document references it",
            "clause_reference": "Clause/section where referenced",
            "document_type": "contract|certificate|regulatory|schedule|annexure",
            "criticality": "critical|high|medium|low",
            "why_needed": "Why this document is important",
            "impact_if_missing": "What issues arise without it",
            "is_deal_blocker": true/false
        }
    ],
    "incomplete_documents": [
        {
            "document_name": "Document that references missing attachment",
            "missing_attachment": "Schedule A / Annexure 1 / etc.",
            "description": "What the attachment should contain"
        }
    ],
    "summary": {
        "total_missing": number,
        "critical_missing": number,
        "deal_blocking_gaps": ["List of gaps that could block the deal"],
        "recommended_requests": ["List of documents to request from seller"]
    }
}

COMMON MISSING DOCUMENTS TO CHECK FOR:
- Subordination agreements (often referenced but not provided)
- Escrow agreements
- Side letters to main agreements
- Board/shareholder resolutions authorizing specific actions
- SARB approval letters (for exchange control matters)
- Competition Commission clearance certificates
- Environmental authorizations
- Mining rights certificates (for mining transactions)
- Water use licenses
- Tax clearance certificates (current/valid)
- BEE verification certificates (current/valid)
- Insurance policies mentioned in contracts
- Guarantee documents referenced in facility agreements
```

---

### C.4 Pass 4: SYNTHESIS Prompts

**File:** `dd_enhanced/prompts/synthesis.py`

#### System Prompt
```
You are a senior M&A partner preparing the final due diligence summary
for presentation to the client and transaction team.

Your role is to:
1. Synthesize all findings into a coherent picture
2. Clearly identify deal-blockers vs manageable issues
3. Quantify financial exposures with VERIFIED calculations
4. Provide actionable recommendations
5. Present information in order of importance
6. Generate STRATEGIC QUESTIONS that probe deeper than the documents

The client needs to understand:
- Can we do this deal?
- What are the key risks?
- How much will it really cost?
- What do we need to close?
- What questions should we be asking that we haven't yet?

CRITICAL: When you identify issues, think like a skeptical partner:
- Challenge the valuation assumptions
- Question why financial performance is declining
- Ask what management isn't telling us
- Probe the real likelihood of adverse scenarios
- Consider what information is missing from the data room
```

#### User Prompt (build_synthesis_prompt)
```
Prepare the final Due Diligence synthesis for this acquisition.

TRANSACTION VALUE: {transaction_value}

---

FINDINGS FROM DOCUMENT ANALYSIS (Pass 2):
{pass2_findings}

---

CROSS-DOCUMENT CONFLICTS IDENTIFIED (Pass 3):
{pass3_conflicts}

---

CHANGE OF CONTROL CASCADE ANALYSIS (Pass 3):
{pass3_cascade}

---

AUTHORIZATION CHECK (Pass 3):
{pass3_authorization}

---

CONSENT MATRIX (Pass 3):
{pass3_consents}

---

Synthesize all the above into a final DD summary.

Return JSON:
{
    "executive_summary": "3-5 paragraph executive summary suitable for client presentation",

    "deal_assessment": {
        "can_proceed": true/false,
        "blocking_issues": ["List of issues that MUST be resolved before closing"],
        "key_risks": ["Top 3-5 risks in order of importance"],
        "overall_risk_rating": "high|medium|low"
    },

    "financial_analysis": {
        "overview": "2-3 paragraph executive financial summary covering: (1) Overall financial health assessment, (2) Key trends and their implications, (3) Major risks/red flags identified, (4) Quality of earnings concerns if any",

        "profitability_performance": {
            "margin_analysis": {
                "gross_margin": {"current": number, "prior": number, "trend": "improving|declining|stable"},
                "operating_margin": {"current": number, "prior": number, "trend": "improving|declining|stable"},
                "ebitda_margin": {"current": number, "prior": number, "trend": "improving|declining|stable"},
                "net_margin": {"current": number, "prior": number, "trend": "improving|declining|stable"},
                "notes": "Margin analysis observations - flag if declining >5% or significantly below peers"
            },
            "return_metrics": {
                "roe": number or null,
                "roa": number or null,
                "roic": number or null,
                "notes": "Return metrics assessment - high ROE from leverage vs operations = different risk"
            },
            "revenue_quality": {
                "recurring_vs_one_off_pct": number or null,
                "customer_concentration": {"top_customer_pct": number, "top_5_customers_pct": number, "flag": "none|warning|critical"},
                "geographic_concentration": "Description of geographic revenue mix",
                "contract_backlog": number or null,
                "notes": ">20% from single customer = key-man risk; high one-off revenue inflates current period"
            }
        },

        "liquidity_solvency": {
            "short_term_liquidity": {
                "current_ratio": number or null,
                "quick_ratio": number or null,
                "cash_ratio": number or null,
                "net_working_capital": number or null,
                "notes": "Current ratio <1.0 signals potential distress; quick ratio critical for manufacturing"
            },
            "leverage_debt_service": {
                "debt_to_equity": number or null,
                "net_debt_to_ebitda": number or null,
                "interest_coverage": number or null,
                "debt_maturity_profile": "Description of maturity schedule - wall of maturities = refinancing risk",
                "covenant_compliance": {"in_compliance": true or false, "headroom_pct": number, "historical_breaches": "none|waived|default"},
                "notes": "Net Debt/EBITDA >3.5x triggers concerns; Interest coverage <2.0x is distressed"
            }
        },

        "cash_flow_health": {
            "operating_cash_flow": {
                "ocf_current": number or null,
                "ocf_prior": number or null,
                "ocf_vs_net_income": "Aligned with NI|Gap - investigate|Significant gap - earnings quality concern",
                "notes": "Persistent OCF vs NI gap = earnings quality concern"
            },
            "cash_conversion_cycle": {
                "dso": number or null,
                "dio": number or null,
                "dpo": number or null,
                "total_ccc_days": number or null,
                "ccc_trend": "improving|stable|deteriorating",
                "notes": "Rising DSO may indicate collection issues; Rising DIO signals obsolescence risk"
            },
            "free_cash_flow": {
                "fcf_current": number or null,
                "capex_maintenance": number or null,
                "capex_growth": number or null,
                "dividend_coverage_ratio": number or null,
                "notes": "Negative FCF with positive NI = red flag; Underspending maintenance = asset quality erosion"
            }
        },

        "quality_of_earnings": {
            "revenue_recognition": {
                "policy_assessment": "Conservative|Appropriate|Aggressive",
                "accrued_unbilled_revenue_trend": "Stable|Growing|Growing faster than billed AR - concern",
                "deferred_revenue_trend": "Stable|Growing|Declining - may signal churn",
                "notes": "Aggressive POC recognition, bill-and-hold arrangements"
            },
            "expense_capitalisation": {
                "capitalised_costs_concern": true or false,
                "rd_capitalisation_rate": number or null,
                "depreciation_policy": "Conservative|Industry standard|Aggressive - longer lives",
                "notes": "Capitalising opex inflates EBITDA; check policy changes"
            },
            "ebitda_adjustments": [
                {
                    "adjustment_type": "Description of add-back",
                    "amount": number,
                    "assessment": "Valid one-time|Questionable|Recurring disguised as one-time",
                    "notes": "Assessment rationale"
                }
            ],
            "related_party_transactions": [
                {
                    "description": "Transaction description",
                    "amount": number or null,
                    "assessment": "Arm's length|Below market|Above market - concern"
                }
            ],
            "owner_adjustments": {
                "above_market_compensation": number or null,
                "personal_expenses_through_business": number or null,
                "notes": "Normalization required for true earnings"
            }
        },

        "balance_sheet_integrity": {
            "asset_quality": {
                "goodwill_to_equity_pct": number or null,
                "receivables_aging_concern": "None|Moderate - growing >60 day|Significant - growing >90 day",
                "inventory_obsolescence_risk": "Low|Moderate|High - slow-moving stock identified",
                "ppe_condition": "Well maintained|Deferred maintenance concern|Impairment indicators",
                "intercompany_balances_concern": "None|Trapped cash|Transfer pricing adjustment needed",
                "notes": "Goodwill > 50% of equity = acquisition integration risk"
            },
            "off_balance_sheet": {
                "operating_lease_commitments": number or null,
                "guarantees_and_commitments": number or null,
                "contingent_liabilities": [
                    {
                        "description": "Litigation/environmental/tax dispute",
                        "amount": number or null,
                        "probability": "Remote|Possible|Probable",
                        "notes": "Assessment"
                    }
                ],
                "factoring_securitisation": "None|True sale|Financing with recourse - add to debt",
                "notes": "Off-balance sheet items that affect true leverage"
            }
        },

        "trend_analysis": {
            "historical_performance": {
                "revenue_3yr_cagr": number or null,
                "ebitda_3yr_cagr": number or null,
                "inflection_points": ["Any significant changes and their causes"],
                "notes": "Historical trend observations"
            },
            "seasonality_patterns": {
                "quarterly_pattern": "Even distribution|Q4 heavy|Seasonal pattern described",
                "hockey_stick_risk": true or false,
                "notes": "Hockey-stick Q4 = channel stuffing risk"
            },
            "forecast_credibility": {
                "historical_accuracy": "Consistently met|Mixed|Consistently missed",
                "budget_variance_pattern": "On target|Systematic over-performance|Systematic under-performance",
                "notes": "Consistent misses = credibility discount on projections"
            }
        },

        "red_flags_summary": [
            {
                "category": "Profitability|Liquidity|Cash Flow|Quality of Earnings|Balance Sheet|Other",
                "flag": "Clear description of the red flag",
                "severity": "critical|high|medium",
                "source": "Document where identified",
                "impact": "Transaction impact - affects valuation/structure/risk allocation"
            }
        ],

        "data_gaps": [
            {
                "missing_item": "What financial information is missing",
                "importance": "critical|high|medium",
                "impact": "How this gap affects the analysis"
            }
        ]
    },

    "financial_exposure_summary": {
        "total_quantified_exposure": number,
        "currency": "ZAR",
        "exposure_breakdown": [
            {
                "category": "change_of_control|acceleration|termination|other",
                "amount": number,
                "description": "Brief description",
                "likelihood": "high|medium|low"
            }
        ],
        "unquantified_risks": ["Risks that couldn't be quantified but are material"]
    },

    "deal_blockers": [
        {
            "issue": "Clear description",
            "source": "Document where found",
            "why_blocking": "Why this prevents closing",
            "resolution_path": "How to resolve",
            "resolution_timeline": "Estimated time to resolve",
            "owner": "Who is responsible for resolution"
        }
    ],

    "conditions_precedent_register": [
        {
            "cp_number": 1,
            "description": "Description of condition",
            "category": "consent|approval|regulatory|document|other",
            "source": "Contract requiring this",
            "responsible_party": "buyer|seller|third_party",
            "target_date": "When needed",
            "status": "not_started|in_progress|complete",
            "is_deal_blocker": true/false
        }
    ],

    "price_adjustment_items": [
        {
            "item": "Description",
            "amount": number or null,
            "basis": "Why this affects price"
        }
    ],

    "warranties_register": [
        {
            "id": "W-001",
            "category": "Title & Capacity|Mining Rights|Environmental|Financial|Material Contracts|Employment|Tax|BEE",
            "description": "Clear description of the warranty",
            "detailed_wording": "Suggested warranty wording for the sale agreement",
            "typical_cap": "Purchase price|50% of purchase price|Unlimited|Quantified amount",
            "survival_period": "18 months|3 years|5 years|7 years",
            "priority": "critical|high|medium",
            "dd_trigger": "Which DD finding(s) triggered this warranty recommendation",
            "source_document": "Document where issue was identified"
        }
    ],

    "indemnities_register": [
        {
            "id": "I-001",
            "category": "Environmental|Mining Rights|Tax|Employment|Third Party Claims|BEE",
            "description": "Clear description of the indemnity",
            "detailed_wording": "Suggested indemnity wording for the sale agreement",
            "trigger": "What triggers this indemnity claim",
            "typical_cap": "Quantified gap amount|Unlimited|As negotiated",
            "survival_period": "3 years|5 years|7 years|Perpetual",
            "priority": "critical|high|medium",
            "escrow_recommendation": "10-20% of purchase price in escrow if applicable",
            "quantified_exposure": {
                "amount": number or null,
                "currency": "ZAR",
                "calculation": "How the amount was calculated"
            },
            "dd_trigger": "Which DD finding(s) triggered this indemnity recommendation",
            "source_document": "Document where issue was identified"
        }
    ],

    "post_closing_items": [
        {
            "item": "Description",
            "deadline": "When to complete",
            "owner": "Who is responsible"
        }
    ],

    "key_recommendations": [
        "Top 5 recommendations for the transaction team"
    ],

    "next_steps": [
        "Immediate actions required"
    ],

    "strategic_questions": [
        {
            "question": "Full question text - must probe WHY not just WHAT",
            "category": "valuation|commercial|strategic|risk|regulatory|governance",
            "priority": "critical|high|medium",
            "context": "Why this question matters for the transaction",
            "who_should_answer": "Target management|Seller|Advisor|Regulatory body",
            "documents_needed": ["Documents that would help answer this"]
        }
    ]
}

IMPORTANT:
1. Be decisive - clearly state if issues are deal-blocking
2. Quantify everything possible with ZAR amounts
3. Prioritize by importance, not by document order
4. Focus on what the client needs to DECIDE and DO
5. Flag any areas where further investigation is needed

STRATEGIC QUESTIONS GUIDANCE:
Generate 8-12 strategic questions that a senior M&A partner would ask the client or target.
These should NOT be simple document requests - they should be INVESTIGATIVE questions that probe deeper issues.

Examples of GOOD strategic questions:
- "What caused the 14.5% revenue decline and is this trend continuing into the current year?"
- "Is the R850M valuation justified given the going concern qualification and negative working capital?"
- "What is Eskom's historical approach to enforcing CoC termination clauses in coal supply agreements?"
- "Should the transaction be structured to preserve existing BEE shareholding to maintain Mining Charter compliance?"
- "What retention mechanisms are needed for the MD given his R15M severance entitlement?"

Examples of BAD questions (too simple - avoid these):
- "Obtain the latest management accounts" (this is a document request, not a question)
- "Confirm the water license status" (this is an action item, not an investigative question)

WARRANTIES & INDEMNITIES GUIDANCE:
Generate SEPARATE warranties and indemnities registers based on DD findings.

WARRANTIES (warranties_register):
- Warranties are representations by the Seller about the current state of the target
- Organize by category: Title & Capacity, Mining Rights, Environmental, Financial, Material Contracts, Employment, Tax, BEE
- Include specific suggested wording for the sale agreement
- Specify typical caps (e.g., "Purchase price", "50% of purchase price") and survival periods
- Link each warranty to the specific DD finding that triggered it
- Prioritize: Title/Capacity and Mining Rights should be "critical"; Tax warranties typically 5 years

INDEMNITIES (indemnities_register):
- Indemnities are obligations by Seller to compensate Buyer for specific identified risks
- Indemnities are appropriate for KNOWN issues discovered in DD (not warranties for unknown risks)
- Key triggers for indemnities:
  * Rehabilitation liability gap (provision < estimated liability)
  * Pre-closing environmental contamination
  * SLP arrears requiring catch-up expenditure
  * Pre-closing tax exposures
  * Occupational disease claims (silicosis, etc.)
  * Pre-closing breaches of material contracts
- Quantify the exposure where possible (e.g., "Rehabilitation gap: R45M - R32M = R13M shortfall")
- Recommend escrow for material environmental or rehabilitation indemnities (typically 10-20% of price)
- Specify survival periods: Environmental 5-7 years, Tax 5 years, Occupational disease 10+ years
```

---

### C.5 Pass 5: VERIFICATION Prompts

**File:** `dd_enhanced/prompts/verification.py`

#### System Prompt
```
You are a senior M&A partner performing final quality control on a due diligence report.
Your role is to be the "skeptical reviewer" - challenging findings, verifying calculations,
and ensuring the analysis is bulletproof before it goes to the client.

You have decades of experience and have seen deals fail due to:
- Overlooked deal-blockers that seemed minor
- Miscalculated financial exposures (off by orders of magnitude)
- Assumptions that weren't validated
- Missing regulatory requirements
- Inconsistent information across documents

Your job is NOT to redo the analysis, but to:
1. VERIFY - Are the conclusions supported by the evidence?
2. CHALLENGE - What assumptions might be wrong?
3. QUANTIFY - Are the financial calculations mathematically correct?
4. PRIORITIZE - Are the deal-blockers truly blocking?
5. FLAG - What's missing or inconsistent?

Be direct and specific. If something is wrong, say so clearly.
```

#### Deal Blocker Verification Prompt (build_deal_blocker_verification_prompt)
```
TRANSACTION CONTEXT:
{transaction_context}

EXECUTIVE SUMMARY:
{executive_summary}

---

IDENTIFIED DEAL BLOCKERS:
{blockers_text}

---

For each deal blocker, provide your assessment:

1. Is this TRULY a deal-blocker, or could it be downgraded to a condition precedent?
   - A TRUE deal-blocker means the transaction CANNOT proceed at all without resolution
   - A condition precedent means the transaction can proceed but this must be resolved by closing

2. Is the severity assessment correct?
   - Could this be resolved more easily than stated?
   - Or is it actually MORE severe than described?

3. Are there any MISSING deal-blockers?
   - Based on the executive summary, what critical issues might have been missed?
   - What regulatory or structural issues are commonly overlooked?

Return JSON:
{
    "blocker_assessments": [
        {
            "blocker_index": 1,
            "original_title": "Title of blocker",
            "is_truly_blocking": true/false,
            "recommended_classification": "deal_blocker|condition_precedent|price_chip|noted",
            "severity_assessment": "correct|understated|overstated",
            "reasoning": "Clear explanation of your assessment",
            "resolution_difficulty": "high|medium|low",
            "estimated_resolution_time": "Before signing|Before closing|Post-closing|Unknown"
        }
    ],
    "missing_blockers": [
        {
            "issue": "Description of potentially missed deal-blocker",
            "why_blocking": "Why this could block the deal",
            "likelihood": "high|medium|low",
            "recommended_action": "What should be done to investigate"
        }
    ],
    "overall_deal_risk": "high|medium|low",
    "recommendation": "Proceed with caution|Resolve blockers first|Further investigation needed|Deal appears sound"
}
```

#### Calculation Verification Prompt (build_calculation_verification_prompt)
```
{transaction_info}

EXTRACTED FINANCIAL FIGURES:
{figures_text}

---

CALCULATED EXPOSURES:
{calc_text}

---

For each calculation, verify:

1. MATHEMATICAL ACCURACY
   - Are the arithmetic operations correct?
   - Do the inputs match the source documents?
   - Are the units consistent (months, years, percentage points)?

2. INTERPRETATION ACCURACY
   - Is the formula appropriate for this type of exposure?
   - Are there alternative interpretations of the contract language?
   - Could the exposure be higher or lower under different readings?

3. MATERIALITY
   - Is this exposure material relative to the transaction value?
   - Should this affect deal pricing or structure?

4. MISSING EXPOSURES
   - Based on the financial figures, are there exposures that should have been calculated but weren't?

Return JSON:
{
    "calculation_verifications": [
        {
            "calculation_index": 1,
            "formula_id": "PEN_001",
            "original_amount": 927000000,
            "verified_amount": 927000000,
            "is_correct": true/false,
            "mathematical_accuracy": "correct|error_found|needs_review",
            "interpretation_accuracy": "correct|alternative_reading|ambiguous",
            "error_description": "If error found, describe it here",
            "alternative_calculation": "If different interpretation, show alternative",
            "materiality": "material|immaterial",
            "confidence": 0.0-1.0
        }
    ],
    "missing_calculations": [
        {
            "description": "What exposure is missing",
            "estimated_range": {"low": 0, "high": 0, "currency": "ZAR"},
            "source": "Where this should come from",
            "priority": "high|medium|low"
        }
    ],
    "total_verified_exposure": {
        "amount": 0,
        "currency": "ZAR",
        "confidence": 0.0-1.0
    },
    "exposure_vs_transaction": {
        "ratio": 0.0,
        "assessment": "acceptable|concerning|deal_threatening",
        "recommendation": "Recommendation for handling"
    }
}
```

#### Consistency Verification Prompt (build_consistency_verification_prompt)
```
FINDINGS BY CATEGORY:
{findings_text}

---

CROSS-DOCUMENT FINDINGS:
{cross_doc_text}

---

IDENTIFIED CONFLICTS:
{conflicts_text}

---

Review the findings for consistency and completeness:

1. INTERNAL CONSISTENCY
   - Do findings contradict each other?
   - Are severity ratings consistent across similar issues?
   - Do financial figures reconcile?

2. LOGICAL CONSISTENCY
   - Do the conclusions follow from the evidence?
   - Are there findings that seem inconsistent with the transaction type?
   - Are there gaps in the logical chain?

3. COMPLETENESS
   - Are there obvious areas not covered?
   - Based on the transaction type, what analysis is typically expected but missing?
   - Are there standard risks for this type of deal that weren't addressed?

4. PRIORITIZATION
   - Are the highest-severity items truly the most important?
   - Should any items be escalated or de-escalated?

Return JSON:
{
    "consistency_issues": [
        {
            "issue_type": "contradiction|gap|misprioritization|incomplete",
            "description": "Clear description of the issue",
            "affected_findings": ["Finding 1", "Finding 2"],
            "severity": "high|medium|low",
            "recommendation": "How to resolve"
        }
    ],
    "missing_analysis_areas": [
        {
            "area": "Name of missing analysis area",
            "typical_risks": "What risks are typically found here",
            "priority": "high|medium|low"
        }
    ],
    "prioritization_adjustments": [
        {
            "finding": "Description of finding",
            "current_severity": "critical|high|medium|low",
            "recommended_severity": "critical|high|medium|low",
            "reasoning": "Why this should change"
        }
    ],
    "overall_consistency_score": 0.0-1.0,
    "confidence_in_analysis": "high|medium|low",
    "key_concerns": [
        "Top 3-5 concerns about the analysis quality"
    ]
}
```

#### Final Verification Summary Prompt (build_final_verification_summary_prompt)
```
TRANSACTION CONTEXT:
{transaction_context}

---

DEAL BLOCKER VERIFICATION RESULTS:
- Overall Deal Risk: {overall_deal_risk}
- Blockers Verified: {num_blockers}
- Missing Blockers Identified: {num_missing}
- Recommendation: {recommendation}

---

CALCULATION VERIFICATION RESULTS:
- Calculations Verified: {num_calculations}
- Errors Found: {num_errors}
- Total Verified Exposure: {currency} {amount}
- Exposure Assessment: {assessment}

---

CONSISTENCY VERIFICATION RESULTS:
- Consistency Issues Found: {num_issues}
- Missing Analysis Areas: {num_missing_areas}
- Overall Consistency Score: {score}
- Confidence in Analysis: {confidence}

---

Based on all verification results, provide a FINAL VERIFICATION SUMMARY:

Return JSON:
{
    "verification_passed": true/false,
    "overall_confidence": 0.0-1.0,
    "critical_issues": [
        {
            "issue": "Description of critical issue that must be addressed",
            "category": "deal_blocker|calculation|consistency|missing",
            "action_required": "Specific action to take",
            "owner": "Who should address this"
        }
    ],
    "warnings": [
        "Non-critical issues to be aware of"
    ],
    "strengths": [
        "What was done well in the analysis"
    ],
    "final_recommendation": {
        "deal_status": "proceed|proceed_with_caution|hold|do_not_proceed",
        "key_conditions": ["Conditions for proceeding"],
        "estimated_total_exposure": {
            "amount": 0,
            "currency": "ZAR",
            "confidence": 0.0-1.0
        },
        "next_steps": ["Immediate actions required"]
    },
    "verification_metadata": {
        "verification_date": "ISO date",
        "areas_verified": ["deal_blockers", "calculations", "consistency"],
        "documents_reviewed": 0,
        "findings_reviewed": 0
    }
}
```

---

*Document maintained by: Alchemy Development Team*
