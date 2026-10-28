"""Tests for the preview-only historical WhatsApp import analysis."""

import io
import zipfile
from datetime import date

import pytest

import historical_import
from historical_import import (
    KIND_ACK,
    KIND_FOLLOW_UP,
    KIND_MEDIA,
    KIND_OBSERVATION,
    KIND_PROGRESS,
    KIND_SYSTEM,
    analyze_export,
    classify_text,
    extract_chat_text,
    find_report_date,
)


SAMPLE = """Messages and calls are end-to-end encrypted.
[8/4/26, 11:24:33 AM] - Engr. Bayonle added You
[8/11/26, 6:39:00 PM] You: <image omitted> Acme Works Nig. Ltd
Project: Drainage
Location: E8 (N4-N5) South Drainage

Site Observation

* Poor reinforcement binding observed.
* Poor housekeeping around the work area, with debris and timber.
* Excavation is ongoing as planned.

Outstanding Actions

* Improve reinforcement fixing.
[8/11/26, 6:40:10 PM] You: <image omitted>
[8/11/26, 9:02:00 PM] Engr. Biola: Noted sir
[8/12/26, 8:00:00 AM] You: Acme Works Nig. Ltd
Date: 12/08/2026
Contractor reported that the previously observed reinforcement binding defect had been corrected. Verification is pending.
[8/12/26, 9:00:00 AM] Engr. Biola: Work plan for today: excavation of drain, manpower 5 persons, ongoing sand spreading.
[8/12/26, 9:05:00 AM] Engr. Biola: This message was deleted
"""


def test_classification_of_basic_message_types():
    assert classify_text(None, "Someone added you")[0] == KIND_SYSTEM
    assert classify_text("A", "This message was deleted")[0] == KIND_SYSTEM
    assert classify_text("A", "<image omitted>")[0] == KIND_MEDIA
    assert classify_text("A", "Noted sir")[0] == KIND_ACK
    assert classify_text("A", "ok")[0] == KIND_ACK


def test_progress_is_not_mistaken_for_an_observation():
    kind, _, _ = classify_text(
        "A",
        "Work plan for today: excavation of drain, manpower 5 persons, "
        "ongoing sand spreading at the site.",
    )
    assert kind == KIND_PROGRESS


def test_neutral_observed_wording_is_not_a_defect():
    kind, reasons, _ = classify_text(
        "A",
        "While passing the road, ongoing works by the contractor were "
        "observed and photographs were taken for record purposes only.",
    )
    assert kind == KIND_PROGRESS
    assert any("without a defect" in reason for reason in reasons)


def test_future_follow_up_plan_is_not_a_rectification_report():
    kind, _, _ = classify_text(
        "A",
        "Outstanding Actions: follow-up inspection to verify corrective "
        "actions before further progression of the affected works. "
        "Rectification of the invert-level difference.",
    )
    assert kind != KIND_FOLLOW_UP


def test_report_with_several_findings_is_split_and_traceable():
    preview = analyze_export(SAMPLE)

    observed = [
        c for c in preview.candidates if c.message_source_line == 3
    ]
    texts = [c.finding_text for c in observed]

    assert len(observed) == 2
    assert texts[0] == "Poor reinforcement binding observed."
    assert texts[1].startswith("Poor housekeeping")
    assert all(c.kind == KIND_OBSERVATION for c in observed)

    # Source lines point at the exact bullet in the export.
    lines = SAMPLE.splitlines()
    for candidate in observed:
        assert candidate.finding_text in lines[candidate.finding_source_line - 1]

    # Neutral bullet is not proposed; actions are copied verbatim.
    assert not any("ongoing as planned" in t for t in texts)
    assert observed[0].message_actions == ("Improve reinforcement fixing.",)


def test_fields_are_copied_from_text_or_left_blank():
    preview = analyze_export(SAMPLE)
    first = preview.candidates[0]

    assert first.contractor == "Acme Works Nig. Ltd"
    assert first.location == "E8 (N4-N5) South Drainage"
    assert first.status == "Open"
    assert first.information_source is None
    assert first.report_date == date(2026, 8, 11)
    assert first.original_message_text.startswith("<image omitted>")
    assert first.sender == "You"


