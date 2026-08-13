"""
GCS Document API

Provides endpoints to:
- Get signed URL for document viewing
- Download document content from GCS

Requires google-cloud-storage package and service account credentials.
"""

import frappe
from frappe import _
from frappe.utils.response import build_response
import json


def get_gcs_client():
    """Get Google Cloud Storage client."""
    try:
        from google.cloud import storage
        return storage.Client()
    except ImportError:
        frappe.throw(_("google-cloud-storage package not installed"))
    except Exception as e:
        frappe.throw(_(f"Failed to initialize GCS client: {str(e)}"))


def parse_gcs_path(gcs_path: str) -> tuple:
    """
    Parse GCS path to extract bucket and blob path.

    Args:
        gcs_path: GCS path like "gs://bucket-name/path/to/file.pdf"

    Returns:
        tuple: (bucket_name, blob_path)
    """
    if not gcs_path.startswith("gs://"):
        frappe.throw(_("Invalid GCS path. Must start with gs://"))

    path = gcs_path[5:]  # Remove "gs://"
    parts = path.split("/", 1)

    if len(parts) < 2:
        frappe.throw(_("Invalid GCS path format"))

    return parts[0], parts[1]


@frappe.whitelist()
def get_document_url(deal_id: str, document_idx: int = 0) -> dict:
    """
    Get a signed URL for viewing a document.

    Args:
        deal_id: CRM Deal ID
        document_idx: Index of document in the documents table (0-based)

    Returns:
        dict: {success: bool, url: str, message: str}
    """
    try:
        # Get document from deal
        deal = frappe.get_doc("CRM Deal", deal_id)

        if not deal.documents or document_idx >= len(deal.documents):
            return {
                "success": False,
                "url": None,
                "message": "Document not found"
            }

        doc = deal.documents[document_idx]

        if not doc.gcs_path:
            return {
                "success": False,
                "url": None,
                "message": "Document has no GCS path"
            }

        # Parse GCS path
        bucket_name, blob_path = parse_gcs_path(doc.gcs_path)

        # Get signed URL
        from datetime import timedelta
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)

        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
        )

        return {
            "success": True,
            "url": url,
            "display_name": doc.display_name,
            "mime_type": doc.mime_type,
            "message": "Success"
        }

    except Exception as e:
        frappe.log_error(f"GCS Document URL Error: {str(e)}")
        return {
            "success": False,
            "url": None,
            "message": str(e)
        }


@frappe.whitelist()
def get_document_content(deal_id: str, document_idx: int = 0):
    """
    Download document content from GCS and return as response.

    Args:
        deal_id: CRM Deal ID
        document_idx: Index of document in the documents table (0-based)

    Returns:
        File content with appropriate headers
    """
    try:
        # Get document from deal
        deal = frappe.get_doc("CRM Deal", deal_id)

        if not deal.documents or document_idx >= len(deal.documents):
            frappe.throw(_("Document not found"))

        doc = deal.documents[document_idx]

        if not doc.gcs_path:
            frappe.throw(_("Document has no GCS path"))

        # Parse GCS path
        bucket_name, blob_path = parse_gcs_path(doc.gcs_path)

        # Download content
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        content = blob.download_as_bytes()

        # Build response with appropriate content type
        frappe.local.response.filename = doc.display_name or blob_path.split("/")[-1]
        frappe.local.response.filecontent = content
        frappe.local.response.type = "download"

        if doc.mime_type:
            frappe.local.response.content_type = doc.mime_type

    except Exception as e:
        frappe.log_error(f"GCS Document Download Error: {str(e)}")
        frappe.throw(_(f"Failed to download document: {str(e)}"))


@frappe.whitelist()
def list_documents(deal_id: str) -> dict:
    """
    List all documents for a refund request.

    Args:
        deal_id: CRM Deal ID

    Returns:
        dict: {success: bool, documents: list, message: str}
    """
    try:
        deal = frappe.get_doc("CRM Deal", deal_id)

        documents = []
        for idx, doc in enumerate(deal.documents or []):
            documents.append({
                "idx": idx,
                "doc_type": doc.doc_type,
                "display_name": doc.display_name,
                "gcs_path": doc.gcs_path,
                "file_url": doc.file_url,
                "mime_type": doc.mime_type,
            })

        return {
            "success": True,
            "documents": documents,
            "message": "Success"
        }

    except Exception as e:
        frappe.log_error(f"GCS List Documents Error: {str(e)}")
        return {
            "success": False,
            "documents": [],
            "message": str(e)
        }
