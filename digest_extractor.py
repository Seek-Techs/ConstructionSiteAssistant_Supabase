
"""Create reviewable digest candidates from WhatsApp messages."""

from datetime import date

from digest_model import DigestItem, SiteDigest
from whatsapp_digest import filter_messages_by_date
from whatsapp_parser import WhatsAppMessage


def build_digest_candidates(
    messages: list[WhatsAppMessage],
    start_date: date,
    end_date: date | None = None,
) -> SiteDigest:
    """Create one pending-review candidate for each selected message.

    Original message details are preserved. No automatic classification
    or verification of site activities is performed.
    """
    if end_date is None:
        end_date = start_date

    selected_messages = filter_messages_by_date(
        messages,
        start_date,
        end_date,
    )

    items = []

    for message in selected_messages:
        statement = message.text.strip() or "[Message contains no text]"

        items.append(
            DigestItem(
                timestamp=message.timestamp,
                sender=message.sender,
                statement=statement,
                category="Confirmation Required",
                evidence_source="Other message",
                source_line=message.source_line,
                review_status="Pending review",
            )
        )

    return SiteDigest(
        start_date=start_date,
        end_date=end_date,
        items=items,
    )
