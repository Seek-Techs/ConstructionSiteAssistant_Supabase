
"""Parse common WhatsApp plain-text chat exports."""

from dataclasses import dataclass
from datetime import datetime
import re


@dataclass(frozen=True)
class WhatsAppMessage:
    """One message extracted from a WhatsApp text export."""

    timestamp: datetime
    sender: str | None
    text: str
    source_line: int


# Common export formats:
# 16/10/2026, 08:15 - Sender: Message
# [16/10/2026, 08:15:00] Sender: Message
# 2026-10-16, 08:15 - Sender: Message

MESSAGE_START = re.compile(
    r"^(?:"
    r"\[(?P<bracket_date>\d{1,4}[/-]\d{1,2}[/-]\d{2,4}), "
    r"(?P<bracket_time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APMapm]{2})?)\]"
    r"|"
    r"(?P<plain_date>\d{1,4}[/-]\d{1,2}[/-]\d{2,4}), "
    r"(?P<plain_time>\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APMapm]{2})?)"
    r")(?:\s*[-–]\s*|\s+)(?P<content>.*)$"
)


DATE_FORMATS = (
    "%m/%d/%y",
    "%m-%d-%y",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d/%m/%y",
    "%d-%m-%y",
)

TIME_FORMATS = (
    "%H:%M",
    "%H:%M:%S",
    "%I:%M %p",
    "%I:%M:%S %p",
)


def _parse_timestamp(date_text: str, time_text: str) -> datetime:
    """Convert supported date and time text into a datetime."""
    normalized_time = re.sub(r"\s+", " ", time_text.strip().upper())

    for date_format in DATE_FORMATS:
        try:
            parsed_date = datetime.strptime(date_text, date_format).date()
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Unsupported date format: {date_text!r}")

    for time_format in TIME_FORMATS:
        try:
            parsed_time = datetime.strptime(
                normalized_time, time_format
            ).time()
            return datetime.combine(parsed_date, parsed_time)
        except ValueError:
            continue

    raise ValueError(f"Unsupported time format: {time_text!r}")


def parse_whatsapp_text(content: str) -> list[WhatsAppMessage]:
    """Parse a WhatsApp text export into individual messages.

    Lines that do not start with a supported timestamp are treated as
    continuation lines for the current message. Lines before the first
    recognised message are ignored.
    """
    messages: list[WhatsAppMessage] = []
    current_timestamp: datetime | None = None
    current_sender: str | None = None
    current_text: list[str] = []
    current_source_line = 0

    def save_current() -> None:
        if current_timestamp is None:
            return

        messages.append(
            WhatsAppMessage(
                timestamp=current_timestamp,
                sender=current_sender,
                text="\n".join(current_text).strip(),
                source_line=current_source_line,
            )
        )

    for line_number, line in enumerate(content.splitlines(), start=1):
        match = MESSAGE_START.match(line)

        if not match:
            if current_timestamp is not None:
                current_text.append(line)
            continue

        save_current()

        date_text = match.group("bracket_date") or match.group("plain_date")
        time_text = match.group("bracket_time") or match.group("plain_time")

        try:
            current_timestamp = _parse_timestamp(date_text, time_text)
        except ValueError:
            # Preserve the text as part of the current message rather than
            # silently creating a potentially incorrect timestamp.
            current_text.append(line)
            continue

        current_source_line = line_number
        content_part = match.group("content")

        # A colon separates a sender name from the message. System
        # notifications without that pattern have sender=None.
        sender_match = re.match(r"([^:]+):\s?(.*)$", content_part)

        if sender_match:
            current_sender = sender_match.group(1).strip()
            first_text = sender_match.group(2)
        else:
            current_sender = None
            first_text = content_part

        current_text = [first_text]

    save_current()
    return messages