def test_nothing_is_ever_proposed_as_closed():
    preview = analyze_export(SAMPLE)
    assert preview.candidates
    assert {c.status for c in preview.candidates} == {"Open"}


def test_follow_up_is_separated_and_linked_only_as_a_suggestion():
    preview = analyze_export(SAMPLE)
    follow_ups = [
        c for c in preview.candidates if c.kind == KIND_FOLLOW_UP
    ]

    assert len(follow_ups) == 1
    follow_up = follow_ups[0]
    assert follow_up.status == "Open"
    assert follow_up.report_date == date(2026, 8, 12)
    # Suggested link points at an earlier finding line, nothing more.
    assert follow_up.possible_links
    assert all(line < follow_up.message_source_line
               for line in follow_up.possible_links)


def test_report_date_parsing_is_day_first_and_flags_differences():
    same, note = find_report_date("Date: 12/08/2026", date(2026, 8, 12))
    assert same == date(2026, 8, 12) and note is None

    near, note = find_report_date("Date: 11/08/2026", date(2026, 8, 12))
    assert near == date(2026, 8, 11) and "differs" in note

    far, note = find_report_date("Date: 01/01/2026", date(2026, 8, 12))
    assert far == date(2026, 8, 12) and "check" in note.lower()

    none, note = find_report_date("No date here", date(2026, 8, 12))
    assert none == date(2026, 8, 12) and note is None


def test_date_and_sender_filters_apply():
    only_biola = analyze_export(SAMPLE, senders={"Engr. Biola"})
    assert {m.sender for m in only_biola.messages} == {"Engr. Biola"}
    assert only_biola.candidates == []

    one_day = analyze_export(
        SAMPLE,
        start_date=date(2026, 8, 12),
        end_date=date(2026, 8, 12),
    )
    assert {m.timestamp.date() for m in one_day.messages} == {
        date(2026, 8, 12)
    }


def test_media_nearby_is_counted_but_never_invented():
    preview = analyze_export(SAMPLE)
    assert preview.candidates[0].media_count >= 1


def test_candidates_have_stable_unique_fingerprints():
    first = analyze_export(SAMPLE)
    second = analyze_export(SAMPLE)

    prints = [c.fingerprint for c in first.candidates]
    assert prints == [c.fingerprint for c in second.candidates]
    assert len(prints) == len(set(prints))


def test_empty_and_unrecognised_input_is_handled():
    preview = analyze_export("just some text\nwith no timestamps")
    assert preview.total_messages == 0
    assert preview.candidates == []


def test_zip_and_txt_uploads_are_read_in_memory():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("chat.txt", SAMPLE)
        archive.writestr("notes.md", "ignored")

    assert extract_chat_text("export.zip", buffer.getvalue()) == SAMPLE
    assert extract_chat_text("chat.txt", SAMPLE.encode()) == SAMPLE


def test_unsupported_or_oversized_uploads_are_rejected():
    with pytest.raises(ValueError):
        extract_chat_text("chat.pdf", b"x")

    with pytest.raises(ValueError):
        extract_chat_text("bad.zip", b"not a zip")

    empty = io.BytesIO()
    with zipfile.ZipFile(empty, "w") as archive:
        archive.writestr("image.png", b"x")
    with pytest.raises(ValueError):
        extract_chat_text("none.zip", empty.getvalue())

    with pytest.raises(ValueError):
        extract_chat_text(
            "big.txt", b"x" * (historical_import.MAX_UPLOAD_BYTES + 1)
        )


def test_preview_modules_cannot_reach_the_database():
    """The preview code must not import any persistence or cloud module."""
    import ast
    from pathlib import Path

    forbidden = {
        "supabase",
        "cloud_data_service",
        "evidence_service",
        "auth_helpers",
        "storage",
        "digest_storage",
        "sqlite3",
        "requests",
        "httpx",
    }
    root = Path(historical_import.__file__).parent

    for filename in ("historical_import.py", "historical_import_ui.py"):
        tree = ast.parse((root / filename).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not (imported & forbidden), (filename, imported & forbidden)
