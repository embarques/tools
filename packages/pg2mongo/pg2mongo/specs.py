from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, Dict, Any, Optional, Tuple
from psycopg import Connection

from pg2mongo.mapping import map_invoice_view_row_to_doc, map_customer_view_row_to_doc

MapperFn = Callable[[Dict[str, Any]], Dict[str, Any]]
QueryBuilderFn = Callable[[str, str], Tuple[str, Tuple[Any, ...]]]


@dataclass(frozen=True)
class TableSpec:
    name: str
    upsert_key: str
    mapper: MapperFn
    query_builder: QueryBuilderFn  # required for explicit date window queries

    def iter_rows_between(
        self,
        conn: Connection,
        start_iso: str,
        end_iso: str,
        fetch_size: int = 1000,
    ) -> Iterable[Dict[str, Any]]:
        sql_text, params = self.query_builder(start_iso, end_iso)
        with conn.cursor(name=f"cur_{self.name}") as cur:
            cur.execute(sql_text, params)
            while True:
                chunk = cur.fetchmany(fetch_size)
                if not chunk:
                    break
                for r in chunk:
                    if isinstance(r, dict):
                        yield r
                    else:
                        yield {desc.name: val for desc, val in zip(cur.description, r)}


def _invoice_view_query(start_iso: str, end_iso: str):
    sql_text = """
SELECT
  id,
  number,
  time_created,
  time_modified,
  is_void,
  invoice_date,
  branch_id,
  container_id,
  "driver_id"              AS driver_id,
  "user_id"                AS user_id,
  cost,
  paid_status,
  paid_region,
  balance,
  payment,
  discount,
  recharge,

  "sender.id"                  AS sender_id,
  "sender.cus_type"            AS sender_cus_type,
  "sender.branch_id"           AS sender_branch_id,
  "sender.name"                AS sender_name,
  "sender.phone1"              AS sender_phone1,
  "sender.phone2"              AS sender_phone2,
  "sender.address.address1"    AS sender_address1,
  "sender.address.apt"         AS sender_apt,
  "sender.time_created"        AS sender_time_created,
  "sender.created_by_id"       AS sender_created_by_id,
  "sender.address.address2"    AS sender_address2,
  "sender.address.city"        AS sender_city,
  "sender.address.state"       AS sender_state,
  "sender.address.zipcode"     AS sender_zipcode,
  "sender.address.country"     AS sender_country,

  "receiver.id"                AS receiver_id,
  "receiver.cus_type"          AS receiver_cus_type,
  "receiver.branch_id"         AS receiver_branch_id,
  "receiver.name"              AS receiver_name,
  "receiver.phone1"            AS receiver_phone1,
  "receiver.phone2"            AS receiver_phone2,
  "receiver.address.address1"  AS receiver_address1,
  "receiver.address.apt"       AS receiver_apt,
  "receiver.time_created"      AS receiver_time_created,
  "receiver.created_by_id"     AS receiver_created_by_id,
  "receiver.address.address2"  AS receiver_address2,
  "receiver.address.city"      AS receiver_city,
  "receiver.address.state"     AS receiver_state,
  "receiver.address.zipcode"   AS receiver_zipcode,
  "receiver.address.country"   AS receiver_country

FROM vwinvoice_api
WHERE is_void = FALSE
  AND registration = 'completed'
  AND time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY invoice_date ASC
"""
    return sql_text, (start_iso, end_iso)


def _customer_view_query(start_iso: str, end_iso: str):
    sql_text = """
SELECT
  id,
  c_type                         AS cus_type,
  branch_id,
  name,
  phone1,
  phone2,
  id_number,
  active,
  "address.address1"             AS address1,
  "address.apt"                  AS apt,
  "time_created"                 AS time_created,
  "created_by_id"                AS created_by_id,
  "address.address2"             AS address2,
  "address.city"                 AS city,
  "address.state"                AS state,
  "address.zipcode"              AS zipcode,
  "address.country"              AS country
FROM vwcustomer_api
WHERE time_modified BETWEEN SYMMETRIC %s AND %s
ORDER BY time_created ASC
"""
    return sql_text, (start_iso, end_iso)


INVOICE_SPEC = TableSpec(
    name="invoice",
    upsert_key="oldID",
    mapper=map_invoice_view_row_to_doc,
    query_builder=_invoice_view_query,
)

CUSTOMER_SPEC = TableSpec(
    name="customer",
    upsert_key="oldID",
    mapper=map_customer_view_row_to_doc,
    query_builder=_customer_view_query,
)

REGISTRY = {
    "invoice": INVOICE_SPEC,
    "customer": CUSTOMER_SPEC,
}
