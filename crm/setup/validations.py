"""
Custom validations for Seito Refund CRM.
"""

import frappe
from frappe import _


def validate_refund_request(doc, method):
    """
    Validation hook for CRM Deal (Refund Request).

    - Prevents status change once Approved or Rejected (final states)
    - Only Seito Admin can reopen closed requests
    - For Approved: requires lost_reason (refund reason) and resolution_notes
    - For Rejected: requires resolution_notes only
    """
    if doc.is_new():
        return

    # Validate fields for final statuses
    if doc.status:
        status_type = frappe.db.get_value("CRM Deal Status", doc.status, "type")

        if status_type == "Won":  # Approved - losing the student
            if not doc.get("resolution_notes"):
                frappe.throw(
                    _("Approval Notes are required when approving a refund"),
                    frappe.MandatoryError
                )
            if not doc.get("lost_reason"):
                frappe.throw(
                    _("Refund Reason is required when approving a refund"),
                    frappe.MandatoryError
                )
        elif status_type == "Lost":  # Rejected
            if not doc.get("resolution_notes"):
                frappe.throw(
                    _("Rejection Notes are required when rejecting a refund"),
                    frappe.MandatoryError
                )

    # Get the old document to compare
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return

    old_status = old_doc.get("status")
    new_status = doc.status

    if old_status == new_status:
        return

    # Check if old status is a final state (Won=Approved, Lost=Rejected)
    if old_status:
        old_status_type = frappe.db.get_value("CRM Deal Status", old_status, "type")

        if old_status_type in ["Won", "Lost"]:
            # Only allow Seito Admin to change status from final states
            user_roles = frappe.get_roles(frappe.session.user)

            if "Seito Admin" not in user_roles and "Administrator" not in user_roles:
                frappe.throw(
                    _("Cannot change status from '{0}'. Only Seito Admin can reopen closed requests.").format(old_status),
                    frappe.PermissionError
                )
            else:
                # Log the reopening
                frappe.msgprint(
                    _("Refund request reopened by {0}. Previous status: {1}").format(
                        frappe.session.user, old_status
                    ),
                    alert=True
                )


def validate_student(doc, method):
    """
    Validation hook for CRM Organization (Student).

    - Auto-generates organization_name from first_name + last_name
    """
    if doc.first_name:
        full_name = doc.first_name
        if doc.last_name:
            full_name += " " + doc.last_name
        doc.organization_name = full_name
