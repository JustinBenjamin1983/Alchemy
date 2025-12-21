"""
Compression Engine for Phase 4: Summary Compression + Batching

Generates legally-focused compressed summaries at target token lengths.
Uses Haiku for cost-efficient compression with ThreadPoolExecutor for parallelism.

Key features:
- Priority-aware compression (critical docs get more detail)
- Legally-focused summaries preserving transaction-relevant provisions
- Structured output with key provisions, parties, dates, amounts, risk flags
- Parallel compression with rate limit awareness

Usage:
    compressed_docs = compress_all_documents(
        documents=documents,
        prioritized_docs=prioritized_docs,
        pass2_findings=pass2_findings,
        claude_client=claude_client,
        progress_callback=update_progress
    )
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
import time

try:
    import tiktoken
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False
    TOKENIZER = None

from .document_priority import PrioritizedDocument, DocumentPriority
from .claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Compression configuration
MAX_WORKERS = 5  # Parallel compression threads
RETRY_DELAY = 2  # Seconds to wait on rate limit
MAX_RETRIES = 3  # Max retries per document
INPUT_CHAR_LIMIT = 25000  # Max chars of document text to send


@dataclass
class CompressedDocument:
    """A compressed document summary ready for batched Pass 3."""
    document_id: str
    document_name: str
    folder_category: str
    document_type: str
    priority: DocumentPriority

    # Compressed content
    summary: str
    summary_tokens: int
    key_provisions: List[str] = field(default_factory=list)
    key_parties: List[str] = field(default_factory=list)
    key_dates: List[str] = field(default_factory=list)
    key_amounts: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)

    # Context from Pass 2
    pass2_finding_summary: str = ""
    finding_count: int = 0

    # Compression metadata
    original_tokens: int = 0
    compression_ratio: float = 0.0
    compression_error: Optional[str] = None


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken or fallback estimation."""
    if HAS_TIKTOKEN and TOKENIZER:
        try:
            return len(TOKENIZER.encode(text))
        except Exception:
            pass
    # Fallback: estimate 4 chars per token
    return len(text) // 4


def compress_document(
    document: Dict[str, Any],
    prioritized: PrioritizedDocument,
    pass2_findings: List[Dict[str, Any]],
    claude_client: ClaudeClient
) -> CompressedDocument:
    """
    Generate a legally-focused compressed summary of a document.

    Args:
        document: Full document dict with extracted_text
        prioritized: PrioritizedDocument with priority and target tokens
        pass2_findings: Findings from Pass 2 for this document
        claude_client: Claude API client

    Returns:
        CompressedDocument with summary and structured data
    """
    target_tokens = prioritized.compressed_token_target
    doc_text = document.get('extracted_text', document.get('text', ''))
    doc_id = prioritized.document_id

    # Get findings for this document
    doc_findings = [
        f for f in pass2_findings
        if str(f.get('document_id', '')) == doc_id or
           f.get('source_document', '') == prioritized.document_name
    ]

    # Build findings summary
    findings_lines = []
    for f in doc_findings[:10]:  # Limit to top 10
        severity = f.get('severity', 'medium').upper()
        title = f.get('title', f.get('description', 'Finding'))[:100]
        findings_lines.append(f"- [{severity}] {title}")
    findings_text = "\n".join(findings_lines) if findings_lines else "No significant findings identified."

    # Adjust prompt based on priority
    if prioritized.priority == DocumentPriority.CRITICAL:
        detail_instruction = """Provide a DETAILED summary preserving:
- All material provisions, obligations, and conditions
- Specific clause references for key terms
- All change of control or assignment provisions
- All financial terms and payment obligations
- All termination triggers and consequences"""
    elif prioritized.priority == DocumentPriority.HIGH:
        detail_instruction = """Provide a comprehensive summary covering:
- Key provisions and material terms
- Notable clauses and conditions
- Change of control provisions if any
- Main financial terms
- Key termination provisions"""
    elif prioritized.priority == DocumentPriority.MEDIUM:
        detail_instruction = """Provide a standard summary covering:
- Main purpose and parties
- Key terms and conditions
- Notable issues or unusual provisions
- Any change of control provisions"""
    else:
        detail_instruction = """Provide a brief summary stating:
- Document type and purpose
- Parties involved
- Any critical issues only"""

    # Target word count (rough: 1 token ≈ 0.75 words)
    target_words = int(target_tokens * 0.75)

    prompt = f"""You are a legal document summarizer for M&A due diligence.

DOCUMENT: {prioritized.document_name}
DOCUMENT TYPE: {prioritized.document_type}
FOLDER: {prioritized.folder_category}

TARGET LENGTH: Approximately {target_words} words ({target_tokens} tokens)

{detail_instruction}

DOCUMENT TEXT:
{doc_text[:INPUT_CHAR_LIMIT]}

ANALYSIS FINDINGS:
{findings_text}

Respond in JSON format only:
{{
    "summary": "<legal summary focusing on transaction-relevant provisions>",
    "key_provisions": ["<material clause 1>", "<material clause 2>"],
    "key_parties": ["<party name and role>"],
    "key_dates": ["<date and significance>"],
    "key_amounts": ["<amount and context>"],
    "risk_flags": ["<any red flags or concerns>"]
}}

CRITICAL INSTRUCTIONS:
- Focus on M&A-relevant provisions (change of control, consent, termination, assignment)
- Include specific clause references where possible
- Note unusual or non-standard provisions
- Flag missing items expected for this document type
- Keep summary at target length - be concise but preserve legal substance
- For risk_flags, only include actual concerns, not confirmations"""

    system_prompt = """You are a senior legal associate summarizing documents for due diligence.
Output valid JSON only. Be precise with legal terminology.
Focus on provisions that affect M&A transactions."""

    # Call Haiku for cost-efficient compression
    response = claude_client.complete_extraction(
        prompt=prompt,
        system=system_prompt,
        max_tokens=target_tokens + 300  # Allow buffer for JSON structure
    )

    # Parse response
    if "error" in response:
        logger.warning(f"Compression failed for {prioritized.document_name}: {response.get('error')}")
        return _create_fallback_compression(prioritized, doc_text, findings_text, response.get('error'))

    # Response should already be parsed JSON from claude_client
    parsed = response if isinstance(response, dict) else _parse_compression_response(str(response))

    summary = parsed.get('summary', '')
    summary_tokens = count_tokens(summary)

    return CompressedDocument(
        document_id=prioritized.document_id,
        document_name=prioritized.document_name,
        folder_category=prioritized.folder_category,
        document_type=prioritized.document_type,
        priority=prioritized.priority,
        summary=summary,
        summary_tokens=summary_tokens,
        key_provisions=parsed.get('key_provisions', [])[:10],
        key_parties=parsed.get('key_parties', [])[:10],
        key_dates=parsed.get('key_dates', [])[:10],
        key_amounts=parsed.get('key_amounts', [])[:10],
        risk_flags=parsed.get('risk_flags', [])[:10],
        pass2_finding_summary=findings_text[:500],
        finding_count=len(doc_findings),
        original_tokens=prioritized.estimated_tokens,
        compression_ratio=_calculate_compression_ratio(prioritized.estimated_tokens, summary_tokens),
    )


