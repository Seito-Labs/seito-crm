"""
Setup script for customizing Frappe CRM for Refund Request workflow.
Run with: bench --site <site> execute seito.setup.setup_crm.execute
This script is idempotent - safe to run multiple times.
"""

import frappe


def execute():
    """Main entry point for CRM customization."""
    print("Starting CRM customization for Seito...")

    # Setup roles and permissions
    setup_roles()
    setup_permissions()

    # Replace CRM Deal statuses with Refund Request statuses
    setup_refund_request_statuses()

    # Add custom fields to CRM Organization for student info
    add_student_custom_fields()

    # Update CRM Fields Layout to show custom fields
    update_crm_field_layouts()

    frappe.db.commit()
    print("CRM customization completed successfully!")


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

    # DocTypes to grant permissions on
    doctypes = [
        "CRM Deal",
        "CRM Organization",
        "CRM Deal Status",
        "FCRM Note",
        "CRM Task",
        "Comment",
        "CRM Notification",
    ]

    # Permission matrix
    # Agent: Full CRUD on records (no delete)
    # Team Lead: Full CRUD + import (no delete)
    # Manager: Full CRUD + delete + import
    # Admin: Full access
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
            # Check if permission already exists
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


def setup_refund_request_statuses():
    """Replace CRM Deal statuses with Refund Request workflow statuses."""
    print("\n=== Setting up Refund Request statuses ===")

    # Define new statuses for refund requests
    # type must be one of: Open, Ongoing, On Hold, Won, Lost
    new_statuses = [
        {"name": "New", "position": 1, "type": "Open"},
        {"name": "Followup", "position": 2, "type": "Ongoing"},
        {"name": "Approved", "position": 3, "type": "Won"},
        {"name": "Rejected", "position": 4, "type": "Lost"},
    ]

    # Get existing statuses
    existing = frappe.get_all("CRM Deal Status", pluck="name")
    print(f"Existing statuses: {existing}")

    # Create new statuses if they don't exist
    for status_data in new_statuses:
        status_name = status_data["name"]
        if status_name not in existing:
            doc = frappe.new_doc("CRM Deal Status")
            doc.deal_status = status_name
            doc.type = status_data["type"]  # Must be: Open, Ongoing, On Hold, Won, Lost
            doc.position = status_data["position"]
            doc.insert(ignore_permissions=True)
            print(f"  Created status: {status_name}")
        else:
            # Update position if exists
            doc = frappe.get_doc("CRM Deal Status", status_name)
            doc.position = status_data["position"]
            doc.save(ignore_permissions=True)
            print(f"  Updated status: {status_name}")

    # Optionally delete old statuses (comment out if you want to keep them)
    old_statuses = ["Qualification", "Demo/Making", "Proposal/Quotation",
                    "Negotiation", "Ready to Close", "Won", "Lost"]
    for old_status in old_statuses:
        if frappe.db.exists("CRM Deal Status", old_status):
            # Check if any deals use this status
            deals_count = frappe.db.count("CRM Deal", {"status": old_status})
            if deals_count == 0:
                frappe.delete_doc("CRM Deal Status", old_status, force=True)
                print(f"  Deleted old status: {old_status}")
            else:
                print(f"  Skipping deletion of {old_status} - {deals_count} deals use it")


def add_student_custom_fields():
    """Add custom fields to CRM Organization for student information."""
    print("\n=== Adding student custom fields to CRM Organization ===")

    custom_fields = [
        {
            "dt": "CRM Organization",
            "fieldname": "student_id",
            "label": "Student ID",
            "fieldtype": "Data",
            "insert_after": "organization_name",
            "unique": 1,
        },
        {
            "dt": "CRM Organization",
            "fieldname": "enrollment_status",
            "label": "Enrollment Status",
            "fieldtype": "Select",
            "options": "Enquiry\nEnrolled\nActive\nCompleted\nDropped",
            "insert_after": "student_id",
        },
        {
            "dt": "CRM Organization",
            "fieldname": "enrolled_on",
            "label": "Enrolled On",
            "fieldtype": "Date",
            "insert_after": "enrollment_status",
        },
    ]

    for field_data in custom_fields:
        fieldname = field_data["fieldname"]
        dt = field_data["dt"]

        # Check if custom field already exists
        existing = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})

        if not existing:
            cf = frappe.new_doc("Custom Field")
            cf.update(field_data)
            cf.insert(ignore_permissions=True)
            print(f"  Created custom field: {dt}.{fieldname}")
        else:
            print(f"  Custom field already exists: {dt}.{fieldname}")


def update_crm_field_layouts():
    """Update CRM Fields Layout to include custom fields in the UI."""
    import json

    print("\n=== Updating CRM Fields Layout ===")

    # Update Organization Side Panel to include student fields
    layout_name = "CRM Organization-Side Panel"
    if frappe.db.exists("CRM Fields Layout", layout_name):
        layout_doc = frappe.get_doc("CRM Fields Layout", layout_name)
        layout_data = json.loads(layout_doc.layout)

        # Add student fields to the first section
        student_fields = ["student_id", "enrollment_status", "enrolled_on"]
        if layout_data and len(layout_data) > 0:
            existing_fields = layout_data[0].get("columns", [{}])[0].get("fields", [])
            for field in student_fields:
                if field not in existing_fields:
                    existing_fields.append(field)
            layout_data[0]["columns"][0]["fields"] = existing_fields

        layout_doc.layout = json.dumps(layout_data)
        layout_doc.save(ignore_permissions=True)
        print(f"  Updated: {layout_name}")

    # Update Organization Quick Entry
    layout_name = "CRM Organization-Quick Entry"
    if frappe.db.exists("CRM Fields Layout", layout_name):
        layout_doc = frappe.get_doc("CRM Fields Layout", layout_name)
        layout_data = json.loads(layout_doc.layout) if layout_doc.layout else []

        # Add student fields
        student_fields = ["student_id", "enrollment_status", "enrolled_on"]
        if layout_data and len(layout_data) > 0:
            existing_fields = layout_data[0].get("columns", [{}])[0].get("fields", [])
            for field in student_fields:
                if field not in existing_fields:
                    existing_fields.append(field)
            layout_data[0]["columns"][0]["fields"] = existing_fields

        layout_doc.layout = json.dumps(layout_data)
        layout_doc.save(ignore_permissions=True)
        print(f"  Updated: {layout_name}")


def hide_leads_from_sidebar():
    """
    Note: Hiding Leads from sidebar requires modifying CRM Settings or
    the Vue frontend configuration. This is typically done via the UI
    in CRM Settings or by modifying the sidebar configuration.
    """
    print("\n=== Note about hiding Leads ===")
    print("  To hide Leads from sidebar, go to CRM Settings in the UI")
    print("  or modify the CRM sidebar configuration.")
