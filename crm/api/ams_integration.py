"""
AMS to CRM Integration API

Provides endpoints for AMS to:
- Create students (CRM Organization)
- Create refund requests (CRM Deal)
- Get refund request status
- Update refund request

Authentication: Use API key or OAuth token
"""

import frappe
from frappe import _


@frappe.whitelist(methods=["POST"])
def create_student(
    application_id: str,
    first_name: str,
    last_name: str = None,
    email: str = None,
    phone: str = None,
    program: str = None,
    elective: str = None,
    batch: str = None,
    university: str = None,
    partner: str = None,
    counsellor: str = None,
) -> dict:
    """
    Create a new student in CRM.

    Args:
        application_id: Unique application ID from AMS (required)
        first_name: Student's first name (required)
        last_name: Student's last name
        email: Student's email
        phone: Student's phone number
        program: Program name
        elective: Elective name
        batch: Batch identifier
        university: University name
        partner: Partner name
        counsellor: Assigned counsellor's email (User)

    Returns:
        dict: {success: bool, student_id: str, message: str}
    """
    try:
        # Check if student already exists - return success with existing student
        existing = frappe.db.exists("CRM Organization", {"application_id": application_id})
        if existing:
            return {
                "success": True,
                "student_id": existing,
                "already_exists": True,
                "message": "Student already exists"
            }

        # Create student
        student = frappe.new_doc("CRM Organization")
        student.application_id = application_id
        student.first_name = first_name
        student.last_name = last_name
        student.student_email = email
        student.student_phone = phone
        student.program = program
        student.elective = elective
        student.batch = batch
        student.university = university
        student.partner = partner
        if counsellor:
            student.counsellor = counsellor
        # organization_name is auto-generated from first_name + last_name in validate hook

        student.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "student_id": student.name,
            "message": "Student created successfully"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"AMS Integration - Create Student Error: {str(e)}")
        return {
            "success": False,
            "student_id": None,
            "message": str(e)
        }


@frappe.whitelist(methods=["POST"])
def create_refund_request(
    student_application_id: str,
    refund_request_id: str = None,
    ticket_id: str = None,
    refundable_amount: float = 0,
    refund_reason: str = None,
    currency: str = "INR",
    counsellor_email: str = None,
    documents: list = None,
) -> dict:
    """
    Create a new refund request in CRM.

    Args:
        student_application_id: Application ID of the student (required)
        refund_request_id: Unique refund request ID from AMS
        ticket_id: Support ticket ID
        refundable_amount: Amount to be refunded
        refund_reason: Reason for refund
        currency: Currency code (default: INR)
        counsellor_email: Email of assigned counsellor
        documents: List of document objects with doc_type, display_name, gcs_path, file_url, mime_type

    Returns:
        dict: {success: bool, deal_id: str, message: str}
    """
    try:
        # Find student by application_id (including counsellor for auto-assignment)
        student = frappe.db.get_value(
            "CRM Organization",
            {"application_id": student_application_id},
            ["name", "organization_name", "counsellor"],
            as_dict=True
        )

        if not student:
            return {
                "success": False,
                "deal_id": None,
                "message": f"Student with application_id '{student_application_id}' not found"
            }

        # Check if refund request already exists (if refund_request_id provided)
        if refund_request_id:
            existing = frappe.db.exists("CRM Deal", {"refund_request_id": refund_request_id})
            if existing:
                return {
                    "success": False,
                    "deal_id": existing,
                    "message": f"Refund request '{refund_request_id}' already exists"
                }

        # Get default status
        default_status = "Pending Consultation"
        if not frappe.db.exists("CRM Deal Status", default_status):
            default_status = frappe.db.get_value(
                "CRM Deal Status",
                {"type": "Open"},
                "name"
            )

        # Determine deal owner (counsellor)
        # Priority: 1) API parameter, 2) Student's assigned counsellor
        deal_owner = None
        if counsellor_email:
            deal_owner = frappe.db.get_value("User", {"email": counsellor_email}, "name")
        elif student.counsellor:
            # Auto-assign from student's counsellor
            deal_owner = student.counsellor

        # Create refund request
        deal = frappe.new_doc("CRM Deal")
        deal.organization = student.name
        deal.refund_request_id = refund_request_id
        deal.ticket_id = ticket_id
        deal.student_application_id = student_application_id
        deal.refundable_amount = refundable_amount
        deal.refund_reason = refund_reason
        deal.currency = currency
        deal.status = default_status
        if deal_owner:
            deal.deal_owner = deal_owner

        # Add documents if provided
        if documents:
            for doc in documents:
                deal.append("documents", {
                    "doc_type": doc.get("doc_type"),
                    "display_name": doc.get("display_name"),
                    "gcs_path": doc.get("gcs_path"),
                    "file_url": doc.get("file_url"),
                    "mime_type": doc.get("mime_type"),
                })

        deal.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "deal_id": deal.name,
            "counsellor": deal_owner,
            "message": "Refund request created successfully"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"AMS Integration - Create Refund Request Error: {str(e)}")
        return {
            "success": False,
            "deal_id": None,
            "message": str(e)
        }


