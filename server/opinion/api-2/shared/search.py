# File: server/opinion/api_2/shared/search.py

import requests
import logging
import os
from shared.utils import now

# Check for dev mode
def _is_dev_mode():
    return os.environ.get("DEV_MODE", "").lower() in ("true", "1", "yes", "local")

# Conditionally import local search adapter for dev mode
if _is_dev_mode():
    logging.info("🔧 [search] DEV MODE - Using local search adapter")
    from shared.dev_adapters.local_search import (
        add_to_index as _dev_add_to_index,
        search as _dev_search,
        delete_from_index as _dev_delete_from_index
    )

def save_to_search_index(doc_id, chunks_and_embeddings, safe_filename, batch_size = 10):
    logging.info(f"save_to_search_index, total chunks_and_embeddings {len(chunks_and_embeddings)}")

    # Use local search adapter in dev mode
    if _is_dev_mode():
        index_name = os.environ.get('SEARCH_INDEX_NAME', 'dev-search-index')
        documents = []
        for item in chunks_and_embeddings:
            documents.append({
                "id": f"{doc_id}-{item['page_number']}-{item['chunk_index']}",
                "doc_id": f"{doc_id}",
                "content": item["chunk"],
                "embedding": item.get("embedding"),
                "filename": safe_filename,
                "page_number": item["page_number"] if item.get("page_number", None) else -1
            })
        _dev_add_to_index(index_name, documents)
        logging.info(f"✅ [LocalSearch] Indexed {len(documents)} chunks for {doc_id}")
        return

    url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }

    for i in range(0, len(chunks_and_embeddings), batch_size):
        logging.info(f"doing batch from {i} of {len(chunks_and_embeddings)}")
        batch = chunks_and_embeddings[i:i + batch_size]
        documents = []
        for item in batch:
            documents.append({
                "@search.action": "upload",
                # "id": f"{doc_id}-{idx}",
                "id": f"{doc_id}-{item['page_number']}-{item['chunk_index']}",
                "document_id": f"{doc_id}",
                "content": item["chunk"],
                "contentVector": item["embedding"],
                "filename": safe_filename,
                "page_number": item["page_number"] if item.get("page_number", None) else -1,
                "createdDate": now()  # ISO format string e.g. "2025-04-22T11:00:00Z"
            })

        payload = {"value": documents}
        response = requests.post(url, headers=headers, json=payload)
        logging.info(f"save_to_search_index status code: {response.status_code}")
        response.raise_for_status()
        logging.info("after post")

    logging.info("done with save_to_search_index")

def delete_from_search_index(doc_id):
    logging.info("delete_from_search_index")

    # Use local search adapter in dev mode
    if _is_dev_mode():
        index_name = os.environ.get('SEARCH_INDEX_NAME', 'dev-search-index')
        # Delete all documents with matching doc_id prefix
        _dev_delete_from_index(index_name, [doc_id])
        logging.info(f"🗑️ [LocalSearch] Deleted documents for {doc_id}")
        return

    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }

    search_body = {
        "search": "*",
        "filter": f"document_id eq '{doc_id}'",
        "select": "id",
        "top": 1000 # TODO may need to check for paging
    }
    logging.info(f"{search_body=}")
    search_response = requests.post(f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01", headers=headers, json=search_body)
    logging.info(f"search response: {search_response.status_code}")
    search_response.raise_for_status()
    logging.info(search_response)
    docs = search_response.json().get("value", [])
    if not docs:
        logging.info(f"No documents found for {doc_id=}.")
        return

    delete_payload = {
        "value": [
            {
                "@search.action": "delete",
                "id": doc["id"]
            }
            for doc in docs
        ]
    }
    logging.info(f"{delete_payload=}")

    response = requests.post(f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01", headers=headers, json=delete_payload)
    logging.info(f"status code: {response.status_code}")
    response.raise_for_status()
    logging.info("documents deleted from index")

def search_similar_documents(embedding: list, doc_ids: list, prompt: str, k: int = 3):
    logging.info("search_similar_documents")

    # Use local search adapter in dev mode
    if _is_dev_mode():
        index_name = os.environ.get('SEARCH_INDEX_NAME', 'dev-search-index')
        # Use text-based search (BM25) since we have mock embeddings
        results = _dev_search(index_name, prompt, top_k=k, filters={'doc_id': doc_ids[0]} if len(doc_ids) == 1 else None)

        # Format results to match Azure Cognitive Search response format
        formatted_results = []
        for r in results:
            formatted_results.append({
                "id": r.get("id"),
                "document_id": r.get("doc_id"),
                "content": r.get("content"),
                "filename": r.get("filename"),
                "page_number": r.get("page_number", -1),
                "@search.score": r.get("score", 0)
            })

        logging.info(f"[LocalSearch] Found {len(formatted_results)} results for '{prompt[:50]}...'")
        return {"value": formatted_results}

    url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01"

    filter = " or ".join([f"document_id eq '{doc_id}'" for doc_id in doc_ids])

    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    logging.info(f"{filter=}")
    body = {}
    match os.environ['AISearchType']: # with_search, just_embeddings
        case "with_search":
            body = {
                "top": k,
                "search": prompt,
                "filter": filter,
                "vectorQueries": [
                    {
                        "kind": "vector",
                        "vector": embedding,
                        "fields": "contentVector",
                        "k": k
                    }
                ]
            }
        case "just_embeddings":
            body = {
                "top": k,
                "filter": filter,
                "vectorQueries": [
                    {
                        "kind": "vector",
                        "vector": embedding,
                        "fields": "contentVector",
                        "k": k
                    }
                ]
            }
    logging.info(f"{body=}")
    response = requests.post(url, headers=headers, json=body)
    logging.info(f"status code: {response.status_code}")
    response.raise_for_status()
    return response.json()

def format_search_results_for_prompt(results: list) -> str:
    """
    Converts a list of search result documents into a prompt-friendly string.

    Each result must contain 'filename', 'page_number', and 'content'.
    """
    formatted_chunks = []

    for doc in results:
        filename = doc.get("filename", "Unknown file")
        page = doc.get("page_number", "N/A")
        content = doc.get("content", "").strip()

        if content:
            chunk = (
                f"Filename: {filename} (Page {page})\n"
                f"Excerpt: {content}\n"
            )
            formatted_chunks.append(chunk)

    return "\n---\n".join(formatted_chunks)