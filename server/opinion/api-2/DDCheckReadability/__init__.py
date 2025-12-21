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

from shared.utils import auth_get_email
from shared.session import transactional_session
from shared.models import Document, Folder, DueDiligence
from shared.uploader import read_from_blob_storage
from sqlalchemy.orm import joinedload

DEV_MODE = os.environ.get("DEV_MODE", "").lower() == "true"
LOCAL_STORAGE_PATH = os.environ.get("LOCAL_STORAGE_PATH", "")

# Supported file types for DD processing
SUPPORTED_TYPES = {"pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "bmp", "tiff", "doc", "xls", "ppt"}


def read_file_contents(doc_id: str) -> bytes:
    """
    Read file contents from storage.
    Uses local storage in DEV_MODE, Azure Blob Storage otherwise.
    """
    if DEV_MODE and LOCAL_STORAGE_PATH:
        # Documents are stored in .local_storage/docs/{doc_id}
        local_path = os.path.join(LOCAL_STORAGE_PATH, "docs", doc_id)
        logging.info(f"[DEV MODE] Looking for document at: {local_path}")
        if os.path.exists(local_path):
            with open(local_path, "rb") as f:
                return f.read()
        # Also check without subfolder (legacy)
        local_path_alt = os.path.join(LOCAL_STORAGE_PATH, doc_id)
        if os.path.exists(local_path_alt):
            with open(local_path_alt, "rb") as f:
                return f.read()
        raise FileNotFoundError(f"File not found in local storage: {doc_id} (checked {local_path})")
    else:
        # Read from Azure Blob Storage
        return read_from_blob_storage(
            os.environ["DD_DOCS_BLOB_STORAGE_CONNECTION_STRING"],
            os.environ.get("DD_DOCS_STORAGE_CONTAINER_NAME", "dd-docs"),
            doc_id
        )


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


def check_pptx_readability(file_contents: bytes, filename: str) -> tuple[bool, str]:
    """Check if a PPTX file is readable."""
    try:
        from pptx import Presentation

        pptx_stream = io.BytesIO(file_contents)
        prs = Presentation(pptx_stream)

        # Check if there are any slides
        if len(prs.slides) == 0:
            return False, "Presentation contains no slides"

        return True, ""

    except Exception as e:
        error_str = str(e).lower()
        if "encrypted" in error_str or "password" in error_str:
            return False, "Presentation is password-protected and cannot be accessed"
        return False, f"Unable to open presentation: {str(e)}"


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


def check_document_readability(doc_id: str, file_type: str, filename: str) -> tuple[bool, str]:
    """
    Check if a document can be read.
    Returns (is_readable, error_message).
    """
    try:
        # Read file from storage (local in DEV_MODE, blob storage otherwise)
        file_contents = read_file_contents(doc_id)

        if not file_contents:
            return False, "Document file is empty or could not be retrieved"

        if len(file_contents) < 100:  # Suspiciously small file
            return False, "Document file appears to be corrupted (file too small)"

        file_type_lower = file_type.lower()

        # Check if supported
        if file_type_lower not in SUPPORTED_TYPES:
            return False, f"Document type '{file_type}' is not supported for analysis"

        # Type-specific checks
        if file_type_lower == "pdf":
            return check_pdf_readability(file_contents, filename)
        elif file_type_lower in ("docx", "doc"):
            if file_type_lower == "doc":
                # .doc files need conversion, treat as potentially readable
                return True, ""
            return check_docx_readability(file_contents, filename)
        elif file_type_lower in ("xlsx", "xls"):
            if file_type_lower == "xls":
                return True, ""  # Legacy format, assume readable
            return check_xlsx_readability(file_contents, filename)
        elif file_type_lower in ("pptx", "ppt"):
            if file_type_lower == "ppt":
                return True, ""  # Legacy format, assume readable
            return check_pptx_readability(file_contents, filename)
        elif file_type_lower in ("jpg", "jpeg", "png", "bmp", "tiff"):
            return check_image_readability(file_contents, filename)
        else:
            # Unknown but potentially supported type
            return True, ""

    except Exception as e:
        logging.error(f"Error checking readability for {doc_id}: {str(e)}")
        return False, f"Error checking document: {str(e)}"


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
                session.commit()

                # Check readability
                is_readable, error_msg = check_document_readability(
                    str(doc.id),
                    doc.type,
                    doc.original_file_name
                )

                # Update document status
                if is_readable:
                    doc.readability_status = "ready"
                    doc.readability_error = None
                    summary["ready"] += 1
                else:
                    doc.readability_status = "failed"
                    doc.readability_error = error_msg
                    summary["failed"] += 1

                session.commit()

                results.append({
                    "doc_id": str(doc.id),
                    "filename": doc.original_file_name,
                    "file_type": doc.type,
                    "status": doc.readability_status,
                    "error": doc.readability_error
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
