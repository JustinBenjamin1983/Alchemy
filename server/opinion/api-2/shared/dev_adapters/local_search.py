# Local Search Adapter - Simple text search to replace Azure Cognitive Search
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
import math

# In-memory search index for dev purposes
_search_indices = defaultdict(list)

def _normalize_text(text: str) -> str:
    """Normalize text for searching"""
    if not text:
        return ""
    # Lowercase, remove extra whitespace
    text = re.sub(r'\s+', ' ', text.lower().strip())
    return text

def _tokenize(text: str) -> List[str]:
    """Simple tokenization"""
    text = _normalize_text(text)
    # Split on non-word characters
    tokens = re.findall(r'\b\w+\b', text)
    return tokens

def _calculate_bm25_score(query_tokens: List[str], doc_tokens: List[str],
                          avg_doc_length: float, k1: float = 1.5, b: float = 0.75) -> float:
    """Calculate BM25 relevance score"""
    if not query_tokens or not doc_tokens:
        return 0.0

    doc_length = len(doc_tokens)
    score = 0.0

    # Count term frequencies in document
    doc_tf = defaultdict(int)
    for token in doc_tokens:
        doc_tf[token] += 1

    for term in query_tokens:
        if term in doc_tf:
            tf = doc_tf[term]
            # Simplified BM25 formula
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
            score += numerator / denominator

    return score

# ============== Search Index Operations ==============

def add_to_index(index_name: str, documents: List[Dict]) -> bool:
    """
    Add documents to the search index

    Args:
        index_name: Name of the search index
        documents: List of documents with 'id', 'content', and other fields

    Returns:
        bool: True if successful
    """
    try:
        for doc in documents:
            doc_id = doc.get('id') or doc.get('doc_id')
            content = doc.get('content', '')

            # Create searchable entry
            entry = {
                'id': doc_id,
                'content': content,
                'tokens': _tokenize(content),
                'metadata': {k: v for k, v in doc.items() if k not in ('id', 'content', 'tokens')}
            }

            # Remove existing entry with same ID
            _search_indices[index_name] = [
                d for d in _search_indices[index_name] if d['id'] != doc_id
            ]

            _search_indices[index_name].append(entry)

        logging.info(f"✅ [LocalSearch] Added {len(documents)} docs to index '{index_name}'")
        return True

    except Exception as e:
        logging.error(f"❌ [LocalSearch] Error adding to index: {e}")
        return False

def search(index_name: str, query: str, top_k: int = 10,
           filters: Dict = None) -> List[Dict]:
    """
    Search the index

    Args:
        index_name: Name of the search index
        query: Search query
        top_k: Number of results to return
        filters: Optional filters (e.g., {'doc_id': 'xxx'})

    Returns:
        List of matching documents with scores
    """
    try:
        index = _search_indices.get(index_name, [])

        if not index:
            logging.warning(f"[LocalSearch] Index '{index_name}' is empty")
            return []

        query_tokens = _tokenize(query)

        if not query_tokens:
            return []

        # Calculate average document length
        total_tokens = sum(len(doc['tokens']) for doc in index)
        avg_doc_length = total_tokens / len(index) if index else 1

        # Score all documents
        scored_docs = []
        for doc in index:
            # Apply filters
            if filters:
                skip = False
                for key, value in filters.items():
                    doc_value = doc.get(key) or doc.get('metadata', {}).get(key)
                    if doc_value != value:
                        skip = True
                        break
                if skip:
                    continue

            score = _calculate_bm25_score(query_tokens, doc['tokens'], avg_doc_length)

            if score > 0:
                scored_docs.append({
                    'id': doc['id'],
                    'content': doc['content'],
                    'score': score,
                    **doc.get('metadata', {})
                })

        # Sort by score and return top_k
        scored_docs.sort(key=lambda x: x['score'], reverse=True)

        logging.info(f"[LocalSearch] Found {len(scored_docs)} results for '{query[:50]}...'")
        return scored_docs[:top_k]

    except Exception as e:
        logging.error(f"❌ [LocalSearch] Search error: {e}")
        return []

