# Claude LLM Adapter - Replaces Azure OpenAI for local dev
import json
import logging
import os
import time
from typing import List, Dict, Any, Optional
from .dev_config import get_dev_config

import anthropic

_client = None

def _get_client():
    """Get or create Anthropic client"""
    global _client
    if _client is None:
        config = get_dev_config()
        api_key = config.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")

        _client = anthropic.Anthropic(api_key=api_key)
        logging.info("🤖 Claude API client initialized")

    return _client

def call_llm_with(*, messages: List[Dict], temperature: float = 0, max_tokens: int = 4000,
                  end_point_env_var: str = 'AZURE_OPENAI_ENDPOINT',
                  key_env_var: str = 'AZURE_OPENAI_KEY',
                  model_deployment_env_var: str = 'AZURE_MODEL_DEPLOYMENT',
                  model_version_env_var: str = 'AZURE_MODEL_VERSION') -> str:
    """
    Call Claude API (replaces Azure OpenAI call_llm_with)

    Args:
        messages: List of message dicts with 'role' and 'content'
        temperature: Sampling temperature (0-1)
        max_tokens: Maximum tokens in response
        *_env_var: Ignored (for compatibility with Azure version)

    Returns:
        str: The assistant's response text
    """
    client = _get_client()

    # Convert messages format - extract system message
    system_prompt = None
    claude_messages = []

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if role == "system":
            system_prompt = content
        else:
            # Claude uses 'user' and 'assistant' roles
            claude_messages.append({
                "role": role if role in ("user", "assistant") else "user",
                "content": content
            })

    # Ensure we have at least one user message
    if not claude_messages:
        claude_messages = [{"role": "user", "content": "Please respond."}]

    # Retry configuration
    max_retries = 5
    base_delay = 2
    max_delay = 60

    for attempt in range(max_retries):
        try:
            logging.info(f"[Claude] API call attempt {attempt + 1}/{max_retries}")

            # Make the API call
            kwargs = {
                "model": "claude-sonnet-4-20250514",  # Use Claude Sonnet 4
                "max_tokens": max_tokens,
                "messages": claude_messages,
            }

            # Add system prompt if present
            if system_prompt:
                kwargs["system"] = system_prompt

            # Add temperature if not 0 (Claude default)
            if temperature > 0:
                kwargs["temperature"] = temperature

            response = client.messages.create(**kwargs)

            # Extract text from response
            reply = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    reply += block.text

            # Log usage
            logging.info(
                f"[Claude] Success. Tokens - "
                f"Input: {response.usage.input_tokens}, "
                f"Output: {response.usage.output_tokens}"
            )

            return reply

        except anthropic.RateLimitError as e:
            wait_time = min(base_delay * (2 ** attempt), max_delay)
            logging.warning(f"[Claude] Rate limited. Waiting {wait_time}s...")

            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            else:
                raise

        except anthropic.APIError as e:
            wait_time = min(base_delay * (2 ** attempt), max_delay)
            logging.error(f"[Claude] API error: {e}")

            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            else:
                raise

        except Exception as e:
            logging.exception(f"[Claude] Unexpected error: {e}")

            if attempt < max_retries - 1:
                wait_time = min(base_delay * (2 ** attempt), max_delay)
                time.sleep(wait_time)
                continue
            else:
                raise

    raise Exception("Max retries exceeded without successful response")

def call_llm_with_search(*, messages: List[Dict], max_tokens: int = 4000,
                         model: str = "o4-mini", enable_web_search: bool = True,
                         max_tool_calls: int = 10, include_search_results: bool = True) -> str:
    """
    Call Claude API for search-enabled queries (replaces OpenAI Responses API)

    Note: Claude doesn't have built-in web search, so this falls back to regular
    Claude calls. For true web search, you'd need to integrate a search API.

    Args:
        messages: List of message dicts
        max_tokens: Maximum tokens in response
        model: Ignored (uses Claude)
        enable_web_search: Logged but not implemented (would need external search API)
        max_tool_calls: Ignored
        include_search_results: Ignored

    Returns:
        str: The assistant's response text
    """
    if enable_web_search:
        logging.warning("[Claude] Web search requested but not available in dev mode. Using standard Claude call.")

    # Just use the standard call
    return call_llm_with(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0
    )