@frappe.whitelist(methods=["GET"])
def get_refund_status(
    refund_request_id: str = None,
    deal_id: str = None,
) -> dict:
    """
    Get the current status of a refund request.

    Args:
        refund_request_id: Refund request ID from AMS
        deal_id: CRM Deal ID

    Returns:
        dict: {success: bool, data: {...}, message: str}
    """
    try:
        if not refund_request_id and not deal_id:
            return {
                "success": False,
                "data": None,
                "message": "Either refund_request_id or deal_id is required"
            }

        filters = {}
        if refund_request_id:
            filters["refund_request_id"] = refund_request_id
        if deal_id:
            filters["name"] = deal_id

        deal = frappe.db.get_value(
            "CRM Deal",
            filters,
            [
                "name", "refund_request_id", "ticket_id", "student_application_id",
                "organization", "status", "refundable_amount", "currency",
                "deal_owner", "resolution_notes", "lost_reason", "lost_notes",
                "creation", "modified"
            ],
            as_dict=True
        )

        if not deal:
            return {
                "success": False,
                "data": None,
                "message": "Refund request not found"
            }

        # Get status type
        status_type = frappe.db.get_value("CRM Deal Status", deal.status, "type")

        # Map status type to readable format
        status_mapping = {
            "Won": "approved",
            "Lost": "rejected",
            "Open": "pending",
            "Ongoing": "in_progress",
            "On Hold": "on_hold"
        }

        return {
            "success": True,
            "data": {
                "deal_id": deal.name,
                "refund_request_id": deal.refund_request_id,
                "ticket_id": deal.ticket_id,
                "student_application_id": deal.student_application_id,
                "student_name": deal.organization,
                "status": deal.status,
                "status_type": status_mapping.get(status_type, status_type),
                "refundable_amount": deal.refundable_amount,
                "currency": deal.currency,
                "counsellor": deal.deal_owner,
                "resolution_notes": deal.resolution_notes,
                "refund_reason": deal.lost_reason,  # lost_reason is used for refund reason in Approved
                "created_at": str(deal.creation),
                "updated_at": str(deal.modified)
            },
            "message": "Success"
        }

    except Exception as e:
        frappe.log_error(f"AMS Integration - Get Refund Status Error: {str(e)}")
        return {
            "success": False,
            "data": None,
            "message": str(e)
        }


@frappe.whitelist(methods=["GET"])
def get_student(application_id: str) -> dict:
    """
    Get student details by application ID.

    Args:
        application_id: Student's application ID

    Returns:
        dict: {success: bool, data: {...}, message: str}
    """
    try:
        student = frappe.db.get_value(
            "CRM Organization",
            {"application_id": application_id},
            [
                "name", "organization_name", "application_id",
                "first_name", "last_name", "student_email", "student_phone",
                "program", "elective", "batch", "university", "partner",
                "counsellor", "creation", "modified"
            ],
            as_dict=True
        )

        if not student:
            return {
                "success": False,
                "data": None,
                "message": f"Student with application_id '{application_id}' not found"
            }

        return {
            "success": True,
            "data": {
                "student_id": student.name,
                "student_name": student.organization_name,
                "application_id": student.application_id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.student_email,
                "phone": student.student_phone,
                "program": student.program,
                "elective": student.elective,
                "batch": student.batch,
                "university": student.university,
                "partner": student.partner,
                "counsellor": student.counsellor,
                "created_at": str(student.creation),
                "updated_at": str(student.modified)
            },
            "message": "Success"
        }

    except Exception as e:
        frappe.log_error(f"AMS Integration - Get Student Error: {str(e)}")
        return {
            "success": False,
            "data": None,
            "message": str(e)
        }


@frappe.whitelist(methods=["PUT", "PATCH"])
def update_student(
    application_id: str,
    first_name: str = None,
    last_name: str = None,
    email: str = None,
    phone: str = None,
    program: str = None,
    elective: str = None,
    batch: str = None,
    university: str = None,
    partner: str = None,
    counsellor: str = None,
) -> dict:
    """
    Update an existing student in CRM.

    Args:
        application_id: Student's application ID (required, used to find student)
        Other fields: Fields to update (only provided fields are updated)
        counsellor: Assigned counsellor's email (User)

    Returns:
        dict: {success: bool, student_id: str, message: str}
    """
    try:
        student_name = frappe.db.get_value(
            "CRM Organization",
            {"application_id": application_id},
            "name"
        )

        if not student_name:
            return {
                "success": False,
                "student_id": None,
                "message": f"Student with application_id '{application_id}' not found"
            }

        student = frappe.get_doc("CRM Organization", student_name)

        # Update only provided fields
        if first_name is not None:
            student.first_name = first_name
        if last_name is not None:
            student.last_name = last_name
        if email is not None:
            student.student_email = email
        if phone is not None:
            student.student_phone = phone
        if program is not None:
            student.program = program
        if elective is not None:
            student.elective = elective
        if batch is not None:
            student.batch = batch
        if university is not None:
            student.university = university
        if partner is not None:
            student.partner = partner
        if counsellor is not None:
            student.counsellor = counsellor

        student.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "student_id": student.name,
            "message": "Student updated successfully"
        }

    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"AMS Integration - Update Student Error: {str(e)}")
        return {
            "success": False,
            "student_id": None,
            "message": str(e)
        }
