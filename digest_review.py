
"""Functions for reviewing WhatsApp digest candidates."""

from dataclasses import replace

from digest_model import (
    DIGEST_CATEGORIES,
    EVIDENCE_SOURCES,
    REVIEW_STATUSES,
    DigestItem,
)


def update_digest_item(
    item: DigestItem,
    *,
    category: str,
    evidence_source: str,
    review_status: str,
    contractor: str = "",
    location: str = "",
    follow_up: str = "",
) -> DigestItem:
    """Return an updated copy of a digest item after human review.

    The original item remains unchanged. Original message details,
    including timestamp, sender, statement, and source line, are preserved.
    """
    if category not in DIGEST_CATEGORIES:
        raise ValueError(f"Invalid category: {category!r}")

    if evidence_source not in EVIDENCE_SOURCES:
        raise ValueError(f"Invalid evidence source: {evidence_source!r}")

    if review_status not in REVIEW_STATUSES:
        raise ValueError(f"Invalid review status: {review_status!r}")

    return replace(
        item,
        category=category,
        evidence_source=evidence_source,
        review_status=review_status,
        contractor=contractor.strip() or None,
        location=location.strip() or None,
        follow_up=follow_up.strip() or None,
    )
