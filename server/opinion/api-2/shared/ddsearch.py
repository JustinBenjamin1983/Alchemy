import requests
import logging
import os
import requests
from shared.utils import now, generate_identifier
from typing import List, Dict, Any

def save_to_dd_search_index(dd_id, doc_id, folder_path, folder_path_special, chunks_and_embeddings, safe_filename, batch_size = 100):
    logging.info(f"save_to_dd_search_index, total chunks_and_embeddings {len(chunks_and_embeddings)}")
    url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    
    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }
    
    for i in range(0, len(chunks_and_embeddings), batch_size):
        # logging.info(f"doing batch from {i} of {len(chunks_and_embeddings)}")
        batch = chunks_and_embeddings[i:i + batch_size]
        documents = []
        for item in batch:
            documents.append({
                "@search.action": "upload",
                # "id": f"{doc_id}-{idx}",
                "id": f"{doc_id}-{item['page_number']}-{item['chunk_index']}",
                "dd_id": f"{dd_id}",
                "document_id": f"{doc_id}",
                "content": item["chunk"],
                "contentVector": item["embedding"],
                "filename": safe_filename, 
                "page_number": item["page_number"] if item.get("page_number", None) else -1,
                "folder_path": folder_path,
                "folder_path_special": folder_path_special,
                "createdDate": now()  # ISO format string e.g. "2025-04-22T11:00:00Z"
            })

        payload = {"value": documents}
        response = requests.post(url, headers=headers, json=payload)
        logging.info(f"save_to_dd_search_index status code: {response.status_code}")
        response.raise_for_status()
        # logging.info("after post")

    # logging.info("done with save_to_dd_search_index")



def update_search_index(doc_id, folder_path, folder_path_special, new_doc_name):
    
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
    search_response = requests.post(f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01", headers=headers, json=search_body)
    logging.info(f"search response: {search_response.status_code}")
    search_response.raise_for_status()
    logging.info(search_response)
    docs = search_response.json().get("value", [])
    if not docs:
        logging.info(f"No documents found for {doc_id=}.")
        return

    update_payload = {
        "value": [
            {
                "@search.action": "merge",
                "id": doc["id"],
                **({"folder_path": folder_path} if folder_path else {}),
                **({"folder_path_special": folder_path_special} if folder_path_special else {}),
                **({"filename": new_doc_name} if new_doc_name else {}),
            }
            for doc in docs
        ]
    }
    logging.info(f"{update_payload=}")

    response = requests.post(f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01", headers=headers, json=update_payload)
    logging.info(f"status code: {response.status_code}")
    response.raise_for_status()
    logging.info("documents update in index")
    

def delete_from_dd_search_index(doc_id):
    logging.info("delete_from_search_index")
    
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
    search_response = requests.post(f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01", headers=headers, json=search_body)
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

    response = requests.post(f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/index?api-version=2023-11-01", headers=headers, json=delete_payload)
    logging.info(f"status code: {response.status_code}")
    response.raise_for_status()
    logging.info("documents deleted from index")

def build_filter(dd_id: str, folder_path_special: str = None, doc_ids: list = None) -> str:
    filters = [f"dd_id eq '{dd_id}'"]

    if doc_ids:
        doc_filters = " or ".join([f"document_id eq '{doc_id}'" for doc_id in doc_ids])
        filters.append(f"({doc_filters})")

    if folder_path_special:
        filters.append(f"folder_path_special eq '{folder_path_special}'")

    return " and ".join(filters)

def search_similar_dd_documents(dd_id: str, folder_hierarchy_ids: str, doc_ids: list, embedding: list, prompt: str, keyword_only: bool, k: int = 3):
    
    if not prompt:
        raise ValueError("Prompt cant be empty.")
    
    prompt = prompt.replace("\n", " ")
    
    url = f"{os.environ['COGNITIVE_SEARCH_ENDPOINT']}/indexes/{os.environ['DD_SEARCH_INDEX_NAME']}/docs/search?api-version=2023-11-01"
    
    filter = build_filter(dd_id, folder_hierarchy_ids, doc_ids)
    
    logging.info(f"search_similar_dd_documents {filter=}")
    logging.info(f"search_similar_dd_documents {prompt=}")
    
    # length issue when searching:
    # eg:
    #     this breaks:
    #         Your task is to review legal and financial documents as part of a due diligence exercise. You are looking for any content that may relate to or raise concerns about the client's specified risk. The client has described the overall due diligence objectives as follows: The client wishes to establish risks in existing trademarks. Risk Description: Does the contract start after 2015. Risk Category: Shareholding and corporate structure. Carefully examine the content to determine if it is relevant to the above-described risk.
    #     this works:
    #         Your task is to review legal and financial documents as part of a due diligence exercise.  The client has described the overall due diligence objectives as follows: The client wishes to establish risks in existing trademarks. Risk Description: Does the contract start after 2015. Risk Category: Shareholding and corporate structure. Carefully examine the content to determine if it is relevant to the above-described risk.

    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ['COGNITIVE_SEARCH_API_KEY']
    }

    body = {}
    if keyword_only:
        logging.info("search_similar_dd_documents keyword only")
        body = {
            "top": k,
            "filter": filter,
            "search": prompt
        }
            # body = {
            #     "top": k,
            #     "search": prompt,
            #     "filter": filter,
            #     # "highlight": "content",
            #     # "queryType": "semantic",
            #     "vectorQueries": [
            #         {
            #             "kind": "vector",
            #             "vector": embedding,
            #             "fields": "contentVector",
            #             "k": k
            #         }
            #     ]
            # }
    else:
        logging.info("search_similar_dd_documents with embeddings, no 'search'")
        body = {
            "search": "*",
            "top": k,
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
        # case "3":
        #     body = {
        #         "top": k,
        #         "filter": filter,
        #         "search": prompt
        #     }
    response = requests.post(url, headers=headers, json=body)
    logging.info(f"status code: {response.status_code}")
    response.raise_for_status()
    return response.json()

def format_search_results_for_prompt(results: list) ->  List[Dict[str, Any]]:
    """
    Converts a list of search result documents into a prompt-friendly string.

    Each result must contain 'filename', 'page_number', and 'content'.
    """
    reasonable_amount_of_content_chars = 20
    formatted_chunks = []

    for doc in results:
        filename = doc.get("filename", "Unknown file")
        doc_id = doc.get("document_id", "N/A")
        page_number = doc.get("page_number", "N/A")
        folder_path = doc.get("folder_path")
        score = doc.get("@search.score")
        content = doc.get("content", "").strip()
        useful_content = content if content and len(content) > reasonable_amount_of_content_chars else None

        if useful_content:
            item = { 
                "result_id": generate_identifier(), # non-deterministic but for UI/uniqueness within results
                "doc_id": doc_id,
                'score': score,
                "filename": filename,
                "page_number": page_number,
                "content": content,
                "folder_path": folder_path
                }
            formatted_chunks.append(item)

    return formatted_chunks