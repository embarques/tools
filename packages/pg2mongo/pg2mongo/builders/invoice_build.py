from __future__ import annotations

from typing import Dict, Any

from pg2mongo import collections as cols
from pg2mongo.utils import to_utc, decimal_to_float

def build_invoice_doc(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a Mongo invoice document from a vwinvoice_api row.
    This focuses on the core header fields and nested sender/receiver.
    """
    doc: Dict[str, Any] = {
        "oldID": int(row["id"]),
        "number": row.get("number") or "",
        "createdAt": to_utc(row.get("time_created")),
        "updatedAt": to_utc(row.get("time_modified")),
        "date": to_utc(row.get("invoice_date")),
        "paidRegion": row.get("paid_region") or "",
        "paidStatus": row.get("paid_status") or "",
        "branch": {"_id": int(row.get("branch_id") or 0)},
        "cost": decimal_to_float(row.get("cost")),
        "user": {"_id": int(row.get("user_id") or 0), "name": row.get("user.name") or ""},
        "driver": {"_id": int(row.get("driver_id") or 0), "name": row.get("driver.name") or ""},
        "container": {"_id": int(row.get("container_id") or 0), "name": row.get("container_designation") or ""},
        "discount": decimal_to_float(row.get("discount") or 0),
        "payment": decimal_to_float(row.get("payment") or 0),
        "balance": decimal_to_float(row.get("balance") or 0),
        "surcharge": decimal_to_float(row.get("recharge") or 0),
        cols.INVOICE_DETAILS_FIELD: [],
    }

    # Sender
    sender_id = row.get("sender.id")
    if sender_id:
        sender = {
            "oldID": int(sender_id),
            "name": row.get("sender.name") or "",
            "customerType": int(row.get("sender.cus_type") or 0),
            "phone1": row.get("sender.phone1") or "",
            "phone2": row.get("sender.phone2") or "",
            "createdAt": to_utc(row.get("sender.time_created")),
            "branch": {"_id": int(row.get("sender.branch_id") or 0)},
            "createdByID": int(row.get("sender.created_by_id") or 0),
            "address": {
                "address1": row.get("sender.address.address1") or "",
                "address2": row.get("sender.address.address2") or "",
                "apartment": row.get("sender.address.apt") or "",
                "city": row.get("sender.address.city") or "",
                "state": row.get("sender.address.state") or "",
                "zipcode": row.get("sender.address.zipcode") or "",
                "country": row.get("sender.address.country") or "",
            },
        }
        doc["sender"] = sender

    # Receiver
    recv_id = row.get("receiver.id")
    if recv_id:
        receiver = {
            "oldID": int(recv_id),
            "name": row.get("receiver.name") or "",
            "customerType": int(row.get("receiver.cus_type") or 0),
            "phone1": row.get("receiver.phone1") or "",
            "phone2": row.get("receiver.phone2") or "",
            "createdAt": to_utc(row.get("receiver.time_created")),
            "branch": {"_id": int(row.get("receiver.branch_id") or 0)},
            "createdByID": int(row.get("receiver.created_by_id") or 0),
            "address": {
                "address1": row.get("receiver.address.address1") or "",
                "address2": row.get("receiver.address.address2") or "",
                "apartment": row.get("receiver.address.apt") or "",
                "city": row.get("receiver.address.city") or "",
                "state": row.get("receiver.address.state") or "",
                "zipcode": row.get("receiver.address.zipcode") or "",
                "country": row.get("receiver.address.country") or "",
            },
        }
        doc["receiver"] = receiver

    return doc
