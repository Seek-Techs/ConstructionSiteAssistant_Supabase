
from datetime import datetime, date

import pytest

from digest_model import DigestItem, SiteDigest
from digest_storage import (
    get_digest_items,
    list_digest_batches,
    save_digest,
    update_saved_digest_item,
    get_digest_batch
)


def test_get_digest_batch_returns_date_range(tmp_path, sample_digest):
    db_path = tmp_path / "test_digest.db"
    save_digest(sample_digest, "BATCH-001", db_path)

    batch = get_digest_batch("BATCH-001", db_path)

    assert batch is not None
    assert batch["batch_id"] == "BATCH-001"
    assert batch["start_date"] == date(2026, 10, 19)
    assert batch["end_date"] == date(2026, 10, 19)


def test_get_missing_digest_batch_returns_none(tmp_path):
    db_path = tmp_path / "test_digest.db"

    assert get_digest_batch("MISSING-BATCH", db_path) is None


@pytest.fixture
def sample_digest():
    item = DigestItem(
        timestamp=datetime(2026, 10, 19, 9, 40),
        sender="Site Supervisor",
        statement="Debris removal was reported during haulage.",
        category="Confirmation Required",
        evidence_source="Other message",
        source_line=42,
    )
    return SiteDigest(
        start_date=date(2026, 10, 19),
        end_date=date(2026, 10, 19),
        items=[item],
    )


def test_save_and_retrieve_digest(tmp_path, sample_digest):
    db_path = tmp_path / "test_digest.db"

    save_digest(sample_digest, "BATCH-001", db_path)

    items = get_digest_items("BATCH-001", db_path)

    assert len(items) == 1
    assert items[0].statement == (
        "Debris removal was reported during haulage."
    )
    assert items[0].sender == "Site Supervisor"
    assert items[0].source_line == 42
    assert items[0].review_status == "Pending review"


def test_review_decision_persists(tmp_path, sample_digest):
    db_path = tmp_path / "test_digest.db"
    save_digest(sample_digest, "BATCH-001", db_path)

    reviewed_item = get_digest_items("BATCH-001", db_path)[0]
    reviewed_item.category = "Progress"
    reviewed_item.evidence_source = "Contractor-reported"
    reviewed_item.contractor = "SinoSky"
    reviewed_item.location = "E8"
    reviewed_item.follow_up = "Verify progress on site."
    reviewed_item.review_status = "Confirmed"

    update_saved_digest_item(
        "BATCH-001", 1, reviewed_item, db_path
    )

    retrieved_item = get_digest_items("BATCH-001", db_path)[0]

    assert retrieved_item.category == "Progress"
    assert retrieved_item.evidence_source == "Contractor-reported"
    assert retrieved_item.contractor == "SinoSky"
    assert retrieved_item.location == "E8"
    assert retrieved_item.follow_up == "Verify progress on site."
    assert retrieved_item.review_status == "Confirmed"


def test_review_update_preserves_original_message(tmp_path, sample_digest):
    db_path = tmp_path / "test_digest.db"
    save_digest(sample_digest, "BATCH-001", db_path)

    item = get_digest_items("BATCH-001", db_path)[0]
    original_timestamp = item.timestamp
    original_sender = item.sender
    original_statement = item.statement
    original_source_line = item.source_line

    item.category = "Progress"
    item.evidence_source = "Contractor-reported"
    item.review_status = "Confirmed"
    item.contractor = "SinoSky"

    update_saved_digest_item("BATCH-001", 1, item, db_path)

    saved = get_digest_items("BATCH-001", db_path)[0]

    assert saved.timestamp == original_timestamp
    assert saved.sender == original_sender
    assert saved.statement == original_statement
    assert saved.source_line == original_source_line


def test_batch_listing_contains_saved_digest(tmp_path, sample_digest):
    db_path = tmp_path / "test_digest.db"
    save_digest(sample_digest, "BATCH-001", db_path)

    batches = list_digest_batches(db_path)

    assert len(batches) == 1
    assert batches[0]["batch_id"] == "BATCH-001"
    assert batches[0]["start_date"] == "2026-10-19"


def test_cannot_update_nonexistent_item(tmp_path):
    db_path = tmp_path / "test_digest.db"

    item = DigestItem(
        timestamp=datetime(2026, 10, 19, 9, 40),
        sender="Site Supervisor",
        statement="Test message",
        category="Progress",
        evidence_source="Contractor-reported",
        source_line=1,
    )

    with pytest.raises(ValueError, match="not found"):
        update_saved_digest_item(
            "MISSING-BATCH", 1, item, db_path
        )


def test_duplicate_batch_id_does_not_overwrite_existing_batch(
    tmp_path, sample_digest
):
    db_path = tmp_path / "test_digest.db"
    save_digest(sample_digest, "BATCH-001", db_path)

    with pytest.raises(Exception):
        save_digest(sample_digest, "BATCH-001", db_path)

    items = get_digest_items("BATCH-001", db_path)
    assert len(items) == 1
    assert items[0].statement == (
        "Debris removal was reported during haulage."
    )
