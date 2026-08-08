"""
CRM to AMS Webhook

Sends notifications to AMS when:
- Refund request status changes
- Refund request is approved/rejected (final states)

Configuration in site_config.json:
{
    "ams_webhook_url": "https://ams.seito.co.in/api/webhook/crm",
    "ams_api_key": "your-secret-key",
    "ams_webhook_enabled": true
}
"""

import frappe
from frappe import _
import requests
import json


def notify_ams_on_status_change(doc, method):
    """
    Called when CRM Deal is updated - notify AMS if status changed.

    Registered in hooks.py under doc_events for CRM Deal.
    """
    # Check if webhook is enabled
    if not frappe.conf.get("ams_webhook_enabled", True):
        return

    # Only proceed if status changed
    if not doc.has_value_changed("status"):
        return

    # Get webhook URL
    webhook_url = frappe.conf.get("ams_webhook_url")
    if not webhook_url:
        frappe.logger().warning("AMS webhook URL not configured")
        return

    # Get status type
    status_type = frappe.db.get_value("CRM Deal Status", doc.status, "type")

    # Map status type
    status_mapping = {
        "Won": "approved",
        "Lost": "rejected",
        "Open": "pending",
        "Ongoing": "in_progress",
        "On Hold": "on_hold"
    }

    # Build payload
    payload = {
        "event": "refund_status_changed",
        "timestamp": frappe.utils.now(),
        "data": {
            "deal_id": doc.name,
            "refund_request_id": doc.refund_request_id,
            "ticket_id": doc.ticket_id,
            "student_application_id": doc.student_application_id,
            "student_name": doc.organization,
            "status": doc.status,
            "status_type": status_mapping.get(status_type, status_type),
            "is_final": status_type in ["Won", "Lost"],
            "refundable_amount": doc.refundable_amount,
            "currency": doc.currency,
            "counsellor": doc.deal_owner,
            "resolution_notes": doc.resolution_notes,
            "refund_reason": doc.lost_reason if status_type == "Won" else None,
            "rejection_notes": doc.resolution_notes if status_type == "Lost" else None,
            "updated_by": frappe.session.user,
            "updated_at": str(doc.modified)
        }
    }

    # Send async to not block the save
    frappe.enqueue(
        "crm.api.ams_webhook.send_webhook",
        queue="short",
        webhook_url=webhook_url,
        payload=payload,
        doc_name=doc.name
    )


def send_webhook(webhook_url: str, payload: dict, doc_name: str):
    """
    Send webhook to AMS (runs in background queue).

    Args:
        webhook_url: AMS webhook endpoint
        payload: Data to send
        doc_name: Deal name for logging
    """
    api_key = frappe.conf.get("ams_api_key", "")

    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Source": "seito-crm",
        "X-Webhook-Event": payload.get("event", "unknown"),
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        # Log success
        log_webhook(
            doc_name=doc_name,
            webhook_url=webhook_url,
            payload=payload,
            response_status=response.status_code,
            response_body=response.text[:500],
            success=True
        )

        frappe.logger().info(
            f"AMS webhook sent successfully for {doc_name}: {response.status_code}"
        )

    except requests.exceptions.Timeout:
        log_webhook(
            doc_name=doc_name,
            webhook_url=webhook_url,
            payload=payload,
            response_status=0,
            response_body="Request timed out",
            success=False
        )
        frappe.logger().error(f"AMS webhook timeout for {doc_name}")

    except requests.exceptions.RequestException as e:
        response_status = e.response.status_code if e.response else 0
        response_body = e.response.text[:500] if e.response else str(e)

        log_webhook(
            doc_name=doc_name,
            webhook_url=webhook_url,
            payload=payload,
            response_status=response_status,
            response_body=response_body,
            success=False
        )
        frappe.logger().error(f"AMS webhook failed for {doc_name}: {e}")

    except Exception as e:
        log_webhook(
            doc_name=doc_name,
            webhook_url=webhook_url,
            payload=payload,
            response_status=0,
            response_body=str(e),
            success=False
        )
        frappe.logger().error(f"AMS webhook error for {doc_name}: {e}")


def log_webhook(
    doc_name: str,
    webhook_url: str,
    payload: dict,
    response_status: int,
    response_body: str,
    success: bool
):
    """
    Log webhook attempt for debugging and retry purposes.
    """
    try:
        frappe.get_doc({
            "doctype": "CRM Webhook Log",
            "reference_doctype": "CRM Deal",
            "reference_name": doc_name,
            "webhook_url": webhook_url,
            "request_payload": json.dumps(payload, indent=2),
            "response_status": response_status,
            "response_body": response_body,
            "success": success,
            "timestamp": frappe.utils.now()
        }).insert(ignore_permissions=True)
        frappe.db.commit()
    except Exception as e:
        # If log doctype doesn't exist, just log to error log
        frappe.logger().warning(f"Could not log webhook: {e}")


@frappe.whitelist(methods=["POST"])
def retry_webhook(doc_name: str) -> dict:
    """
    Manually retry sending webhook for a specific deal.

    Args:
        doc_name: CRM Deal name

    Returns:
        dict: {success: bool, message: str}
    """
    try:
        webhook_url = frappe.conf.get("ams_webhook_url")
        if not webhook_url:
            return {
                "success": False,
                "message": "AMS webhook URL not configured"
            }

        doc = frappe.get_doc("CRM Deal", doc_name)
        status_type = frappe.db.get_value("CRM Deal Status", doc.status, "type")

        status_mapping = {
            "Won": "approved",
            "Lost": "rejected",
            "Open": "pending",
            "Ongoing": "in_progress",
            "On Hold": "on_hold"
        }

        payload = {
            "event": "refund_status_changed",
            "timestamp": frappe.utils.now(),
            "retry": True,
            "data": {
                "deal_id": doc.name,
                "refund_request_id": doc.refund_request_id,
                "ticket_id": doc.ticket_id,
                "student_application_id": doc.student_application_id,
                "student_name": doc.organization,
                "status": doc.status,
                "status_type": status_mapping.get(status_type, status_type),
                "is_final": status_type in ["Won", "Lost"],
                "refundable_amount": doc.refundable_amount,
                "currency": doc.currency,
                "counsellor": doc.deal_owner,
                "resolution_notes": doc.resolution_notes,
                "refund_reason": doc.lost_reason if status_type == "Won" else None,
                "updated_by": frappe.session.user,
                "updated_at": str(doc.modified)
            }
        }

        # Send synchronously for retry
        send_webhook(webhook_url, payload, doc_name)

        return {
            "success": True,
            "message": "Webhook retry initiated"
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }
