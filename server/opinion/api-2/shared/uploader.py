# File: server/opinion/api_2/shared/uploader.py

import os
import logging
from requests_toolbelt.multipart import decoder
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from datetime import datetime, timedelta
from shared.ddsearch import save_to_dd_search_index
from shared.search import save_to_search_index
from shared.rag import create_chunks_and_embeddings_from_pages, create_chunks_and_embeddings_from_text, split_text_by_page
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from io import BytesIO
import time
from azure.core.exceptions import HttpResponseError

def is_above_synchronous_indexing_threshold(file_bytes)->bool:
    return get_kb_size(file_bytes) > 300

def get_kb_size(file_bytes):
    return len(file_bytes) / 1024

def get_file_type(filename: str) -> str:
    """
    Updated to recognize all supported file types for OCR processing.
    """
    ext = filename.split(".")[-1].lower()
    
    # All supported types by Azure Document Intelligence (v4.0)
    if ext in ["pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "bmp", "tiff", "html"]:
        return ext
    
    return "OTHER"

PROCESSING_SIZE = 200

def handle_file_with_next_chunk_to_process(
    file_bytes: bytes,
    safe_filename: str,
    extension: str,
    dd_id: str,
    doc_id: str,
    folder_path: str,
    folder_path_special: str,
    next_chunk_to_process: int,
):
    """
    Updated to use new Azure Document Intelligence SDK with Office support.
    Returns (chunk_stop, pages_total, status).
    """

    SUPPORTED = {"pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "bmp", "tiff"}
    
    if extension not in SUPPORTED:
        logging.info(f"🟡 Unsupported extension '{extension}' – marking as unsupported: {safe_filename}")
        return (0, 0, "unsupported")
    
    try:
        # Use the new Document Intelligence client
        pages = extract_text_with_new_client(file_bytes, extension, safe_filename)
            
        if not pages:
            logging.warning(f"No text extracted from {safe_filename}; marking as failed")
            return (0, 0, "failed")
        
        pages_chunked = split_text_by_page(pages, chunk_size=800, chunk_overlap=80)
        chunk_stop = next_chunk_to_process + PROCESSING_SIZE
        chunks_to_process = pages_chunked[next_chunk_to_process:chunk_stop]
        
        logging.info(
            f"{safe_filename}: {len(pages_chunked)=} {next_chunk_to_process=} "
            f"{chunk_stop=} chunks_to_process={len(chunks_to_process)}"
        )
        
        chunks_and_embeddings = create_chunks_and_embeddings_from_pages(chunks_to_process)
        save_to_dd_search_index(
            dd_id,
            doc_id,
            folder_path,
            folder_path_special,
            chunks_and_embeddings,
            safe_filename,
        )
        
        return (chunk_stop, len(pages_chunked), "success")
        
    except Exception as e:
        logging.error(f"Failed to process {safe_filename}: {str(e)}")
        return (0, 0, "failed")

def handle_file(file_bytes, safe_filename: str, extension: str, doc_id: str) -> bool:
    """
    Updated to use new Azure Document Intelligence SDK.
    """
    if is_above_synchronous_indexing_threshold(file_bytes):
        logging.info("above sync indexing threshold")
        return False
    
    try:
        pages = extract_text_with_new_client(file_bytes, extension, safe_filename)
        pages_chunked = split_text_by_page(pages)
        chunks_and_embeddings = create_chunks_and_embeddings_from_pages(pages_chunked)
        save_to_search_index(doc_id, chunks_and_embeddings, safe_filename)
        return True
    except Exception as e:
        logging.error(f"Failed to process {safe_filename}: {str(e)}")
        return False

def extract_text_with_new_client(file_bytes: bytes, extension: str, filename: str):
    """
    Uses azure-ai-documentintelligence client with proper Office document support.
    """
    # Create the Document Intelligence client with custom polling interval
    client = DocumentIntelligenceClient(
        endpoint=os.environ["AZURE_FORM_RECOGNIZER_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_FORM_RECOGNIZER_KEY"])
    )
    
    logging.info(f"Starting Document Intelligence v4.0 for {extension.upper()} file: {filename}")
    
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            model_id = get_optimal_model_for_filetype(extension)

            if extension in ['docx', 'xlsx', 'pptx']:

                poller = client.begin_analyze_document(
                    model_id=model_id,
                    body=file_bytes,
                    content_type="application/octet-stream",
                    polling_interval=1  
                )
            else:
                # For PDFs and images, use AnalyzeDocumentRequest
                analyze_request = AnalyzeDocumentRequest(bytes_source=file_bytes)
                poller = client.begin_analyze_document(
                    model_id=model_id,
                    body=analyze_request,
                    polling_interval=5  # Override default 30 seconds
                )
            
            # Wait for the operation to complete with timeout
            # Office documents can take longer to process
            timeout = 300 if extension in ['docx', 'xlsx', 'pptx'] else 120
            
            logging.info(f"Waiting for analysis to complete (timeout: {timeout}s)...")
            
            result = poller.result(timeout=timeout)
            
            # Process the result
            pages = []
            
            # Check if we have pages in the result
            if hasattr(result, 'pages') and result.pages:
                for page_idx, page in enumerate(result.pages):
                    page_content_parts = []
                    
                    # Extract lines (main text content)
                    if hasattr(page, 'lines') and page.lines:
                        for line in page.lines:
                            if hasattr(line, 'content') and line.content:
                                page_content_parts.append(line.content)
                    
                    # For Office documents, also check for words if lines are empty
                    if not page_content_parts and hasattr(page, 'words') and page.words:
                        current_line = []
                        last_y = None
                        
                        for word in page.words:
                            if hasattr(word, 'content') and word.content:
                                # Simple line detection based on Y coordinate
                                if last_y is not None and hasattr(word, 'polygon') and word.polygon:
                                    current_y = word.polygon[1] if len(word.polygon) > 1 else None
                                    if current_y and abs(current_y - last_y) > 10:
                                        if current_line:
                                            page_content_parts.append(' '.join(current_line))
                                            current_line = []
                                
                                current_line.append(word.content)
                                
                                if hasattr(word, 'polygon') and word.polygon and len(word.polygon) > 1:
                                    last_y = word.polygon[1]
                        
                        if current_line:
                            page_content_parts.append(' '.join(current_line))
                    
                    # Extract tables
                    if hasattr(result, 'tables') and result.tables:
                        page_tables = [
                            table for table in result.tables 
                            if hasattr(table, 'bounding_regions') and 
                            table.bounding_regions and 
                            len(table.bounding_regions) > 0 and
                            table.bounding_regions[0].page_number == page_idx + 1
                        ]
                        
                        for table in page_tables:
                            table_text = extract_table_text(table)
                            if table_text:
                                page_content_parts.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")
                    
                    # Combine all content for this page
                    page_text = "\n".join(page_content_parts).strip()
                    
                    if page_text:
                        pages.append({"page_number": page_idx + 1, "text": page_text})
            
            # Alternative: Check for content in the result directly
            if not pages and hasattr(result, 'content') and result.content:
                # Some models return content directly without page structure
                logging.info("No pages found, using direct content extraction")
                pages.append({"page_number": 1, "text": result.content})
            
            # For Office documents, also check paragraphs if available
            if not pages and hasattr(result, 'paragraphs') and result.paragraphs:
                logging.info("Using paragraph extraction for Office document")
                full_text = []
                for paragraph in result.paragraphs:
                    if hasattr(paragraph, 'content') and paragraph.content:
                        full_text.append(paragraph.content)
                
                if full_text:
                    pages.append({"page_number": 1, "text": "\n\n".join(full_text)})
            
            if pages:
                logging.info(f"Successfully extracted text from {len(pages)} pages/slides/sheets")
                return pages
            else:
                logging.warning(f"No content extracted from {filename}")
                
                # Log more details about the result structure for debugging
                logging.debug(f"Result attributes: {dir(result)}")
                if hasattr(result, 'pages'):
                    logging.debug(f"Number of pages in result: {len(result.pages) if result.pages else 0}")
                    if result.pages and len(result.pages) > 0:
                        logging.debug(f"First page attributes: {dir(result.pages[0])}")
                
                # Don't immediately fail, try fallback
                
        except HttpResponseError as e:
            logging.error(f"HTTP error on attempt {attempt + 1}: {str(e)}")
            if e.status_code == 429:  # Rate limiting
                time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                continue
            elif attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                raise
                
        except TimeoutError as e:
            logging.error(f"Timeout on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                continue
            else:
                raise
                
        except Exception as e:
            logging.error(f"Error on attempt {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                break
    
    # Fallback to read model for Office documents
    if extension in ['docx', 'xlsx', 'pptx']:
        try:
            logging.info(f"Attempting fallback with prebuilt-read model for {filename}")
            
            poller = client.begin_analyze_document(
                model_id="prebuilt-read",
                body=file_bytes,
                content_type="application/octet-stream",
                polling_interval=5
            )
            
            result = poller.result(timeout=300)
            
            pages = []
            if hasattr(result, 'pages') and result.pages:
                for i, page in enumerate(result.pages):
                    page_text = []
                    if hasattr(page, 'lines') and page.lines:
                        page_text = [line.content for line in page.lines if hasattr(line, 'content')]
                    elif hasattr(page, 'words') and page.words:
                        page_text = [word.content for word in page.words if hasattr(word, 'content')]
                    
                    if page_text:
                        pages.append({"page_number": i + 1, "text": " ".join(page_text)})
            
            if not pages and hasattr(result, 'content') and result.content:
                pages.append({"page_number": 1, "text": result.content})
            
            if pages:
                logging.info(f"Fallback successful: extracted {len(pages)} pages")
                return pages
                
        except Exception as fallback_error:
            logging.error(f"Fallback also failed for {filename}: {str(fallback_error)}")
    
    # If all attempts failed, raise an error
    raise Exception(f"Failed to extract text from {filename} after all attempts")


def get_optimal_model_for_filetype(extension: str) -> str:
    """
    Choose the best Document Intelligence model based on file type.
    Updated based on latest documentation.
    """
    # For Office documents, use prebuilt-read as it has better compatibility
    if extension in ['docx', 'xlsx', 'pptx']:
        return "prebuilt-read"
    
    # Layout model for PDFs (best structure preservation)
    elif extension in ['pdf']:
        return "prebuilt-layout"
    
    # Read model for images
    elif extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff']:
        return "prebuilt-read"
    
    # Default to read model
    else:
        return "prebuilt-read"


def extract_table_text(table):
    """
    Extract structured text from Document Intelligence table.
    """
    if not hasattr(table, 'cells') or not table.cells:
        return ""
    
    # Group cells by row and column
    rows = {}
    max_col = 0
    
    for cell in table.cells:
        if hasattr(cell, 'row_index') and hasattr(cell, 'column_index'):
            row_idx = cell.row_index
            col_idx = cell.column_index
            max_col = max(max_col, col_idx)
            
            if row_idx not in rows:
                rows[row_idx] = {}
            
            content = cell.content if hasattr(cell, 'content') else ""
            rows[row_idx][col_idx] = content or ""
    
    # Build table text with proper formatting
    table_lines = []
    for row_idx in sorted(rows.keys()):
        row = rows[row_idx]
        row_cells = [row.get(col_idx, "") for col_idx in range(max_col + 1)]
        row_text = " | ".join(row_cells)
        table_lines.append(row_text)
    
    return "\n".join(table_lines)

def handle_text(text, filename: str, doc_id: str):
    """
    Handle raw text input (unchanged).
    """
    chunks_and_embeddings = create_chunks_and_embeddings_from_text(text)
    save_to_search_index(doc_id, chunks_and_embeddings, filename)

def read_from_blob_storage(connection_string, container_name, key):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)

    downloader = blob_client.download_blob()
    file_bytes = downloader.readall()

    return file_bytes

def write_to_blob_storage(connection_string, container_name, key, blob, meta_data = None, overwrite=True):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    blob_client.upload_blob(blob, metadata=meta_data or {}, overwrite=overwrite)

def get_blob_metadata(connection_string, container_name, key):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    
    props = blob_client.get_blob_properties()
 
    return props.metadata

def set_blob_metadata(connection_string, container_name, key, new_metadata):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)

    blob_client.set_blob_metadata(metadata=new_metadata)

    return True

def delete_from_blob_storage(connection_string, container_name, key):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=key)
    blob_client.delete_blob()

def get_content_type(extension):
    if extension == "pdf":
        return "application/pdf"
    elif extension == "docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        logging.info(f"unknown extension of {extension=} can't find content type")

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
        logging.info("error")

    safe_filename = os.path.basename(uploaded_filename)
    extension = os.path.splitext(safe_filename)[1].lstrip(".")
    return safe_filename, extension, uploaded_file_content
