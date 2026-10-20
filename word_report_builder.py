from datetime import date

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.image.image import Image as DocxImage
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from storage import (
    DB_PATH,
    get_observation_photos,
    get_projects,
    resolve_photo_path,
)

STANDARD_CATEGORIES = ["Quality", "HSE", "Traffic", "Other"]
STATUSES = ["Open", "In Progress", "Closed"]

FONT_NAME = "Arial"
DARK_BLUE = RGBColor(0x1F, 0x3A, 0x5F)
LABEL_SHADING = "E8EDF3"
HEADER_SHADING = "1F3A5F"

# Photographs are scaled to fit inside this box, keeping their proportions.
MAX_PHOTO_WIDTH_INCHES = 4.5
MAX_PHOTO_HEIGHT_INCHES = 3.6

LABEL_COLUMN_INCHES = 1.8
VALUE_COLUMN_INCHES = 5.1


def format_date(iso_text):
    """Show 2026-10-20 as '20 Oct 2026'. Unreadable text is left as is."""

    try:
        parsed = date.fromisoformat(iso_text)
    except (ValueError, TypeError):
        return iso_text or ""

    return f"{parsed.day} {parsed:%b} {parsed.year}"


# ---------------------------------------------------------------- helpers


def _add_field(paragraph, instruction):
    """Insert a Word field (such as PAGE or NUMPAGES) into a paragraph."""

    run = paragraph.add_run()

    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")

    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction

    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")

    placeholder = OxmlElement("w:t")
    placeholder.text = "1"

    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")

    for element in (begin, instr, separate, placeholder, end):
        run._r.append(element)

    return run


def _add_header_and_footer(section):
    """Add a running header and a 'Page X of Y' footer."""

    header = section.header.paragraphs[0]
    header.text = "Construction Site Observation Report"
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in header.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run(
        f"Generated {format_date(date.today().isoformat())}  |  Page "
    )
    _add_field(footer, "PAGE")
    footer.add_run(" of ")
    _add_field(footer, "NUMPAGES")
    for run in footer.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x59, 0x59, 0x59)


def _style_document(document):
    """Set one consistent font and colour scheme."""

    styles = document.styles
    styles["Normal"].font.name = FONT_NAME
    styles["Normal"].font.size = Pt(10)

    for name, size in [
        ("Title", 20),
        ("Heading 1", 14),
        ("Heading 2", 12),
        ("Heading 3", 10),
    ]:
        style = styles[name]
        style.font.name = FONT_NAME
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = DARK_BLUE
        # Make Word use Arial for every script, not just Latin text.
        rfonts = style.element.rPr.rFonts
        for attribute in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
            rfonts.set(qn(attribute), FONT_NAME)
        for attribute in (
            "w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme",
        ):
            if rfonts.get(qn(attribute)) is not None:
                del rfonts.attrib[qn(attribute)]


def _shade(cell, hex_fill):
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), hex_fill)
    properties.append(shading)


def _write_cell(cell, text, bold=False, colour=None, size=None, align=None):
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(str(text))
    run.bold = bold
    if colour is not None:
        run.font.color.rgb = colour
    if size is not None:
        run.font.size = Pt(size)
    if align is not None:
        paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(2)
    paragraph.paragraph_format.space_before = Pt(2)


def _keep_table_together(table):
    """Ask Word not to split a short table across pages."""

    for row in table.rows[:-1]:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = True

    for row in table.rows:
        row_properties = row._tr.get_or_add_trPr()
        row_properties.append(OxmlElement("w:cantSplit"))


def _key_value_table(document, rows):
    """A two-column table: shaded label on the left, value on the right."""

    table = document.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(LABEL_COLUMN_INCHES)
    table.columns[1].width = Inches(VALUE_COLUMN_INCHES)

    for label, value in rows:
        cells = table.add_row().cells
        cells[0].width = Inches(LABEL_COLUMN_INCHES)
        cells[1].width = Inches(VALUE_COLUMN_INCHES)
        _shade(cells[0], LABEL_SHADING)
        _write_cell(cells[0], label, bold=True)
        _write_cell(cells[1], value)

    _keep_table_together(table)
    return table


def _count_table(document, headings, counts):
    """A header row of names with one row of counts beneath it."""

    table = document.add_table(rows=2, cols=len(headings))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for index, (heading, count) in enumerate(zip(headings, counts)):
        _shade(table.rows[0].cells[index], HEADER_SHADING)
        _write_cell(
            table.rows[0].cells[index],
            heading,
            bold=True,
            colour=RGBColor(0xFF, 0xFF, 0xFF),
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )
        _write_cell(
            table.rows[1].cells[index],
            count,
            align=WD_ALIGN_PARAGRAPH.CENTER,
        )

    _keep_table_together(table)


