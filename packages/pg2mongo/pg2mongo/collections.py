"""
MongoDB collection names and related document field names.

Multi-word names use snake_case to match the database.
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
ACTIVITY_LOGS = "activity_logs"
JOURNALS = "journals"

# Invoice document field holding references to invoice_details documents
INVOICE_DETAILS_FIELD = "invoice_details"


def qualified(db_name: str, collection: str) -> str:
    """Format ``database.collection`` for log output."""
    return f"{db_name}.{collection}"
