"""Small helpers shared by tests."""

import struct
import zlib


def make_png_bytes(width=40, height=30, colour=(200, 80, 40)):
    """Build a tiny valid PNG without needing any imaging library."""

    row = b"\x00" + bytes(colour) * width
    raw = row * height

    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack(">I", len(data))
            + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class FakeUpload:
    """Mimics the parts of a Streamlit uploaded file that storage uses."""

    def __init__(self, name, data):
        self.name = name
        self._data = data

    def getvalue(self):
        return self._data


def document_text(document):
    """All text in a Word document: paragraphs, tables, header and footer.

    Two-column table rows are written as 'Label: value' so tests can look
    for the same wording a reader sees.
    """

    lines = [p.text for p in document.paragraphs]

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            if len(cells) == 2:
                lines.append(f"{cells[0]}: {cells[1]}")
            else:
                lines.append(" | ".join(cells))

    for section in document.sections:
        lines += [p.text for p in section.header.paragraphs]
        lines += [p.text for p in section.footer.paragraphs]

    return "\n".join(lines)


def count_row(document, first_heading):
    """Return {heading: count} for the summary table starting with a heading."""

    for table in document.tables:
        headings = [cell.text for cell in table.rows[0].cells]
        if headings and headings[0] == first_heading and len(table.rows) == 2:
            counts = [cell.text for cell in table.rows[1].cells]
            return dict(zip(headings, counts))

    raise AssertionError(f"No summary table starting with {first_heading}")
