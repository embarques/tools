"""
MongoDB collection names and related document field names.

Naming split (matches the Go / Mongo app):
  - **Collections**: lowercase; multi-word → snake_case (``invoice_details``).
  - **Document fields**: camelCase from Go ``bson`` tags (``createdAt``, ``oldID``,
    ``invoiceDetails``, ``customerType``, etc.).
"""

# Collections (single-word names stay lowercase without underscores)
BRANCHES = "branches"
CUSTOMERS = "customers"
INVOICES = "invoices"
INVOICE_DETAILS = "invoice_details"
PICKUPS = "pickups"
CONTAINERS = "containers"
DELIVERIES = "deliveries"
EMPLOYEES = "employees"
USERS = "users"
COUNTERS = "counters"
ACCOUNTS = "accounts"
INCOME_STATEMENTS = "income_statements"
ROLES = "roles"
PERMISSIONS = "permissions"
CITIES = "cities"
ACTIVITY_LOG = "activity_log"
# Backward-compatible alias (deprecated)
ACTIVITY_LOGS = ACTIVITY_LOG
JOURNALS = "journals"

# Invoice document field holding references to invoice_details documents
INVOICE_DETAILS_FIELD = "invoiceDetails"


def qualified(db_name: str, collection: str) -> str:
    """Format ``database.collection`` for log output."""
    return f"{db_name}.{collection}"
