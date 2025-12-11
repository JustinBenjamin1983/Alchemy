import requests
import logging
import os
import requests
from shared.utils import now

def save_to_search_index(doc_id, chunks_and_embeddings, safe_filename):
    logging.info("upload_to_search")
    url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    
    documents = []
    for item in chunks_and_embeddings:
        documents.append({
            "@search.action": "upload",
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
    logging.info(f"status code: {response.status_code}")
    response.raise_for_status()
    # logging.info("after post")

# def delete_from_search_index(doc_id):
#     logging.info("delete_from_search_index")
#     url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01"
#     headers = {
#         "Content-Type": "application/json",
#         "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
#     }

#     # Construct the delete payload
#     payload = {
#         "value": [
#             {
#                 "@search.action" : "delete",
#                 # "id": f"{doc_id}-{idx}"  # match exactly what was uploaded # TODO
#                 "document_id" : f"{doc_id}"
#             }
#             for idx in range(0, 50)  # adjust range or dynamically track how many chunks you uploaded # TODO
#         ]
#     }

#     response = requests.post(url, headers=headers, json=payload)
#     logging.info(f"status code: {response.status_code}")
#     response.raise_for_status()
#     logging.info("documents deleted from index")

def search_similar_documents(embedding: list, doc_ids: list, prompt: str, k: int = 3):
    logging.info("search_similar_documents")
    url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01"
    
    # filter = f"document_id eq '{doc_ids[0]}'"
    filter = " or ".join([f"document_id eq '{doc_id}'" for doc_id in doc_ids])

    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    body = {
        "top": k,
        "search": prompt, # TODO
        "filter": filter,
        # "highlight": "content",
        # "queryType": "semantic",
        "vectorQueries": [
            {
                "kind": "vector",
                "vector": embedding,
                "fields": "contentVector",
                "k": k
            }
        ]
    }
    # logging.info("body")
    # logging.info(body)
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