def _fit_picture_size(photo_path):
    """Return (width, height) that fits the photo box, keeping proportions."""

    image = DocxImage.from_file(str(photo_path))
    scale = min(
        MAX_PHOTO_WIDTH_INCHES / image.px_width,
        MAX_PHOTO_HEIGHT_INCHES / image.px_height,
    )
    return (
        Inches(image.px_width * scale),
        Inches(image.px_height * scale),
    )


def _joined(values, empty="Not recorded"):
    unique = sorted({value for value in values if value})
    return "; ".join(unique) if unique else empty


def _date_text(report_dates):
    if len(report_dates) == 1:
        return format_date(report_dates[0])
    return (
        f"{format_date(report_dates[0])} to "
        f"{format_date(report_dates[-1])}"
    )


# ---------------------------------------------------------------- report


def build_word_report(
    observations,
    output_path,
    db_path=DB_PATH,
    prepared_by="",
    checked_by="",
    report_reference="",
):
    """Create a Word management report with photographic evidence.

    Project details and photographs are read from the database at
    db_path, so a report is always built from the same database that the
    observations came from.

    prepared_by, checked_by and report_reference are optional. Names left
    blank are printed as empty lines to be completed by hand.
    """

    document = Document()

    section = document.sections[0]
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    _style_document(document)
    _add_header_and_footer(section)

    document.add_heading("CONSTRUCTION SITE OBSERVATION REPORT", level=0)

    if not observations:
        document.add_paragraph(
            "No observations were selected for this report."
        )
        document.save(output_path)
        return

    report_dates = sorted(
        {observation.report_date for observation in observations}
    )

    projects_by_code = {
        project["project_code"]: project
        for project in get_projects(db_path)
    }
    project_codes = sorted({
        observation.project_code
        for observation in observations
        if observation.project_code
    })

    project_names = []
    project_locations = []
    for code in project_codes:
        project = projects_by_code.get(code)
        if project:
            project_names.append(f"{project['project_name']} ({code})")
            project_locations.append(project["location"])
        else:
            project_names.append(f"{code} (not in the project register)")

    has_unlinked = any(
        not observation.project_code for observation in observations
    )
    if has_unlinked and project_names:
        project_names.append("Some observations are not linked to a project")

    # ---- Report details block
    identification = [
        (
            "Project",
            "; ".join(project_names) if project_names
            else "Not linked to a project",
        ),
    ]
    if project_locations:
        identification.append(
            ("Project location", _joined(project_locations))
        )
    identification += [
        ("Site", _joined(o.site for o in observations)),
        ("Contractor", _joined(o.contractor for o in observations)),
        (
            "Report date" if len(report_dates) == 1 else "Report period",
            _date_text(report_dates),
        ),
    ]
    if report_reference.strip():
        identification.append(
            ("Report reference", report_reference.strip())
        )
    identification.append(
        ("Observations included", str(len(observations)))
    )

    _key_value_table(document, identification)

    # ---- Management summary
    document.add_heading("Management Summary", level=1)

    scope_note = document.add_paragraph()
    scope_note.add_run(
        "Scope: the counts below describe only the "
        f"{len(observations)} observation(s) selected for this report. "
        "They are not a summary of all observations recorded for the "
        "project."
    ).italic = True

    category_counts = [
        sum(1 for o in observations if o.category == category)
        for category in STANDARD_CATEGORIES
    ]
    # Older or imported records may carry a category outside the standard
    # list. Count them so the summary always adds up to the total.
    unlisted_count = len(observations) - sum(category_counts)
    category_counts[STANDARD_CATEGORIES.index("Other")] += unlisted_count

    category_label = document.add_paragraph()
    category_label.add_run("By category").bold = True
    category_label.paragraph_format.keep_with_next = True
    _count_table(
        document,
        STANDARD_CATEGORIES + ["Total"],
        category_counts + [len(observations)],
    )

    status_counts = [
        sum(1 for o in observations if o.status == status)
        for status in STATUSES
    ]
    status_label = document.add_paragraph()
    status_label.add_run("By action status").bold = True
    status_label.paragraph_format.space_before = Pt(10)
    status_label.paragraph_format.keep_with_next = True
    _count_table(
        document,
        STATUSES + ["Total"],
        status_counts + [len(observations)],
    )

    # ---- Observations, grouped by category
    extra_categories = sorted({
        observation.category
        for observation in observations
        if observation.category not in STANDARD_CATEGORIES
    })

    photo_number = 0

    for category in STANDARD_CATEGORIES + extra_categories:
        category_observations = [
            observation
            for observation in observations
            if observation.category == category
        ]

        if not category_observations:
            continue

        document.add_heading(category, level=1)

        for observation in category_observations:
            document.add_heading(
                f"{observation.observation_id} — {observation.site}",
                level=2,
            )

            if observation.information_source == "Contractor-reported":
                source_text = (
                    "Contractor-reported (not directly observed by the "
                    "preparer)"
                )
            else:
                source_text = observation.information_source

            rows = [
                ("Date", format_date(observation.report_date)),
                ("Location / Chainage", observation.location),
                ("Contractor", observation.contractor),
                ("Information source", source_text),
                ("Observation", observation.description),
                ("Required action", observation.required_action),
                ("Responsible party", observation.responsible_party),
                (
                    "Action due date",
                    format_date(observation.due_date)
                    if observation.due_date else "Not set",
                ),
                ("Status", observation.status),
            ]

            if observation.verification_notes.strip():
                rows.append(
                    ("Verification notes", observation.verification_notes)
                )

            _key_value_table(document, rows)

            # Photographs associated with this observation.
            photos = get_observation_photos(
                observation.observation_id,
                db_path,
            )

            heading = document.add_heading("Photographic Evidence", level=3)
            heading.paragraph_format.space_before = Pt(10)

            if not photos:
                document.add_paragraph(
                    "No photographs attached to this observation."
                )
                continue

            for photo in photos:
                label = photo.get("caption", "").strip() or photo[
                    "original_filename"
                ]
                photo_path = resolve_photo_path(photo, db_path)

                if photo_path is None:
                    document.add_paragraph(
                        f"Photo file unavailable: {label}"
                    )
                    continue

                try:
                    width, height = _fit_picture_size(photo_path)
                    document.add_picture(
                        str(photo_path),
                        width=width,
                        height=height,
                    )
                except Exception:
                    document.add_paragraph(
                        f"Photo could not be embedded: {label}"
                    )
                    continue

                photo_number += 1

                # Keep the picture on the same page as its caption.
                picture_paragraph = document.paragraphs[-1]
                picture_paragraph.paragraph_format.keep_with_next = True
                picture_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

                caption = document.add_paragraph()
                caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
                caption.add_run(f"Photo {photo_number}: ").bold = True
                caption.add_run(label).italic = True
                caption.paragraph_format.space_after = Pt(8)

    # ---- Basis of the report and sign-off
    document.add_heading("Basis of this Report", level=1)

    basis = document.add_paragraph(
        "Report generated from saved site observation records. "
        "Photographs show conditions at the time they were taken and do "
        "not by themselves demonstrate compliance or completion of "
        "corrective work. Information marked Contractor-reported was "
        "provided by the contractor and was not directly observed by the "
        "preparer. An observation is shown as Closed only where "
        "verification notes have been recorded."
    )
    basis.paragraph_format.keep_with_next = True
    basis.paragraph_format.space_after = Pt(10)

    signoff = document.add_table(rows=3, cols=4)
    signoff.style = "Table Grid"
    signoff.alignment = WD_TABLE_ALIGNMENT.CENTER
    signoff.autofit = False
    for column, inches in zip(signoff.columns, (1.3, 2.4, 2.0, 1.2)):
        column.width = Inches(inches)
        for cell in column.cells:
            cell.width = Inches(inches)

    for index, heading in enumerate(["", "Name", "Signature", "Date"]):
        _shade(signoff.rows[0].cells[index], HEADER_SHADING)
        _write_cell(
            signoff.rows[0].cells[index],
            heading,
            bold=True,
            colour=RGBColor(0xFF, 0xFF, 0xFF),
        )

    for row_index, (role, name) in enumerate(
        [("Prepared by", prepared_by), ("Checked by", checked_by)],
        start=1,
    ):
        cells = signoff.rows[row_index].cells
        _shade(cells[0], LABEL_SHADING)
        _write_cell(cells[0], role, bold=True)
        _write_cell(cells[1], name.strip())
        _write_cell(cells[2], "")
        _write_cell(cells[3], "")
        # Give the signature space.
        row_properties = signoff.rows[row_index]._tr.get_or_add_trPr()
        height = OxmlElement("w:trHeight")
        height.set(qn("w:val"), "620")
        row_properties.append(height)

    _keep_table_together(signoff)

    document.save(output_path)
