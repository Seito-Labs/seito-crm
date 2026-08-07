"""
Setup script for customizing Frappe CRM for Seito Refund Request workflow.
Run with: bench --site <site> execute crm.setup.setup_crm.execute
This script is idempotent - safe to run multiple times.
"""

import frappe


def execute():
    """Main entry point for CRM customization."""
    print("Starting CRM customization for Seito...")

    # Setup roles and permissions
    setup_roles()
    setup_permissions()

    # Add custom fields to CRM Organization (Student)
    add_student_custom_fields()

    # Add custom fields to CRM Deal (Refund Request)
    add_refund_request_custom_fields()

    # Setup refund request statuses
    setup_refund_request_statuses()

    # Update CRM Fields Layout to show custom fields in UI
    update_crm_field_layouts()

    frappe.db.commit()
    print("\nCRM customization completed successfully!")


def setup_roles():
    """Create Seito roles for CRM access."""
    print("\n=== Setting up Seito roles ===")

    roles = [
        {"role_name": "Seito Agent", "desk_access": 1},
        {"role_name": "Seito Team Lead", "desk_access": 1},
        {"role_name": "Seito Manager", "desk_access": 1},
        {"role_name": "Seito Admin", "desk_access": 1},
    ]

    for role_data in roles:
        role_name = role_data["role_name"]
        if not frappe.db.exists("Role", role_name):
            role = frappe.new_doc("Role")
            role.role_name = role_name
            role.desk_access = role_data["desk_access"]
            role.insert(ignore_permissions=True)
            print(f"  Created role: {role_name}")
        else:
            print(f"  Role already exists: {role_name}")


def setup_permissions():
    """Setup permissions for Seito roles on CRM DocTypes."""
    print("\n=== Setting up role permissions ===")

    doctypes = [
        "CRM Deal",
        "CRM Organization",
        "CRM Deal Status",
        "FCRM Note",
        "CRM Task",
        "Comment",
        "CRM Notification",
    ]

    permissions_map = {
        "Seito Agent": {
            "read": 1, "write": 1, "create": 1, "delete": 0,
            "report": 1, "export": 1, "import": 0, "share": 1,
            "print": 1, "email": 1
        },
        "Seito Team Lead": {
            "read": 1, "write": 1, "create": 1, "delete": 0,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1
        },
        "Seito Manager": {
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1
        },
        "Seito Admin": {
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1
        },
    }

    for doctype in doctypes:
        if not frappe.db.exists("DocType", doctype):
            print(f"  Skipping {doctype} - does not exist")
            continue

        for role, perms in permissions_map.items():
            existing = frappe.db.exists("Custom DocPerm", {
                "parent": doctype,
                "role": role
            })

            if not existing:
                perm = frappe.new_doc("Custom DocPerm")
                perm.parent = doctype
                perm.parenttype = "DocType"
                perm.parentfield = "permissions"
                perm.role = role
                perm.permlevel = 0

                for key, val in perms.items():
                    setattr(perm, key, val)

                perm.insert(ignore_permissions=True)
                print(f"  Added {role} permission for {doctype}")
            else:
                print(f"  Permission exists: {role} on {doctype}")


def add_student_custom_fields():
    """Add custom fields to CRM Organization for student information."""
    print("\n=== Adding Student custom fields to CRM Organization ===")

    custom_fields = [
        # Application ID with user-provided prefix (e.g., APP-UUID)
        {
            "dt": "CRM Organization",
            "fieldname": "application_id",
            "label": "Application ID",
            "fieldtype": "Data",
            "insert_after": "organization_name",
            "unique": 1,
            "bold": 1,
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "first_name",
            "label": "First Name",
            "fieldtype": "Data",
            "insert_after": "application_id",
            "reqd": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "last_name",
            "label": "Last Name",
            "fieldtype": "Data",
            "insert_after": "first_name",
        },
        {
            "dt": "CRM Organization",
            "fieldname": "student_email",
            "label": "Email",
            "fieldtype": "Data",
            "options": "Email",
            "insert_after": "last_name",
            "in_list_view": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "student_phone",
            "label": "Phone",
            "fieldtype": "Data",
            "options": "Phone",
            "insert_after": "student_email",
        },
        {
            "dt": "CRM Organization",
            "fieldname": "program",
            "label": "Program",
            "fieldtype": "Data",
            "insert_after": "student_phone",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "elective",
            "label": "Elective",
            "fieldtype": "Data",
            "insert_after": "program",
        },
        {
            "dt": "CRM Organization",
            "fieldname": "batch",
            "label": "Batch",
            "fieldtype": "Data",
            "insert_after": "elective",
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "university",
            "label": "University",
            "fieldtype": "Data",
            "insert_after": "batch",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "partner",
            "label": "Partner",
            "fieldtype": "Data",
            "insert_after": "university",
            "in_standard_filter": 1,
        },
    ]

    _create_custom_fields(custom_fields)


