from __future__ import annotations
from typing import Any, Dict, Optional
from decimal import Decimal
from datetime import datetime, date
from pg2mongo.models import (
    InvoiceDocument, BranchRef, UserRef, DriverRef, ContainerRef, Party, Address,
    CustomerDocument
)


def _to_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except Exception:
        return None


def _to_dt(d: Any) -> Optional[datetime]:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    return None


def _norm_upper(s: Optional[str]) -> Optional[str]:
    return s.upper() if isinstance(s, str) else s


# -------- Invoice (view) --------
def map_invoice_view_row_to_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    sender = Party(
        oldID=row.get("sender_id"),
        customerType=row.get("sender_cus_type"),
        name=row.get("sender_name"),
        phone1=row.get("sender_phone1"),
        branch=BranchRef(_id=row["sender_branch_id"]) if row.get("sender_branch_id") is not None else None,
        createdAt=_to_dt(row.get("sender_time_created")),
        createdByID=row.get("sender_created_by_id"),
        address=Address(
            address1=row.get("sender_address1"),
            address2=row.get("sender_address2"),
            city=row.get("sender_city"),
            state=row.get("sender_state"),
            country=row.get("sender_country"),
        ),
    ) if row.get("sender_id") is not None else None

    receiver = Party(
        oldID=row.get("receiver_id"),
        customerType=row.get("receiver_cus_type"),
        name=row.get("receiver_name"),
        phone1=row.get("receiver_phone1"),
        branch=BranchRef(_id=row["receiver_branch_id"]) if row.get("receiver_branch_id") is not None else None,
        createdAt=_to_dt(row.get("receiver_time_created")),
        createdByID=row.get("receiver_created_by_id"),
        address=Address(
            address1=row.get("receiver_address1"),
            address2=row.get("receiver_address2"),
            city=row.get("receiver_city"),
            state=row.get("receiver_state"),
            country=row.get("receiver_country"),
        ),
    ) if row.get("receiver_id") is not None else None

    doc = InvoiceDocument(
        oldID=row.get("id"),
        number=str(row.get("number") or ""),
        createdAt=_to_dt(row.get("time_created")),
        updatedAt=_to_dt(row.get("time_modified")),
        date=_to_dt(row.get("invoice_date")),
        paidRegion=_norm_upper(row.get("paid_region")),
        paidStatus=_norm_upper(row.get("paid_status")),
        branch=BranchRef(_id=row["branch_id"]) if row.get("branch_id") is not None else None,
        user=UserRef(_id=row["user_id"]) if row.get("user_id") is not None else None,
        driver=DriverRef(_id=row["driver_id"]) if row.get("driver_id") is not None else None,
        container=ContainerRef(_id=row["container_id"]) if row.get("container_id") is not None else None,
        cost=_to_float(row.get("cost")),
        discount=_to_float(row.get("discount")),
        payment=_to_float(row.get("payment")),
        balance=_to_float(row.get("balance")),
        recharge=_to_float(row.get("recharge")),
        sender=sender,
        receiver=receiver,
        invoice_details=None,
    ).model_dump()
    return doc


# -------- Customer (view) --------
def map_customer_view_row_to_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    addr = Address(
        address1=row.get("address1"),
        address2=row.get("address2"),
        city=row.get("city"),
        state=row.get("state"),
        country=row.get("country"),
    )
    doc = CustomerDocument(
        oldID=row.get("id"),
        customerType=row.get("cus_type"),
        name=str(row.get("name") or ""),
        phone1=row.get("phone1"),
        phone2=row.get("phone2"),
        idNumber=row.get("id_number"),
        active=row.get("active"),
        createdAt=_to_dt(row.get("time_created")),
        createdByID=row.get("created_by_id"),
        branch=BranchRef(_id=row["branch_id"]) if row.get("branch_id") is not None else None,
        address=addr,
    ).model_dump()
    return doc
