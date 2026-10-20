
"""Data models for the reviewable WhatsApp site digest."""

from dataclasses import dataclass, field
from datetime import date, datetime


DIGEST_CATEGORIES = (
    "Progress",
    "Quality",
    "HSE",
    "Traffic",
    "Management Instruction",
    "Confirmation Required",
)

EVIDENCE_SOURCES = (
    "Direct observation",
    "Contractor-reported",
    "Management instruction",
    "Other message",
)

REVIEW_STATUSES = (
    "Pending review",
    "Confirmed",
    "Rejected/Corrected",
)


@dataclass
class DigestItem:
    """One potential activity, observation, or action for review."""

    timestamp: datetime
    sender: str | None
    statement: str
    category: str
    evidence_source: str
    source_line: int
    contractor: str | None = None
    location: str | None = None
    follow_up: str | None = None
    review_status: str = "Pending review"

    def __post_init__(self) -> None:
        """Reject incomplete or invalid digest records."""
        if not self.statement.strip():
            raise ValueError("Statement cannot be empty.")

        if self.category not in DIGEST_CATEGORIES:
            raise ValueError(
                f"Invalid category: {self.category!r}"
            )

        if self.evidence_source not in EVIDENCE_SOURCES:
            raise ValueError(
                f"Invalid evidence source: {self.evidence_source!r}"
            )

        if self.review_status not in REVIEW_STATUSES:
            raise ValueError(
                f"Invalid review status: {self.review_status!r}"
            )

        if self.source_line < 1:
            raise ValueError("Source line must be at least 1.")


@dataclass
class SiteDigest:
    """A date-scoped collection of reviewable digest items."""

    start_date: date
    end_date: date
    items: list[DigestItem] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.end_date < self.start_date:
            raise ValueError(
                "End date cannot be earlier than start date."
            )

    @property
    def pending_items(self) -> list[DigestItem]:
        """Return items that still need human review."""
        return [
            item
            for item in self.items
            if item.review_status == "Pending review"
        ]