def add_refund_request_custom_fields():
    """Add custom fields to CRM Deal for refund request information."""
    print("\n=== Adding Refund Request custom fields to CRM Deal ===")

    custom_fields = [
        {
            "dt": "CRM Deal",
            "fieldname": "refund_request_id",
            "label": "Refund Request ID",
            "fieldtype": "Data",
            "insert_after": "naming_series",
            "unique": 1,
            "bold": 1,
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "ticket_id",
            "label": "Ticket ID",
            "fieldtype": "Data",
            "insert_after": "refund_request_id",
            "in_list_view": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "student_application_id",
            "label": "Student Application ID",
            "fieldtype": "Data",
            "insert_after": "ticket_id",
            "description": "Links to Student's Application ID",
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "refund_reason",
            "label": "Refund Reason",
            "fieldtype": "Small Text",
            "insert_after": "student_application_id",
        },
        {
            "dt": "CRM Deal",
            "fieldname": "refundable_amount",
            "label": "Refundable Amount",
            "fieldtype": "Currency",
            "insert_after": "refund_reason",
            "options": "currency",
            "in_list_view": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "master_status",
            "label": "Master Status",
            "fieldtype": "Select",
            "options": "\nSUPPORT_REVIEW\nSUPPORT_CLEARED\nSUPPORT_REJECTED",
            "insert_after": "refundable_amount",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "support_status",
            "label": "Support Status",
            "fieldtype": "Select",
            "options": "\nPending Consultation\nUnder Review\nAwaiting Student Response\nApproved\nRejected",
            "insert_after": "master_status",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "counsellor_name",
            "label": "Counsellor Name",
            "fieldtype": "Link",
            "options": "User",
            "insert_after": "support_status",
            "in_list_view": 1,
            "in_standard_filter": 1,
        },
        {
            "dt": "CRM Deal",
            "fieldname": "counsellor_notes",
            "label": "Counsellor Notes",
            "fieldtype": "Text",
            "insert_after": "counsellor_name",
        },
    ]

    _create_custom_fields(custom_fields)


def _create_custom_fields(custom_fields):
    """Helper to create custom fields."""
    for field_data in custom_fields:
        fieldname = field_data["fieldname"]
        dt = field_data["dt"]

        existing = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})

        if not existing:
            cf = frappe.new_doc("Custom Field")
            cf.update(field_data)
            cf.insert(ignore_permissions=True)
            print(f"  Created: {dt}.{fieldname}")
        else:
            # Update existing field
            cf = frappe.get_doc("Custom Field", {"dt": dt, "fieldname": fieldname})
            cf.update(field_data)
            cf.save(ignore_permissions=True)
            print(f"  Updated: {dt}.{fieldname}")


def setup_refund_request_statuses():
    """Setup CRM Deal statuses for refund workflow."""
    print("\n=== Setting up Refund Request statuses ===")

    # Note: These are for the CRM's status field (kanban view)
    # master_status and support_status are separate custom fields
    new_statuses = [
        {"name": "New", "position": 1, "type": "Open"},
        {"name": "Followup", "position": 2, "type": "Ongoing"},
        {"name": "Approved", "position": 3, "type": "Won"},
        {"name": "Rejected", "position": 4, "type": "Lost"},
    ]

    existing = frappe.get_all("CRM Deal Status", pluck="name")

    for status_data in new_statuses:
        status_name = status_data["name"]
        if status_name not in existing:
            doc = frappe.new_doc("CRM Deal Status")
            doc.deal_status = status_name
            doc.type = status_data["type"]
            doc.position = status_data["position"]
            doc.insert(ignore_permissions=True)
            print(f"  Created status: {status_name}")
        else:
            doc = frappe.get_doc("CRM Deal Status", status_name)
            doc.position = status_data["position"]
            doc.save(ignore_permissions=True)
            print(f"  Updated status: {status_name}")


def update_crm_field_layouts():
    """Update CRM Fields Layout to include custom fields in the UI."""
    import json

    print("\n=== Updating CRM Fields Layout ===")

    # Student fields for Organization
    student_fields = [
        "application_id", "first_name", "last_name",
        "student_email", "student_phone", "program",
        "elective", "batch", "university", "partner"
    ]

    # Refund Request fields for Deal
    refund_fields = [
        "refund_request_id", "ticket_id", "student_application_id",
        "refund_reason", "refundable_amount", "master_status",
        "support_status", "counsellor_name", "counsellor_notes"
    ]

    # Update Organization Side Panel
    _update_layout("CRM Organization-Side Panel", student_fields)

    # Update Organization Quick Entry
    _update_layout("CRM Organization-Quick Entry", student_fields[:6])  # First 6 fields for quick entry

    # Update Deal Side Panel
    _update_layout("CRM Deal-Side Panel", refund_fields)

    # Update Deal Quick Entry
    _update_layout("CRM Deal-Quick Entry", refund_fields[:5])  # First 5 fields for quick entry


def _update_layout(layout_name, fields_to_add):
    """Helper to update a CRM Fields Layout."""
    import json

    if not frappe.db.exists("CRM Fields Layout", layout_name):
        print(f"  Layout not found: {layout_name}")
        return

    layout_doc = frappe.get_doc("CRM Fields Layout", layout_name)
    layout_data = json.loads(layout_doc.layout) if layout_doc.layout else []

    if layout_data and len(layout_data) > 0:
        # Get existing fields in first section
        if "columns" in layout_data[0] and len(layout_data[0]["columns"]) > 0:
            existing_fields = layout_data[0]["columns"][0].get("fields", [])
        else:
            existing_fields = []
            layout_data[0]["columns"] = [{"fields": []}]

        # Add new fields if not present
        for field in fields_to_add:
            if field not in existing_fields:
                existing_fields.append(field)

        layout_data[0]["columns"][0]["fields"] = existing_fields

    layout_doc.layout = json.dumps(layout_data)
    layout_doc.save(ignore_permissions=True)
    print(f"  Updated: {layout_name}")
