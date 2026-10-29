"""Smoke tests for the preview-only import screen."""

from historical_import import analyze_export
from historical_import_ui import candidate_rows, message_rows

from test_historical_import import SAMPLE


def test_rows_preserve_verbatim_text_and_mark_blank_fields():
    preview = analyze_export(SAMPLE)
    rows = candidate_rows(preview.candidates)

    assert rows
    first = rows[0]
    assert first["Finding (verbatim)"] == (
        "Poor reinforcement binding observed."
    )
    assert first["Source"] == "— choose in review —"
    assert first["Contractor"] == "Acme Works Nig. Ltd"
    assert isinstance(first["Source line"], int)


def test_message_rows_show_classification_reasons():
    preview = analyze_export(SAMPLE)
    rows = message_rows(preview)

    assert len(rows) == len(preview.messages)
    assert all(row["Why"] for row in rows)
    assert {"Line", "Time", "Sender", "Classified as", "Text"} <= set(rows[0])


def test_screen_runs_without_an_upload():
    from streamlit.testing.v1 import AppTest

    script = (
        "from historical_import_ui import "
        "render_historical_import_preview\n"
        "render_historical_import_preview()\n"
    )
    app = AppTest.from_string(script).run()

    assert not app.exception
    assert any("preview only" in s.value.lower() for s in app.subheader)
    assert any("Nothing on this screen is saved" in i.value for i in app.info)
