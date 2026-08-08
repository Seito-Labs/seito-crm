"""
Setup script for customizing Frappe CRM for Seito Refund Request workflow.
Run with: bench --site <site> execute crm.setup.setup_crm.execute
This script is idempotent - safe to run multiple times.

Field Mappings (Built-in → Your Fields):
- status → support_status (workflow statuses)
- deal_owner → counsellor_name (assigned user)
- organization → student (link to student)
- currency → for refundable_amount
- creation → created_at
- modified → updated_at
- lost_reason → rejection reason
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

    # Setup refund request statuses (maps to support_status)
    setup_refund_request_statuses()

    # Update CRM Fields Layout to show only relevant fields
    update_crm_field_layouts()

    # Configure quick filters for search bars
    setup_quick_filters()

    # Remove unused custom fields (mapped to built-in)
    cleanup_duplicate_fields()

    frappe.db.commit()
    print("\nCRM customization completed successfully!")
    print("\nField Mappings:")
    print("  status → Support Status (Pending Consultation, Under Review, etc.)")
    print("  deal_owner → Counsellor (assigned user)")
    print("  organization → Student")
    print("  lost_reason → Rejection reason (required when Rejected)")


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

    # Regular DocTypes - all roles can create/edit
    regular_doctypes = [
        "CRM Deal",
        "CRM Organization",
        "FCRM Note",
        "CRM Task",
        "Comment",
        "CRM Notification",
    ]

    # Admin-only DocTypes - only Admin can create/edit statuses
    admin_only_doctypes = [
        "CRM Deal Status",
    ]

    # Permissions for regular DocTypes
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

    # Permissions for admin-only DocTypes (CRM Deal Status, etc.)
    # Only Admin can create/write/delete, others can only read
    admin_only_permissions_map = {
        "Seito Agent": {
            "read": 1, "write": 0, "create": 0, "delete": 0,
            "report": 0, "export": 0, "import": 0, "share": 0,
            "print": 0, "email": 0
        },
        "Seito Team Lead": {
            "read": 1, "write": 0, "create": 0, "delete": 0,
            "report": 0, "export": 0, "import": 0, "share": 0,
            "print": 0, "email": 0
        },
        "Seito Manager": {
            "read": 1, "write": 0, "create": 0, "delete": 0,
            "report": 1, "export": 1, "import": 0, "share": 0,
            "print": 0, "email": 0
        },
        "Seito Admin": {
            "read": 1, "write": 1, "create": 1, "delete": 1,
            "report": 1, "export": 1, "import": 1, "share": 1,
            "print": 1, "email": 1
        },
    }

    # Apply permissions to regular DocTypes
    for doctype in regular_doctypes:
        _apply_permissions(doctype, permissions_map)

    # Apply restricted permissions to admin-only DocTypes
    for doctype in admin_only_doctypes:
        _apply_permissions(doctype, admin_only_permissions_map)


def _apply_permissions(doctype, permissions_map):
    """Helper to apply permissions to a DocType."""
    if not frappe.db.exists("DocType", doctype):
        print(f"  Skipping {doctype} - does not exist")
        return

    for role, perms in permissions_map.items():
        existing = frappe.db.exists("Custom DocPerm", {
            "parent": doctype,
            "role": role
        })

        if existing:
            # Update existing permission
            perm = frappe.get_doc("Custom DocPerm", existing)
            for key, val in perms.items():
                setattr(perm, key, val)
            perm.save(ignore_permissions=True)
            print(f"  Updated {role} permission for {doctype}")
        else:
            # Create new permission
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


def add_student_custom_fields():
    """Add custom fields to CRM Organization for student information.

    Maps:
    - organization_name → Student Name (built-in, keep)
    """
    print("\n=== Adding Student custom fields to CRM Organization ===")

    custom_fields = [
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
            "description": "Unique ID with user-provided prefix (e.g., APP-UUID)",
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
    """Add custom fields to CRM Deal for refund request information.

    Field Mappings (Built-in → Your Field):
    - status → support_status (Pending Consultation, Under Review, etc.)
    - deal_owner → counsellor_name (assigned user)
    - organization → student (link)
    - currency → for refundable_amount
    - lost_reason → rejection reason (required when Rejected)
    - creation → created_at
    - modified → updated_at
    """
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
            "fieldname": "counsellor_notes",
            "label": "Counsellor Notes",
            "fieldtype": "Text",
            "insert_after": "master_status",
        },
        {
            "dt": "CRM Deal",
            "fieldname": "resolution_notes",
            "label": "Resolution Notes",
            "fieldtype": "Text",
            "insert_after": "counsellor_notes",
            "description": "Notes for Approved/Rejected resolution",
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
            cf = frappe.get_doc("Custom Field", {"dt": dt, "fieldname": fieldname})
            cf.update(field_data)
            cf.save(ignore_permissions=True)
            print(f"  Updated: {dt}.{fieldname}")


def setup_refund_request_statuses():
    """Setup CRM Deal statuses for refund workflow.

    These map to support_status via the built-in status field.
    Status types determine workflow behavior:
    - Open: New requests
    - Ongoing: In progress
    - Won: Approved (final - cannot be changed)
    - Lost: Rejected (final - requires lost_reason)
    """
    print("\n=== Setting up Support Statuses ===")

    statuses = [
        {"name": "Pending Consultation", "position": 1, "type": "Open"},
        {"name": "Under Review", "position": 2, "type": "Ongoing"},
        {"name": "Awaiting Student Response", "position": 3, "type": "On Hold"},
        {"name": "Approved", "position": 4, "type": "Won"},
        {"name": "Rejected", "position": 5, "type": "Lost"},
    ]

    existing = frappe.get_all("CRM Deal Status", pluck="name")

    for status_data in statuses:
        status_name = status_data["name"]
        if status_name not in existing:
            doc = frappe.new_doc("CRM Deal Status")
            doc.deal_status = status_name
            doc.type = status_data["type"]
            doc.position = status_data["position"]
            doc.insert(ignore_permissions=True)
            print(f"  Created: {status_name} ({status_data['type']})")
        else:
            doc = frappe.get_doc("CRM Deal Status", status_name)
            doc.type = status_data["type"]
            doc.position = status_data["position"]
            doc.save(ignore_permissions=True)
            print(f"  Updated: {status_name} ({status_data['type']})")

    # Delete old unused statuses
    old_statuses = ["Qualification", "Demo/Making", "Proposal/Quotation",
                    "Negotiation", "Ready to Close", "Won", "Lost",
                    "New", "Followup"]
    for old_status in old_statuses:
        if frappe.db.exists("CRM Deal Status", old_status):
            deals_count = frappe.db.count("CRM Deal", {"status": old_status})
            if deals_count == 0:
                frappe.delete_doc("CRM Deal Status", old_status, force=True)
                print(f"  Deleted old: {old_status}")


def cleanup_duplicate_fields():
    """Remove custom fields that are mapped to built-in fields."""
    print("\n=== Cleaning up duplicate fields ===")

    # These custom fields should use built-in fields instead
    duplicates = [
        ("CRM Deal", "support_status"),      # Use built-in 'status'
        ("CRM Deal", "counsellor_name"),     # Use built-in 'deal_owner'
        ("CRM Organization", "student_id"),  # Use application_id
        ("CRM Organization", "enrollment_status"),  # Not needed
        ("CRM Organization", "enrolled_on"),  # Not needed
    ]

    for dt, fieldname in duplicates:
        cf_name = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
        if cf_name:
            frappe.delete_doc("Custom Field", cf_name, force=True)
            print(f"  Removed: {dt}.{fieldname}")


def update_crm_field_layouts():
    """Update CRM Fields Layout to show only relevant fields."""
    import json

    print("\n=== Updating CRM Fields Layout ===")

    # Student fields to show
    student_fields = [
        "application_id", "first_name", "last_name",
        "student_email", "student_phone", "program",
        "elective", "batch", "university", "partner"
    ]

    # Refund Request fields to show
    # Note: status = support_status, deal_owner = counsellor, organization = student
    refund_fields = [
        "refund_request_id", "ticket_id", "student_application_id",
        "organization",  # Student link
        "refund_reason", "refundable_amount", "currency",
        "master_status",
        "status",  # Support Status
        "deal_owner",  # Counsellor
        "counsellor_notes",
        "resolution_notes",  # For Approved/Rejected
        "lost_reason",  # Required for Rejected
    ]

    # Update layouts - show all fields in Side Panel, Quick Entry, and Data Fields
    _update_layout("CRM Organization-Side Panel", student_fields)
    _update_layout("CRM Organization-Quick Entry", student_fields)  # All student fields
    _update_layout("CRM Deal-Side Panel", refund_fields)
    _update_layout("CRM Deal-Quick Entry", refund_fields[:9])  # Up to master_status

    # Update Data Fields layout (main detail view)
    _update_data_fields_layout()


def _update_layout(layout_name, fields_to_show):
    """Helper to update a CRM Fields Layout with specific fields."""
    import json

    if not frappe.db.exists("CRM Fields Layout", layout_name):
        print(f"  Layout not found: {layout_name}")
        return

    layout_doc = frappe.get_doc("CRM Fields Layout", layout_name)

    # Create new layout with only the fields we want
    new_layout = [{
        "label": "Details",
        "name": "details",
        "opened": True,
        "columns": [{
            "fields": fields_to_show
        }]
    }]

    layout_doc.layout = json.dumps(new_layout)
    layout_doc.save(ignore_permissions=True)
    print(f"  Updated: {layout_name}")


def setup_quick_filters():
    """Configure quick filters (search bar fields) for CRM doctypes."""
    import json

    print("\n=== Setting up Quick Filters ===")

    # Student quick filters
    student_filters = [
        "organization_name",  # Student Name
        "application_id",
        "student_email",
        "program",
        "university",
        "batch",
    ]

    # Refund Request quick filters
    refund_filters = [
        "refund_request_id",
        "status",
        "organization",  # Student
        "deal_owner",  # Counsellor
        "master_status",
    ]

    _create_quick_filter_setting("CRM Organization", student_filters)
    _create_quick_filter_setting("CRM Deal", refund_filters)


def _create_quick_filter_setting(doctype, filters):
    """Create or update CRM Global Settings for quick filters."""
    import json

    setting_name = frappe.db.exists("CRM Global Settings", {
        "dt": doctype,
        "type": "Quick Filters"
    })

    if setting_name:
        doc = frappe.get_doc("CRM Global Settings", setting_name)
        doc.json = json.dumps(filters)
        doc.save(ignore_permissions=True)
        print(f"  Updated quick filters for {doctype}")
    else:
        doc = frappe.new_doc("CRM Global Settings")
        doc.dt = doctype
        doc.type = "Quick Filters"
        doc.json = json.dumps(filters)
        doc.insert(ignore_permissions=True)
        print(f"  Created quick filters for {doctype}")


def _update_data_fields_layout():
    """Update or create CRM Deal-Data Fields layout for Refund Request detail view."""
    import json

    layout_name = "CRM Deal-Data Fields"

    # Refund Request data fields layout
    # Organized in sections with multiple columns
    new_layout = [{
        "name": "first_tab",
        "sections": [
            {
                "label": "Request Details",
                "name": "request_details_section",
                "opened": True,
                "columns": [
                    {
                        "name": "column_1",
                        "fields": ["refund_request_id", "ticket_id", "student_application_id"]
                    },
                    {
                        "name": "column_2",
                        "fields": ["organization", "refundable_amount", "currency"]
                    }
                ]
            },
            {
                "label": "Status & Assignment",
                "name": "status_section",
                "opened": True,
                "columns": [
                    {
                        "name": "column_3",
                        "fields": ["status", "master_status"]
                    },
                    {
                        "name": "column_4",
                        "fields": ["deal_owner"]
                    }
                ]
            },
            {
                "label": "Notes",
                "name": "notes_section",
                "opened": True,
                "columns": [
                    {
                        "name": "column_5",
                        "fields": ["refund_reason", "counsellor_notes", "resolution_notes"]
                    }
                ]
            }
        ]
    }]

    if frappe.db.exists("CRM Fields Layout", layout_name):
        layout_doc = frappe.get_doc("CRM Fields Layout", layout_name)
        layout_doc.layout = json.dumps(new_layout)
        layout_doc.save(ignore_permissions=True)
        print(f"  Updated: {layout_name}")
    else:
        layout_doc = frappe.new_doc("CRM Fields Layout")
        layout_doc.dt = "CRM Deal"
        layout_doc.type = "Data Fields"
        layout_doc.layout = json.dumps(new_layout)
        layout_doc.insert(ignore_permissions=True)
        print(f"  Created: {layout_name}")
