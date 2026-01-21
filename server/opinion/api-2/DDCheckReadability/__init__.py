# DDCheckReadability/__init__.py
"""
Document Readability Check Endpoint

Validates that documents can be read/parsed before the main DD processing begins.
This is a lightweight check that verifies:
1. File exists in blob storage (or local storage in DEV_MODE)
2. File is not empty
3. File extension is supported
4. File can be opened (not corrupted or password-protected)
"""
import logging
import os
import json
import io
import azure.functions as func

import uuid

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence
from shared.uploader import read_from_blob_storage, write_to_blob_storage
from sqlalchemy.orm import joinedload

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "")

# Supported file types for DD processing
SUPPORTED_TYPES = {"pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "bmp", "tiff", "doc", "xls", "ppt"}


def convert_pptx_to_pdf(file_contents: bytes, filename: str) -> bytes:
    """
    Extract text from PPTX and create a readable PDF.
    Returns PDF bytes.
    """
    from pptx import Presentation

    pptx_stream = io.BytesIO(file_contents)
    prs = Presentation(pptx_stream)

    # Create PDF
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for slide_num, slide in enumerate(prs.slides, 1):
        # Add slide header
        story.append(Paragraph(f"<b>Slide {slide_num}</b>", styles['Heading2']))
        story.append(Spacer(1, 12))

        # Extract text from all shapes
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text.strip():
                # Escape special XML characters for reportlab
                text = shape.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                try:
                    story.append(Paragraph(text, styles['Normal']))
                    story.append(Spacer(1, 6))
                except Exception as e:
                    # If paragraph fails, try plain text without formatting
                    logging.warning(f"Failed to add formatted text, using plain: {e}")
                    story.append(Paragraph(text[:500], styles['Normal']))  # Truncate if needed

        story.append(Spacer(1, 20))

    doc.build(story)
    return pdf_buffer.getvalue()


def store_converted_pdf(original_doc_id: str, pdf_bytes: bytes, original_filename: str, folder_id: str, session) -> str:
    """
    Store converted PDF and create Document record.
    Returns the new document ID.
    """
    converted_doc_id = str(uuid.uuid4())
    pdf_filename = original_filename.rsplit('.', 1)[0] + '_converted.pdf'

    # Store PDF (local in DEV_MODE, blob storage otherwise)
    if DEV_MODE and LOCAL_STORAGE_PATH:
        local_path = os.path.join(LOCAL_STORAGE_PATH, "docs", converted_doc_id)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(pdf_bytes)
        logging.info(f"[DEV MODE] Stored converted PDF at: {local_path}")
    else:
        write_to_blob_storage(
            os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
            os.environ.get("DD_DOCS_STORAGE_CONTAINER_NAME", "dd-docs"),
            converted_doc_id,
            pdf_bytes,
            meta_data={
                "original_file_name": pdf_filename,
                "extension": "pdf",
                "converted_from": original_doc_id,
                "is_converted": "true"
            }
        )
        logging.info(f"Stored converted PDF in blob storage: {converted_doc_id}")

    # Create new Document record for the converted PDF
    new_doc = Document(
        id=uuid.UUID(converted_doc_id),
        folder_id=uuid.UUID(folder_id) if isinstance(folder_id, str) else folder_id,
        type="pdf",
        original_file_name=pdf_filename,
        processing_status="pending",
        is_original=False,
        size_in_bytes=len(pdf_bytes),
        readability_status="ready",  # Converted PDF is inherently readable
        converted_from_id=uuid.UUID(original_doc_id) if isinstance(original_doc_id, str) else original_doc_id
    )
    session.add(new_doc)
    session.flush()  # Ensure ID is available

    return converted_doc_id


def read_file_contents(doc_id: str) -> bytes:
    """
    Read file contents from storage with fallback.
    Tries primary storage first, then falls back to the other.
    This ensures files work regardless of where they were uploaded.
    """
    local_path = os.path.join(LOCAL_STORAGE_PATH, "docs", doc_id) if LOCAL_STORAGE_PATH else None
    local_path_alt = os.path.join(LOCAL_STORAGE_PATH, doc_id) if LOCAL_STORAGE_PATH else None

    def try_local_storage():
        """Attempt to read from local storage."""
        if not LOCAL_STORAGE_PATH:
            return None
        if local_path and os.path.exists(local_path):
            logging.info(f"[LOCAL] Reading document from: {local_path}")
            with open(local_path, "rb") as f:
                return f.read()
        if local_path_alt and os.path.exists(local_path_alt):
            logging.info(f"[LOCAL] Reading document from: {local_path_alt}")
            with open(local_path_alt, "rb") as f:
                return f.read()
        return None

    def try_blob_storage():
        """Attempt to read from Azure Blob Storage."""
        try:
            conn_string = os.environ.get("DD_DOCS_BLOB_STORAGE_CONNECTION_STRING")
            if not conn_string:
                logging.warning("[BLOB] No blob storage connection string configured")
                return None
            logging.info(f"[BLOB] Reading document from Azure Blob Storage: {doc_id}")
            return read_from_blob_storage(
                conn_string,
                os.environ.get("DD_DOCS_STORAGE_CONTAINER_NAME", "dd-docs"),
                doc_id
            )
        except Exception as e:
            logging.warning(f"[BLOB] Failed to read from blob storage: {e}")
            return None

    # Try primary storage first, then fallback
    if DEV_MODE:
        # DEV_MODE: Try local first, then blob
        content = try_local_storage()
        if content is not None:
            return content
        logging.info(f"[FALLBACK] File not in local storage, trying Azure Blob...")
        content = try_blob_storage()
        if content is not None:
            return content
        raise FileNotFoundError(f"File not found in local storage or blob storage: {doc_id}")
    else:
        # Production: Try blob first, then local
        content = try_blob_storage()
        if content is not None:
            return content
        logging.info(f"[FALLBACK] File not in blob storage, trying local...")
        content = try_local_storage()
        if content is not None:
            return content
        raise FileNotFoundError(f"File not found in blob storage or local storage: {doc_id}")


def check_pdf_readability(file_contents: bytes, filename: str) -> tuple[bool, str]:
    """Check if a PDF file is readable (not corrupted or password-protected)."""
    try:
        import fitz  # PyMuPDF

        pdf_stream = io.BytesIO(file_contents)
        doc = fitz.open(stream=pdf_stream, filetype="pdf")

        # Check if encrypted/password-protected
        if doc.is_encrypted:
            doc.close()
            return False, "Document is password-protected and cannot be accessed"

        # Try to read first page to verify it's not corrupted
        if doc.page_count == 0:
            doc.close()
            return False, "Document contains no pages"

        # Try to extract text from first page
        try:
            first_page = doc[0]
            _ = first_page.get_text()
        except Exception as e:
            doc.close()
            return False, f"Unable to read document content: {str(e)}"

        doc.close()
        return True, ""

    except Exception as e:
        return False, f"Unable to open document: {str(e)}"


def check_docx_readability(file_contents: bytes, filename: str) -> tuple[bool, str]:
    """Check if a DOCX file is readable."""
    try:
        from docx import Document as DocxDocument

        docx_stream = io.BytesIO(file_contents)
        doc = DocxDocument(docx_stream)

        # Try to read paragraphs
        paragraph_count = len(doc.paragraphs)
        if paragraph_count == 0 and len(doc.tables) == 0:
            # Check if document has any content at all
            text_content = ""
            for para in doc.paragraphs:
                text_content += para.text
            if not text_content.strip():
                return True, ""  # Empty but valid document

        return True, ""

    except Exception as e:
        error_str = str(e).lower()
        if "encrypted" in error_str or "password" in error_str:
            return False, "Document is password-protected and cannot be accessed"
        return False, f"Unable to open document: {str(e)}"


def check_xlsx_readability(file_contents: bytes, filename: str) -> tuple[bool, str]:
    """Check if an XLSX file is readable."""
    try:
        import openpyxl

        xlsx_stream = io.BytesIO(file_contents)
        workbook = openpyxl.load_workbook(xlsx_stream, read_only=True)

        # Check if there are any sheets
        if len(workbook.sheetnames) == 0:
            workbook.close()
            return False, "Spreadsheet contains no worksheets"

        workbook.close()
        return True, ""

    except Exception as e:
        error_str = str(e).lower()
        if "encrypted" in error_str or "password" in error_str:
            return False, "Spreadsheet is password-protected and cannot be accessed"
        return False, f"Unable to open spreadsheet: {str(e)}"


def check_pptx_readability(
    file_contents: bytes,
    filename: str,
    doc_id: str = None,
    folder_id: str = None,
    session = None
) -> tuple[bool, str, str | None]:
    """
    Check if a PPTX file is readable and convert to PDF.
    Returns (is_readable, error_message, converted_doc_id).
    """
    try:
        from pptx import Presentation

        pptx_stream = io.BytesIO(file_contents)
        prs = Presentation(pptx_stream)

        # Check if there are any slides
        if len(prs.slides) == 0:
            return False, "Presentation contains no slides", None

        # If we have session info, perform conversion
        converted_doc_id = None
        if doc_id and folder_id and session:
            try:
                logging.info(f"Converting PPTX to PDF: {filename}")
                pdf_bytes = convert_pptx_to_pdf(file_contents, filename)
                converted_doc_id = store_converted_pdf(
                    doc_id, pdf_bytes, filename, folder_id, session
                )
                logging.info(f"Successfully converted {filename} to PDF: {converted_doc_id}")
            except Exception as conv_error:
                logging.error(f"Failed to convert PPTX to PDF: {conv_error}")
                # Conversion failure is not a readability failure
                # The PPTX is still readable, just couldn't convert

        return True, "", converted_doc_id

    except Exception as e:
        error_str = str(e).lower()
        if "encrypted" in error_str or "password" in error_str:
            return False, "Presentation is password-protected and cannot be accessed", None
        return False, f"Unable to open presentation: {str(e)}", None


def check_image_readability(file_contents: bytes, filename: str) -> tuple[bool, str]:
    """Check if an image file is readable."""
    try:
        from PIL import Image

        img_stream = io.BytesIO(file_contents)
        img = Image.open(img_stream)
        img.verify()  # Verify it's a valid image

        return True, ""

    except Exception as e:
        return False, f"Unable to open image: {str(e)}"


def check_document_readability(
    doc_id: str,
    file_type: str,
    filename: str,
    folder_id: str = None,
    session = None
) -> tuple[bool, str, str | None]:
    """
    Check if a document can be read.
    Returns (is_readable, error_message, converted_doc_id).
    converted_doc_id is set only for PPTX files that were converted to PDF.
    """
    try:
        # Read file from storage (local in DEV_MODE, blob storage otherwise)
        file_contents = read_file_contents(doc_id)

        if not file_contents:
            return False, "Document file is empty or could not be retrieved", None

        if len(file_contents) < 100:  # Suspiciously small file
            return False, "Document file appears to be corrupted (file too small)", None

        file_type_lower = file_type.lower()

        # Check if supported
        if file_type_lower not in SUPPORTED_TYPES:
            return False, f"Document type '{file_type}' is not supported for analysis", None

        # Type-specific checks
        if file_type_lower == "pdf":
            is_readable, error = check_pdf_readability(file_contents, filename)
            return is_readable, error, None
        elif file_type_lower in ("docx", "doc"):
            if file_type_lower == "doc":
                # .doc files need conversion, treat as potentially readable
                return True, "", None
            is_readable, error = check_docx_readability(file_contents, filename)
            return is_readable, error, None
        elif file_type_lower in ("xlsx", "xls"):
            if file_type_lower == "xls":
                return True, "", None  # Legacy format, assume readable
            is_readable, error = check_xlsx_readability(file_contents, filename)
            return is_readable, error, None
        elif file_type_lower in ("pptx", "ppt"):
            if file_type_lower == "ppt":
                return True, "", None  # Legacy format, assume readable
            # PPTX files get converted to PDF
            return check_pptx_readability(
                file_contents, filename, doc_id, folder_id, session
            )
        elif file_type_lower in ("jpg", "jpeg", "png", "bmp", "tiff"):
            is_readable, error = check_image_readability(file_contents, filename)
            return is_readable, error, None
        else:
            # Unknown but potentially supported type
            return True, "", None

    except Exception as e:
        logging.error(f"Error checking readability for {doc_id}: {str(e)}")
        return False, f"Error checking document: {str(e)}", None


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Check readability of documents in a DD project.

    POST /api/dd-check-readability
    Body: {
        "dd_id": "uuid",
        "doc_ids": ["uuid1", "uuid2"]  // Optional - if not provided, checks all docs
    }

    Returns: {
        "dd_id": "uuid",
        "total_documents": 10,
        "results": [
            {
                "doc_id": "uuid",
                "filename": "example.pdf",
                "status": "ready|failed|checking",
                "error": "Error message if failed"
            }
        ],
        "summary": {
            "ready": 8,
            "failed": 2,
            "checking": 0
        }
    }
    """

    # Auth check
    if not DEV_MODE and req.headers.get('function-key') != os.environ.get("FUNCTION_KEY"):
        logging.info("No matching value in header")
        return func.HttpResponse("", status_code=401)

    try:
        email, err = auth_get_email(req)
        if err:
            return err

        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON body"}),
                status_code=400,
                mimetype="application/json"
            )

        dd_id = req_body.get("dd_id")
        doc_ids = req_body.get("doc_ids")  # Optional list of specific doc IDs

        if not dd_id:
            return func.HttpResponse(
                json.dumps({"error": "dd_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        results = []
        summary = {"ready": 0, "failed": 0, "checking": 0}

        with transactional_session() as session:
            # Verify DD exists
            dd = session.query(DueDiligence).filter(DueDiligence.id == dd_id).first()
            if not dd:
                return func.HttpResponse(
                    json.dumps({"error": f"Due diligence {dd_id} not found"}),
                    status_code=404,
                    mimetype="application/json"
                )

            # Get documents to check
            # Explicitly specify the join condition since Document has multiple FKs to Folder
            docs_query = (
                session.query(Document)
                .join(Folder, Document.folder_id == Folder.id)
                .filter(
                    Folder.dd_id == dd_id,
                    Document.is_original == False
                )
            )

            if doc_ids:
                docs_query = docs_query.filter(Document.id.in_(doc_ids))

            documents = docs_query.all()

            for doc in documents:
                # Update status to checking
                doc.readability_status = "checking"
                doc.conversion_status = "pending" if doc.type.lower() == "pptx" else None
                session.commit()

                # Check readability (and convert PPTX to PDF if applicable)
                is_readable, error_msg, converted_doc_id = check_document_readability(
                    str(doc.id),
                    doc.type,
                    doc.original_file_name,
                    str(doc.folder_id),
                    session
                )

                # Update document status
                if is_readable:
                    doc.readability_status = "ready"
                    doc.readability_error = None
                    summary["ready"] += 1

                    # Handle PPTX conversion result
                    if converted_doc_id:
                        doc.converted_doc_id = uuid.UUID(converted_doc_id)
                        doc.conversion_status = "converted"
                    elif doc.type.lower() == "pptx":
                        # PPTX was readable but conversion failed
                        doc.conversion_status = "failed"
                else:
                    doc.readability_status = "failed"
                    doc.readability_error = error_msg
                    summary["failed"] += 1
                    if doc.type.lower() == "pptx":
                        doc.conversion_status = "failed"

                session.commit()

                results.append({
                    "doc_id": str(doc.id),
                    "filename": doc.original_file_name,
                    "file_type": doc.type,
                    "status": doc.readability_status,
                    "error": doc.readability_error,
                    "converted_doc_id": str(doc.converted_doc_id) if doc.converted_doc_id else None,
                    "conversion_status": doc.conversion_status
                })

                logging.info(f"Readability check for {doc.original_file_name}: {doc.readability_status}")

            response = {
                "dd_id": str(dd_id),
                "total_documents": len(documents),
                "results": results,
                "summary": summary
            }

            return func.HttpResponse(
                json.dumps(response),
                status_code=200,
                mimetype="application/json"
            )

    except Exception as e:
        logging.error(f"Error in readability check: {str(e)}")
        logging.exception("Full traceback:")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