def _parse_compression_response(response: str) -> Dict[str, Any]:
    """Parse JSON response from compression prompt."""
    try:
        # Handle potential markdown code blocks
        if '```json' in response:
            response = response.split('```json')[1].split('```')[0]
        elif '```' in response:
            response = response.split('```')[1].split('```')[0]
        return json.loads(response.strip())
    except json.JSONDecodeError:
        # Return the raw response as summary if JSON parsing fails
        return {
            'summary': response[:1000],
            'key_provisions': [],
            'key_parties': [],
            'key_dates': [],
            'key_amounts': [],
            'risk_flags': ['JSON parsing failed - summary may be incomplete']
        }


def _create_fallback_compression(
    prioritized: PrioritizedDocument,
    doc_text: str,
    findings_text: str,
    error: str
) -> CompressedDocument:
    """Create a fallback compression when API call fails."""
    # Create a minimal summary from the first part of the document
    fallback_summary = f"[Compression failed] Document type: {prioritized.document_type}. "
    fallback_summary += doc_text[:500].replace('\n', ' ')[:400]

    return CompressedDocument(
        document_id=prioritized.document_id,
        document_name=prioritized.document_name,
        folder_category=prioritized.folder_category,
        document_type=prioritized.document_type,
        priority=prioritized.priority,
        summary=fallback_summary,
        summary_tokens=count_tokens(fallback_summary),
        key_provisions=[],
        key_parties=[],
        key_dates=[],
        key_amounts=[],
        risk_flags=['Compression failed - using truncated original'],
        pass2_finding_summary=findings_text[:500],
        finding_count=0,
        original_tokens=prioritized.estimated_tokens,
        compression_ratio=0.0,
        compression_error=error,
    )


def _calculate_compression_ratio(original: int, compressed: int) -> float:
    """Calculate compression ratio as percentage reduction."""
    if original <= 0:
        return 0.0
    return max(0.0, (1 - (compressed / original)) * 100)


