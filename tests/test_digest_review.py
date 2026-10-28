
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from digest_model import DigestItem
from digest_review import update_digest_item


@pytest.fixture
def sample_item():
    return DigestItem(
        timestamp=datetime(2026, 10, 19, 9, 30),
        sender="Contractor Representative",
        statement="Drainage work reported as completed.",
        category="Confirmation Required",
        evidence_source="Other message",
        source_line=100,
    )


def test_update_changes_review_fields(sample_item):
    updated = update_digest_item(
        sample_item,
        category="Progress",
        evidence_source="Contractor-reported",
        review_status="Pending review",
        contractor="SinoSky",
        location="E8, Chainage 0+360",
        follow_up="Verify completed length with surveyor.",
    )

    assert updated.category == "Progress"
    assert updated.evidence_source == "Contractor-reported"
    assert updated.review_status == "Pending review"
    assert updated.contractor == "SinoSky"
    assert updated.location == "E8, Chainage 0+360"
    assert updated.follow_up == "Verify completed length with surveyor."


def test_original_item_is_not_modified(sample_item):
    update_digest_item(
        sample_item,
        category="Progress",
        evidence_source="Contractor-reported",
        review_status="Confirmed",
    )

    assert sample_item.category == "Confirmation Required"
    assert sample_item.review_status == "Pending review"
    assert sample_item.contractor is None


def test_original_message_details_are_preserved(sample_item):
    updated = update_digest_item(
        sample_item,
        category="Progress",
        evidence_source="Contractor-reported",
        review_status="Pending review",
    )

    assert updated.timestamp == sample_item.timestamp
    assert updated.sender == sample_item.sender
    assert updated.statement == sample_item.statement
    assert updated.source_line == sample_item.source_line


@pytest.mark.parametrize(
    "field,value",
    [
        ("category", "Safety"),
        ("evidence_source", "Verified"),
        ("review_status", "Completed"),
    ],
)
def test_invalid_values_are_rejected(sample_item, field, value):
    values = {
        "category": "Progress",
        "evidence_source": "Direct observation",
        "review_status": "Pending review",
    }
    values[field] = value

    with pytest.raises(ValueError):
        update_digest_item(sample_item, **values)


def test_blank_optional_details_become_none(sample_item):
    updated = update_digest_item(
        sample_item,
        category="Quality",
        evidence_source="Direct observation",
        review_status="Confirmed",
        contractor="  ",
        location="  ",
        follow_up="  ",
    )

    assert updated.contractor is None
    assert updated.location is None
    assert updated.follow_up is None