def delete_from_index(index_name: str, doc_ids: List[str]) -> bool:
    """
    Delete documents from the index

    Args:
        index_name: Name of the search index
        doc_ids: List of document IDs to delete

    Returns:
        bool: True if successful
    """
    try:
        original_count = len(_search_indices.get(index_name, []))

        _search_indices[index_name] = [
            doc for doc in _search_indices.get(index_name, [])
            if doc['id'] not in doc_ids
        ]

        deleted_count = original_count - len(_search_indices[index_name])
        logging.info(f"🗑️ [LocalSearch] Deleted {deleted_count} docs from '{index_name}'")
        return True

    except Exception as e:
        logging.error(f"❌ [LocalSearch] Delete error: {e}")
        return False

def clear_index(index_name: str) -> bool:
    """Clear all documents from an index"""
    _search_indices[index_name] = []
    logging.info(f"🗑️ [LocalSearch] Cleared index '{index_name}'")
    return True

# ============== Azure Search API Compatible Functions ==============

def index_documents(index_name: str, documents: List[Dict]) -> Dict:
    """
    Index documents (Azure Search compatible)

    Args:
        index_name: Index name
        documents: Documents to index

    Returns:
        Dict with results
    """
    success = add_to_index(index_name, documents)
    return {
        'value': [{'key': doc.get('id'), 'status': success} for doc in documents]
    }

def search_documents(index_name: str, search_text: str, top: int = 10,
                     filter_str: str = None, select: List[str] = None) -> Dict:
    """
    Search documents (Azure Search compatible)

    Args:
        index_name: Index name
        search_text: Search query
        top: Number of results
        filter_str: Filter string (simplified parsing)
        select: Fields to return

    Returns:
        Dict with search results
    """
    # Parse simple filter string
    filters = {}
    if filter_str:
        # Handle simple equality filters like "doc_id eq 'xxx'"
        match = re.search(r"(\w+)\s+eq\s+'([^']+)'", filter_str)
        if match:
            filters[match.group(1)] = match.group(2)

    results = search(index_name, search_text, top, filters)

    # Format like Azure Search response
    return {
        'value': results,
        '@odata.count': len(results)
    }

def delete_documents(index_name: str, keys: List[str]) -> Dict:
    """
    Delete documents (Azure Search compatible)
    """
    success = delete_from_index(index_name, keys)
    return {
        'value': [{'key': key, 'status': success} for key in keys]
    }

# ============== Vector Search (Simplified) ==============

def vector_search(index_name: str, query_embedding: List[float],
                  top_k: int = 10, filters: Dict = None) -> List[Dict]:
    """
    Vector similarity search using cosine similarity

    Note: This is a simplified implementation. For production,
    you'd want to use a proper vector database.

    Args:
        index_name: Index name
        query_embedding: Query vector
        top_k: Number of results
        filters: Optional filters

    Returns:
        List of results with similarity scores
    """
    try:
        index = _search_indices.get(index_name, [])

        if not index:
            return []

        def cosine_similarity(a: List[float], b: List[float]) -> float:
            if len(a) != len(b):
                return 0.0
            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot_product / (norm_a * norm_b)

        scored_docs = []
        for doc in index:
            # Apply filters
            if filters:
                skip = False
                for key, value in filters.items():
                    doc_value = doc.get(key) or doc.get('metadata', {}).get(key)
                    if doc_value != value:
                        skip = True
                        break
                if skip:
                    continue

            # Calculate similarity if document has embedding
            doc_embedding = doc.get('metadata', {}).get('embedding')
            if doc_embedding:
                score = cosine_similarity(query_embedding, doc_embedding)
                if score > 0:
                    scored_docs.append({
                        'id': doc['id'],
                        'content': doc['content'],
                        'score': score,
                        **{k: v for k, v in doc.get('metadata', {}).items() if k != 'embedding'}
                    })

        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs[:top_k]

    except Exception as e:
        logging.error(f"❌ [LocalSearch] Vector search error: {e}")
        return []
