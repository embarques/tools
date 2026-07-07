from __future__ import annotations

from pg2mongo.builders.contacts import primary_phone_number
from pg2mongo.builders.customer_build import build_customer_doc
from pg2mongo.match_keys import customer_match_filter
from pg2mongo.utils import pg_row_to_dict


CUSTOMER_BY_ID_SQL = """
SELECT c.id,
       c.c_type AS "cus_type",
       c.branch_id,
       c.name,
       c.phone1,
       c.phone2,
       c.id_number,
       c.active,
       c."address.address1",
       c."address.apt",
       c."time_created",
       c."created_by_id",
       c."address.address2",
       c."address.city",
       c."address.state",
       c."address.zipcode",
       c."address.country",
       b.code AS branch_code,
       b.name AS branch_name
FROM vwcustomer_api c
LEFT JOIN branch b ON b.id = c.branch_id
WHERE c.id = %s
"""


def fetch_customer_doc_by_pg_id(pg_conn, pg_customer_id: int) -> dict | None:
    """Load one customer row from Postgres and build the API-shaped Mongo doc."""
    with pg_conn.cursor() as cur:
        cur.execute(CUSTOMER_BY_ID_SQL, (pg_customer_id,))
        row = cur.fetchone()
        if not row:
            return None
        if not isinstance(row, dict):
            col_names = [desc[0] for desc in cur.description]
            row = pg_row_to_dict(row, col_names)
    return build_customer_doc(row)


def find_customer_in_mongo(
    mongo_client,
    mongo_db_name: str,
    pg_conn,
    pg_customer_id: int,
    *,
    session=None,
):
    """Resolve a Mongo customer ``_id`` from a Postgres customer id (no ``oldID`` field)."""
    from pg2mongo import collections as cols

    doc = fetch_customer_doc_by_pg_id(pg_conn, pg_customer_id)
    if not doc:
        return None

    filt = customer_match_filter(doc)
    return mongo_client[mongo_db_name][cols.CUSTOMERS].find_one(
        filt,
        {"_id": 1, "name": 1},
        session=session,
    )
