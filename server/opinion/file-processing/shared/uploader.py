import os
import logging
from requests_toolbelt.multipart import decoder
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from datetime import datetime, timedelta
import fitz  # PyMuPDF
from docx import Document
from shared.search import save_to_search_index
from shared.rag import create_chunks_and_embeddings_from_pages, create_chunks_and_embeddings_from_text, split_text_by_page

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from io import BytesIO

PROCESSING_SIZE = 50

# def is_above_synchronous_indexing_threshold(file_bytes)->bool:
#     return get_kb_size(file_bytes) > 300

# def get_kb_size(file_bytes):
#     return len(file_bytes) / 1024

def handle_file(file_bytes, safe_filename: str, extension: str, doc_id: str, next_chunk_to_process: int) -> bool:
    logging.info(f"handle_file {extension=}")

    # if is_above_synchronous_indexing_threshold(file_bytes):
    #     return False

    pages = None
    if extension == "pdf":
        logging.info("a pdf")
        pages = extract_pages_of_text_from_pdf(file_bytes) # {"page_number": page_num + 1, "text": text}
        if not is_text_meaningful(pages):
            logging.info("likely a scan")
            pages = extract_text_via_ocr(file_bytes)
    elif extension == "docx":
        logging.info("a docx")
        pages = extract_text_from_docx(file_bytes)

    pages_chunked = split_text_by_page(pages, chunk_size=800, chunk_overlap=80)
    
    # logging.info("all page numbers")
    # logging.info(sorted(item["page_number"] for item in pages_chunked))
    # [logging.info(f"***-*** Page {item['page_number']} (chunk {item['chunk_index']}):\n{item['text']}\n{'-' * 80}") 
    #     for item in pages_chunked if 20 <= item["page_number"] <= 30]

    # list slicing is exclusive of the end index
    chunk_stop = next_chunk_to_process + PROCESSING_SIZE
    chunks_to_process = pages_chunked[next_chunk_to_process: chunk_stop]

    logging.info(f"total pages_chunked: {len(pages_chunked)} {next_chunk_to_process=} {chunk_stop=} chunks_to_process len:{len(chunks_to_process)}")

    chunks_and_embeddings = create_chunks_and_embeddings_from_pages(chunks_to_process) # { "chunk": text, "page_number": page_number, "embedding": embedding }

    save_to_search_index(doc_id, chunks_and_embeddings, safe_filename)

    return (chunk_stop, len(pages_chunked))


def handle_text(text, filename: str, doc_id: str):
    
    chunks_and_embeddings = create_chunks_and_embeddings_from_text(text) # { "chunk": text, "page_number": page_number, "embedding": embedding }

    save_to_search_index(doc_id, chunks_and_embeddings, filename)


def is_text_meaningful(pages, min_words_per_page=10, min_ratio=0.5):
    """
    Returns True if at least `min_ratio` of pages have more than `min_words_per_page` words.
    pages = [{'text':'abc'}]
    """
    if not pages:
        return False

    def word_count(text):
        return len(text.strip().split())

    total_pages = len(pages)
    informative_pages = sum(
        1 for page in pages if word_count(page["text"]) >= min_words_per_page
    )

    ratio = informative_pages / total_pages
    return ratio >= min_ratio

def extract_pages_of_text_from_pdf(file_bytes):
    doc = fitz.open(stream=file_bytes, filetype="pdf")

    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        pages.append({"page_number": page_num + 1, "text": text})
    
    return pages

def extract_text_via_ocr(file_stream):
    client = DocumentAnalysisClient(os.environ["AZURE_FORM_RECOGNIZER_ENDPOINT"], AzureKeyCredential(os.environ["AZURE_FORM_RECOGNIZER_KEY"]))
    poller = client.begin_analyze_document("prebuilt-read", document=file_stream)
    result = poller.result()

    pages = []
    for i, page in enumerate(result.pages):
        page_text = "\n".join([line.content for line in page.lines])
        pages.append({"page_number": i + 1, "text": page_text})

    # logging.info("result of ocr")
    # logging.info(pages)
    return pages

def extract_text_from_docx(file_bytes) -> str:
    doc = Document(BytesIO(file_bytes))
    text = []

    for para in doc.paragraphs:
        text.append(para.text)

    all_text = "\n".join(text).strip()

    return [{"page_number": 0, "text": all_text}] # TODO add pages support


def write_to_blob_storage(connection_string, container_name, key, blob, meta_data = None, overwrite=True):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    blob_client.upload_blob(blob, metadata=meta_data or {}, overwrite=overwrite)

def read_from_blob_storage(connection_string, container_name, key):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)

    downloader = blob_client.download_blob()
    file_bytes = downloader.readall()

    return file_bytes

def delete_from_blob_storage(connection_string, container_name, key):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    blob_client.delete_blob()
    logging.info(f"deleted blob {key=}")

def get_content_type(extension):
    # logging.info(f"trying to find content type of ext {extension=}")
    if extension == "pdf":
        return "application/pdf"
    elif extension == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        logging.info(f"unknown extension of {extension=} can't find content type")

def get_blob_metadata(connection_string, container_name, key):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    
    props = blob_client.get_blob_properties()
    # logging.info(f"meta data of {key}")
    # logging.info(props.metadata)

    return props.metadata

def set_blob_metadata(connection_string, container_name, key, new_metadata):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)

    blob_client.set_blob_metadata(metadata=new_metadata)

    return True

def get_blob_sas_url(connection_string, container_name, key, expiry_minutes=60):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    
    props = blob_client.get_blob_properties()
    logging.info(f"meta data of {key}") # {"original_file_name":safe_filename, "extension": extension}
    logging.info(props.metadata)

    blob_client.set_http_headers(
        content_settings=ContentSettings(
            content_type=get_content_type(props.metadata["extension"]),
            content_disposition=f'inline; filename="{props.metadata['original_file_name']}"'
        )
    )
    logging.info("set headers")
    

    blob_url = blob_client.url
    logging.info("got url")

    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        account_key=blob_service_client.credential.account_key,
        container_name=container_name,
        blob_name=key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )

    return f"{blob_url}?{sas_token}"

def extract_file(req):
    
    uploaded_filename = None
    uploaded_file_content = None

    multipart_data = decoder.MultipartDecoder(req.get_body(), req.headers.get("content-type"))

    for part in multipart_data.parts:
        content_disposition = part.headers.get(b"Content-Disposition", b"").decode()
        if 'name="file"' in content_disposition:
            # Extract filename
            filename_marker = 'filename="'
            start = content_disposition.find(filename_marker) + len(filename_marker)
            end = content_disposition.find('"', start)
            uploaded_filename = content_disposition[start:end]
            uploaded_file_content = part.content
            break

    if not uploaded_filename or not uploaded_file_content:
        logging.info("error in extract_file") # TODO

    safe_filename = os.path.basename(uploaded_filename)
    extension = os.path.splitext(safe_filename)[1].lstrip(".")

    return safe_filename, extension, uploaded_file_content