def get_llm_summary(doc_results: List[Dict], prompt: str) -> str:
    """
    Get LLM summary using Claude (replaces Azure OpenAI version)
    """
    formatted_doc_results = "\n\n".join(
        f"Filename: {doc_result.get('filename', 'Unknown file')}\n"
        f"Page Number: {doc_result.get('page_number', 'N/A')}\n"
        f"Content: {doc_result.get('content', '').strip()}"
        for doc_result in doc_results
    )

    messages = [
        {"role": "system", "content": f"""
{prompt}

Here is additional files and content provided by the client. Use it as your only source of information. If this information is not helpful just reply with "NONE":
{formatted_doc_results}
"""},
        {"role": "user", "content": "Extract the relevant information as requested."}
    ]

    return call_llm_with(messages=messages, temperature=0, max_tokens=4000)

def get_llm_summaryChat(doc_results: List[Dict], prompt: str) -> str:
    """
    Get LLM summary for chat using Claude (replaces Azure OpenAI version)
    """
    formatted_doc_results = "\n\n".join(
        f"Document ID: {doc_result.get('doc_id', 'Unknown')}\n"
        f"Filename: {doc_result.get('filename', 'Unknown file')}\n"
        f"Page Number: {doc_result.get('page_number', 'N/A')}\n"
        f"Content: {doc_result.get('content', '').strip()}"
        for doc_result in doc_results
    )

    system_content = f"""
{prompt}

Here are the source documents provided by the client. Use ONLY this information as your source:
{formatted_doc_results}

CRITICAL INSTRUCTIONS FOR YOUR RESPONSE:

1. STRUCTURE your response using this EXACT format:

## Executive Summary
[Provide a concise 1-2 sentence direct answer to the question]

## Detailed Analysis
[Provide thorough analysis with specific references]

## Key Findings
[Use bullet points for main discoveries, each with confidence scores and citations]

## Source References
[List all documents referenced with page numbers]

2. CONFIDENCE SCORING: For every factual claim, include a confidence score using this format:
- **High Confidence (90-100%)**: Information explicitly stated in multiple sources
- **Medium Confidence (70-89%)**: Information clearly stated in one reliable source
- **Low Confidence (50-69%)**: Information inferred or partially documented
- **Uncertain (<50%)**: Information unclear or contradictory

3. CITATIONS: Use this exact format for every claim:
- For direct quotes: "exact text" (Source: [Filename], Page [X])
- For paraphrased information: [Information] (Source: [Filename], Page [X])

If the provided information is insufficient to answer the question meaningfully, respond with "NONE".
"""

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "Extract the relevant information as requested, following the structured format."}
    ]

    return call_llm_with(messages=messages, temperature=0, max_tokens=4000)

def create_embeddings(texts: List[str], batch_size: int = 100) -> List[List[float]]:
    """
    Create embeddings using Claude's embedding capability or a fallback

    Note: Anthropic doesn't have a public embeddings API yet.
    For dev purposes, we'll use a simple hash-based mock or you can
    integrate with another embedding service.

    Args:
        texts: List of texts to embed
        batch_size: Ignored (for compatibility)

    Returns:
        List of embedding vectors (mock implementation)
    """
    logging.warning("[Claude] Embeddings not available via Claude API. Using mock embeddings for dev.")

    # Mock embeddings - in production you'd use a real embedding service
    # This creates deterministic pseudo-embeddings based on text hash
    import hashlib

    embeddings = []
    for text in texts:
        # Create a deterministic "embedding" from text hash
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Convert to 1536 floats (same dimension as OpenAI embeddings)
        embedding = []
        for i in range(0, min(len(hash_bytes), 32)):
            # Spread each byte into ~48 dimensions
            byte_val = hash_bytes[i]
            for j in range(48):
                # Create varied float values from the byte
                val = ((byte_val + j * 7) % 256) / 255.0 - 0.5
                embedding.append(val)
                if len(embedding) >= 1536:
                    break
            if len(embedding) >= 1536:
                break

        # Pad if needed
        while len(embedding) < 1536:
            embedding.append(0.0)

        embeddings.append(embedding[:1536])

    return embeddings

def create_chunks_and_embeddings_from_pages(pages: List[Dict], batch_size: int = 500) -> List[Dict]:
    """
    Create embeddings for page chunks using mock embeddings

    Args:
        pages: List of page chunks with text, page_number, chunk_index
        batch_size: Ignored

    Returns:
        List of dicts with chunk, page_number, chunk_index, and embedding
    """
    logging.info(f"[Claude] Creating mock embeddings for {len(pages)} chunks")

    texts = [item["text"] for item in pages]
    embeddings = create_embeddings(texts)

    results = []
    for i, (page, embedding) in enumerate(zip(pages, embeddings)):
        results.append({
            "chunk": page["text"],
            "page_number": page["page_number"],
            "chunk_index": page.get("chunk_index", i),
            "embedding": embedding
        })

    return results
