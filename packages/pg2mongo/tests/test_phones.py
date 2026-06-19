from pg2mongo.phones import normalize_phone_number, phone_doc


def test_normalize_phone_number_adds_country_code_for_ten_digits():
    assert normalize_phone_number("305-555-1000") == "+13055551000"


def test_normalize_phone_number_preserves_nanp_country_code():
    assert normalize_phone_number("1 (305) 555-1000") == "+13055551000"


def test_normalize_phone_number_cleans_existing_plus_number():
    assert normalize_phone_number("+1 305.555.1000") == "+13055551000"


def test_phone_doc_normalizes_number():
    assert phone_doc("mobile", "(305) 555-1000", is_primary=True) == {
        "type": "mobile",
        "number": "+13055551000",
        "isPrimary": True,
    }
