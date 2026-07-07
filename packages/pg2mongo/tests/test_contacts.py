from pg2mongo.builders.contacts import (
    customer_addresses_from_legacy,
    phones_from_legacy,
    primary_phone_number,
)


def test_phones_from_legacy_primary_and_secondary():
    phones = phones_from_legacy("305-555-1000", "305-555-2000")
    assert phones == [
        {"type": "mobile", "number": "+13055551000", "isPrimary": True},
        {"type": "home", "number": "+13055552000"},
    ]


def test_phones_from_legacy_single_phone_is_primary():
    phones = phones_from_legacy("3055551000", None)
    assert phones[0]["isPrimary"] is True


def test_customer_addresses_from_legacy():
    addresses = customer_addresses_from_legacy(
        {
            "address1": "3141 23 Street",
            "apartment": "Apt 2",
            "city": "Miami",
            "state": "FL",
            "zipCode": "33101",
            "country": "US",
        },
        primary_phone="+17865551234",
    )
    assert len(addresses) == 1
    assert addresses[0]["isPrimary"] is True
    assert addresses[0]["zipcode"] == "33101"
    assert addresses[0]["phone"] == "+17865551234"


def test_primary_phone_number():
    phones = phones_from_legacy("3055551000", "3055552000")
    assert primary_phone_number(phones) == "+13055551000"
