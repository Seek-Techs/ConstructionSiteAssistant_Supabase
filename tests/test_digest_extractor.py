
from datetime import date, datetime

from digest_extractor import build_digest_candidates
from whatsapp_parser import WhatsAppMessage


def sample_messages():
    return [
        WhatsAppMessage(
            timestamp=datetime(2026, 10, 18, 9, 0),
            sender="Supervisor",
            text="Earlier message",
            source_line=10,
        ),
        WhatsAppMessage(
            timestamp=datetime(2026, 10, 19, 10, 30),
            sender="Contractor",
            text="Work progress update",
            source_line=11,
        ),
        WhatsAppMessage(
            timestamp=datetime(2026, 10, 19, 11, 15),
            sender="Supervisor",
            text="",
            source_line=12,
        ),
    ]


def test_creates_candidates_only_for_selected_date():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 19),
    )

    assert len(digest.items) == 2
    assert all(
        item.timestamp.date() == date(2026, 10, 19)
        for item in digest.items
    )


def test_preserves_original_message_details():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 19),
    )

    item = digest.items[0]

    assert item.timestamp == datetime(2026, 10, 19, 10, 30)
    assert item.sender == "Contractor"
    assert item.statement == "Work progress update"
    assert item.source_line == 11


def test_candidates_start_pending_review():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 19),
    )

    assert all(
        item.review_status == "Pending review"
        for item in digest.items
    )


def test_does_not_claim_messages_are_verified():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 19),
    )

    assert all(
        item.category == "Confirmation Required"
        and item.evidence_source == "Other message"
        for item in digest.items
    )


def test_empty_message_is_preserved_with_placeholder():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 19),
    )

    assert digest.items[1].statement == "[Message contains no text]"


def test_date_range_includes_messages_on_both_dates():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 18),
        date(2026, 10, 19),
    )

    assert len(digest.items) == 3
    assert digest.start_date == date(2026, 10, 18)
    assert digest.end_date == date(2026, 10, 19)


def test_no_messages_produces_empty_digest():
    digest = build_digest_candidates(
        sample_messages(),
        date(2026, 10, 20),
    )

    assert digest.items == []
    assert digest.pending_items == []
