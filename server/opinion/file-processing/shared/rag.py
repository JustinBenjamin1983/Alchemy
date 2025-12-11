import logging
import os
import requests
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

def clean_text(text: str) -> str: # TODO
    text = re.sub(r"\s+", " ", text)  # normalize whitespace
    text = re.sub(r"\n{2,}", "\n", text)  # remove extra line breaks
    text = re.sub(r"Page \d+ of \d+", "", text)  # remove common footers
    text = text.strip()
    return text

def split_text(text, max_tokens=500):
    logging.info("split_text 2")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,  # 50 tokens overlap
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunks = text_splitter.split_text(text)
    return chunks

def split_text_by_page(pages, chunk_size=500, chunk_overlap=80):
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    split_chunks = []

    for page in pages:
        page_number = page["page_number"]
        text = page["text"]

        chunks = text_splitter.split_text(text)

        for idx, chunk in enumerate(chunks):
            split_chunks.append({
                "page_number": page_number,
                "chunk_index": idx,
                "text": chunk
            })

    return split_chunks


def create_chunks_and_embeddings_from_text(text: str):
    logging.info("create_chunks_and_embeddings_from_text")
    text_chunks = split_text(text)
    embeddings = []

    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ["AZURE_OPENAI_KEY"]
    }
    url = f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/deployments/{os.environ['EMBEDDING_DEPLOYMENT']}/embeddings?api-version=2023-05-15"

    for chunk in text_chunks:
        data = {"input": chunk}
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        logging.info(f"create_chunks_and_embeddings_from_text status code {response.status_code}")
        embedding = response.json()["data"][0]["embedding"]
        embeddings.append({
            "chunk": chunk,
            "embedding": embedding
        })
    
    return embeddings

# def create_chunks_and_embeddings_from_pages(pages):
#     logging.info("create_chunks_and_embeddings_from_pages")
#     embeddings = []

#     headers = {
#         "Content-Type": "application/json",
#         "api-key": os.environ["AZURE_OPENAI_KEY"]
#     }
#     url = f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/deployments/{os.environ['EMBEDDING_DEPLOYMENT']}/embeddings?api-version=2023-05-15"

#     for idx, chunk in enumerate(pages):
#         text = chunk["text"]
#         page_number = chunk["page_number"]
#         data = {"input": text}
        
#         response = requests.post(url, headers=headers, json=data)
#         response.raise_for_status()

#         logging.info(f"create_chunks_and_embeddings_from_pages {idx=} status code {response.status_code}")
#         embedding = response.json()["data"][0]["embedding"]
#         embeddings.append({
#             "chunk": text,
#             "chunk_index": chunk.get("chunk_index", idx), # shouldn't need default idx
#             "page_number": page_number,
#             "embedding": embedding
#         })
    
#     return embeddings
def create_chunks_and_embeddings_from_pages(pages, batch_size=16):
    logging.info("create_chunks_and_embeddings_from_pages")
    embeddings = []

    headers = {
        "Content-Type": "application/json",
        "api-key": os.environ["AZURE_OPENAI_KEY"]
    }
    url = f"{os.environ['AZURE_OPENAI_ENDPOINT']}/openai/deployments/{os.environ['EMBEDDING_DEPLOYMENT']}/embeddings?api-version=2023-05-15"

    # Flatten input with tracking
    # tracked_chunks = []
    # for chunk in pages:
    #     tracked_chunks.append({
    #         "text": chunk["text"],
    #         "page_number": chunk["page_number"],
    #         # "chunk_index": chunk.get("chunk_index", idx)
    #         "chunk_index": chunk.get["chunk_index"]
    #     })

    # Send in batches
    for i in range(0, len(pages), batch_size):
        batch = pages[i:i + batch_size]
        texts = [item["text"] for item in batch]
        data = {"input": texts}

        response = requests.post(url, headers=headers, json=data)
        logging.info(f"create_chunks_and_embeddings_from_pages {i=} status code {response.status_code}")
        response.raise_for_status() # TODO
        
        batch_embeddings = response.json()["data"]

        for j, emb in enumerate(batch_embeddings):
            item = batch[j]
            embeddings.append({
                "chunk": item["text"],
                "page_number": item["page_number"],
                "chunk_index": item["chunk_index"],
                "embedding": emb["embedding"]
            })

        logging.info(f"Processed batch {i // batch_size + 1} of {len(pages) // batch_size + 1}")

    return embeddings