def _compress_with_retry(
    document: Dict[str, Any],
    prioritized: PrioritizedDocument,
    pass2_findings: List[Dict[str, Any]],
    claude_client: ClaudeClient,
    max_retries: int = MAX_RETRIES
) -> CompressedDocument:
    """Compress a document with retry logic for rate limits."""
    last_error = None

    for attempt in range(max_retries):
        try:
            return compress_document(document, prioritized, pass2_findings, claude_client)
        except Exception as e:
            last_error = str(e)
            if 'rate' in last_error.lower() or '429' in last_error:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.warning(f"Rate limit hit, waiting {wait_time}s before retry")
                time.sleep(wait_time)
            else:
                logger.error(f"Compression error for {prioritized.document_name}: {e}")
                break

    return _create_fallback_compression(
        prioritized,
        document.get('extracted_text', ''),
        '',
        last_error or 'Unknown error'
    )


def compress_all_documents(
    documents: List[Dict[str, Any]],
    prioritized_docs: List[PrioritizedDocument],
    pass2_findings: List[Dict[str, Any]],
    claude_client: ClaudeClient,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    max_workers: int = MAX_WORKERS
) -> List[CompressedDocument]:
    """
    Compress all documents with parallel processing and progress tracking.

    Args:
        documents: List of full document dicts
        prioritized_docs: List of PrioritizedDocument from priority system
        pass2_findings: List of findings from Pass 2
        claude_client: Claude API client
        progress_callback: Optional callback(current, total, message)
        max_workers: Number of parallel compression threads

    Returns:
        List of CompressedDocument in priority order
    """
    total = len(prioritized_docs)
    compressed: List[CompressedDocument] = []

    # Build document lookup by ID
    doc_lookup = {str(d.get('id', '')): d for d in documents}

    # Also try by filename for matching
    for d in documents:
        filename = d.get('original_file_name', d.get('filename', ''))
        if filename:
            doc_lookup[filename] = d

    def compress_one(prioritized: PrioritizedDocument) -> CompressedDocument:
        doc = doc_lookup.get(prioritized.document_id)
        if not doc:
            doc = doc_lookup.get(prioritized.document_name, {})

        return _compress_with_retry(
            document=doc,
            prioritized=prioritized,
            pass2_findings=pass2_findings,
            claude_client=claude_client
        )

    # Use ThreadPoolExecutor for parallel compression
    logger.info(f"Compressing {total} documents with {max_workers} workers")

    completed = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all compression tasks
        future_to_doc = {
            executor.submit(compress_one, p): p
            for p in prioritized_docs
        }

        # Collect results as they complete
        for future in as_completed(future_to_doc):
            prioritized = future_to_doc[future]
            try:
                result = future.result()
                compressed.append(result)
            except Exception as e:
                logger.error(f"Compression failed for {prioritized.document_name}: {e}")
                compressed.append(_create_fallback_compression(
                    prioritized,
                    doc_lookup.get(prioritized.document_id, {}).get('extracted_text', ''),
                    '',
                    str(e)
                ))

            completed += 1
            if progress_callback:
                progress_callback(
                    completed,
                    total,
                    f"Compressed {prioritized.document_name}"
                )

    # Re-sort by priority (as_completed returns in completion order)
    compressed.sort(key=lambda x: (x.priority.value, -x.original_tokens))

    # Log compression stats
    total_original = sum(c.original_tokens for c in compressed)
    total_compressed = sum(c.summary_tokens for c in compressed)
    overall_ratio = _calculate_compression_ratio(total_original, total_compressed)

    logger.info(f"Compression complete:")
    logger.info(f"  Total documents: {len(compressed)}")
    logger.info(f"  Original tokens: {total_original:,}")
    logger.info(f"  Compressed tokens: {total_compressed:,}")
    logger.info(f"  Overall reduction: {overall_ratio:.1f}%")

    errors = [c for c in compressed if c.compression_error]
    if errors:
        logger.warning(f"  Compression errors: {len(errors)}")

    return compressed


def get_compression_stats(compressed_docs: List[CompressedDocument]) -> Dict[str, Any]:
    """
    Get statistics about compressed documents.

    Returns:
        Dict with compression metrics
    """
    if not compressed_docs:
        return {'total_documents': 0}

    total_original = sum(c.original_tokens for c in compressed_docs)
    total_compressed = sum(c.summary_tokens for c in compressed_docs)

    by_priority = {}
    for doc in compressed_docs:
        tier = doc.priority.name
        if tier not in by_priority:
            by_priority[tier] = {
                'count': 0,
                'original_tokens': 0,
                'compressed_tokens': 0,
            }
        by_priority[tier]['count'] += 1
        by_priority[tier]['original_tokens'] += doc.original_tokens
        by_priority[tier]['compressed_tokens'] += doc.summary_tokens

    return {
        'total_documents': len(compressed_docs),
        'total_original_tokens': total_original,
        'total_compressed_tokens': total_compressed,
        'compression_ratio': _calculate_compression_ratio(total_original, total_compressed),
        'by_priority': by_priority,
        'errors': len([c for c in compressed_docs if c.compression_error]),
        'avg_summary_tokens': total_compressed // len(compressed_docs) if compressed_docs else 0,
    }
