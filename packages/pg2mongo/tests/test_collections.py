from pg2mongo import collections as cols


def test_multi_word_collections_use_snake_case():
    assert cols.INVOICE_DETAILS == "invoice_details"
    assert cols.INCOME_STATEMENTS == "income_statements"
    assert cols.ACTIVITY_LOG == "activity_log"
    assert cols.ACTIVITY_LOGS == "activity_log"
    assert cols.INVOICE_DETAILS_FIELD == "invoiceDetails"


def test_qualified():
    assert cols.qualified("emsysdb", cols.INVOICE_DETAILS) == "emsysdb.invoice_details"
