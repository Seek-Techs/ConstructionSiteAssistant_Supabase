
from datetime import date, datetime

import pytest

from digest_model import DigestItem, SiteDigest


@pytest.fixture
def sample_item():
    return DigestItem(
        timestamp=datetime(2026, 10, 19, 10, 30),
        sender="Contractor representative",
        statement="The contractor reported that drainage work progressed.",
        category="Progress",
        evidence_source="Contractor-reported",
        source_line=25,
        contractor="Example Contractor",
        location="N4–N5",
    )


def test_digest_item_defaults_to_pending_review(sample_item):
    assert sample_item.review_status == "Pending review"


def test_digest_retrieves_pending_items(sample_item):
    confirmed_item = DigestItem(
        timestamp=datetime(2026, 10, 19, 11, 0),
        sender="Supervisor",
        statement="Inspection record reviewed.",
        category="Quality",
        evidence_source="Direct observation",
        source_line=26,
        review_status="Confirmed",
    )

    digest = SiteDigest(
        start_date=date(2026, 10, 19),
        end_date=date(2026, 10, 19),
        items=[sample_item, confirmed_item],
    )

    assert digest.pending_items == [sample_item]


def test_rejects_empty_statement():
    with pytest.raises(ValueError, match="Statement"):
        DigestItem(
            timestamp=datetime(2026, 10, 19, 10, 30),
            sender="Supervisor",
            statement="   ",
            category="Quality",
            evidence_source="Direct observation",
            source_line=1,
        )


def test_rejects_invalid_category(sample_item):
    with pytest.raises(ValueError, match="category"):
        sample_item.category = "Unverified Category"
        sample_item.__post_init__()


def test_rejects_end_date_before_start_date():
    with pytest.raises(ValueError, match="End date"):
        SiteDigest(
            start_date=date(2026, 10, 19),
            end_date=date(2026, 10, 15),
        )
