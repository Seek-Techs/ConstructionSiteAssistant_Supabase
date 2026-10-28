
"""Select WhatsApp messages for a daily or date-range digest."""

from datetime import date

from whatsapp_parser import WhatsAppMessage


def filter_messages_by_date(
    messages: list[WhatsAppMessage],
    start_date: date,
    end_date: date | None = None,
) -> list[WhatsAppMessage]:
    """Return messages between the selected dates, inclusive.

    If end_date is omitted, only start_date is selected.
    The original message order is preserved.
    """
    if end_date is None:
        end_date = start_date

    if end_date < start_date:
        raise ValueError("End date cannot be earlier than start date.")

    return [
        message
        for message in messages
        if start_date
        <= message.timestamp.date()
        <= end_date
    ]
