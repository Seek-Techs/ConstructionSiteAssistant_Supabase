
import pytest
import sqlite3

from observation_model import SiteObservation
from storage import (
    initialize_database,
    save_observation,
    get_observations,
    next_observation_id,
    update_observation_status,
    update_observation,
    save_project,
    get_projects,
)


def make_observation(observation_id="OBS-0001"):
    return SiteObservation(
        observation_id=observation_id,
        report_date="2026-10-16",
        site="Test Site",
        location="E2",
        contractor="Sample Contractor",
        category="Quality",
        information_source="Direct observation",
        description="Debris was observed in the work area.",
        required_action="Remove the debris.",
        responsible_party="Contractor",
    )


def test_observation_status_and_notes_are_saved(tmp_path):
    db_path = tmp_path / "test_observations.db"
    save_observation(make_observation(), db_path)

    update_observation_status(
        "OBS-0001",
        "In Progress",
        "Contractor has started removing the debris.",
        db_path,
    )

    updated = get_observations(db_path)[0]

    assert updated.status == "In Progress"
    assert updated.verification_notes == (
        "Contractor has started removing the debris."
    )


def test_observation_cannot_be_closed_without_verification(tmp_path):
    db_path = tmp_path / "test_observations.db"
    save_observation(make_observation(), db_path)

    with pytest.raises(ValueError, match="Verification notes are required"):
        update_observation_status(
            "OBS-0001",
            "Closed",
            "",
            db_path,
        )

    unchanged = get_observations(db_path)[0]
    assert unchanged.status == "Open"


def test_edit_observation_updates_details_and_preserves_status_and_notes(
    tmp_path,
):
    db_path = tmp_path / "observations.db"

    original = make_observation()
    original.status = "Closed"
    original.verification_notes = "Follow-up inspection completed."

    save_observation(original, db_path)

    edited = SiteObservation(
        observation_id=original.observation_id,
        report_date="2026-10-16",
        site="Updated Drainage Project",
        location="E8, Chainage 0+400",
        contractor="Updated Contractor Ltd.",
        category="Quality",
        information_source="Direct observation",
        description="Corrected observation description.",
        required_action="Verify the corrected work.",
        responsible_party="Contractor",
        status="Open",
        verification_notes="",
    )

    update_observation(edited, db_path)

    saved = get_observations(db_path)[0]

    assert saved.observation_id == original.observation_id
    assert saved.site == "Updated Drainage Project"
    assert saved.location == "E8, Chainage 0+400"
    assert saved.description == "Corrected observation description."
    assert saved.status == "Closed"
    assert saved.verification_notes == (
        "Follow-up inspection completed."
    )


def test_edit_observation_rejects_unknown_id(tmp_path):
    db_path = tmp_path / "observations.db"

    edited = make_observation("OBS-9999")

    with pytest.raises(ValueError, match="Observation not found"):
        update_observation(edited, db_path)


def test_save_and_retrieve_observation_due_date(tmp_path):
    db_path = tmp_path / "observations.db"
    observation = make_observation()
    observation.due_date = "2026-10-20"

    save_observation(observation, db_path)

    saved = get_observations(db_path)[0]

    assert saved.due_date == "2026-10-20"


def test_edit_observation_updates_due_date(tmp_path):
    db_path = tmp_path / "observations.db"
    observation = make_observation()
    observation.due_date = "2026-10-20"

    save_observation(observation, db_path)

    observation.due_date = "2026-10-25"
    update_observation(observation, db_path)

    saved = get_observations(db_path)[0]

    assert saved.due_date == "2026-10-25"

def test_project_table_is_created(tmp_path):
    db_path = tmp_path / "test_observations.db"

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        columns = connection.execute(
            "PRAGMA table_info(projects)"
        ).fetchall()

    column_names = [column[1] for column in columns]

    assert column_names == [
        "project_code",
        "project_name",
        "location",
    ]


def test_project_can_be_saved_and_retrieved(tmp_path):
    db_path = tmp_path / "test_observations.db"

    save_project(
        "LFZ-P001",
        "South Drainage Construction",
        "E8, N4-N5",
        db_path,
    )

    projects = get_projects(db_path)

    assert len(projects) == 1
    assert projects[0] == {
        "project_code": "LFZ-P001",
        "project_name": "South Drainage Construction",
        "location": "E8, N4-N5",
    }


def test_project_fields_are_trimmed(tmp_path):
    db_path = tmp_path / "test_observations.db"

    save_project(
        " LFZ-P001 ",
        " South Drainage Construction ",
        " E8, N4-N5 ",
        db_path,
    )

    projects = get_projects(db_path)

    assert projects[0]["project_code"] == "LFZ-P001"
    assert projects[0]["project_name"] == "South Drainage Construction"
    assert projects[0]["location"] == "E8, N4-N5"


def test_project_requires_all_fields(tmp_path):
    db_path = tmp_path / "test_observations.db"

    try:
        save_project(
            "LFZ-P001",
            "",
            "E8, N4-N5",
            db_path,
        )
    except ValueError as error:
        assert str(error) == (
            "Project code, project name and location are required."
        )
    else:
        assert False, "Expected ValueError for a missing project name"


def test_duplicate_project_code_is_rejected(tmp_path):
    db_path = tmp_path / "test_observations.db"

    save_project(
        "LFZ-P001",
        "South Drainage Construction",
        "E8, N4-N5",
        db_path,
    )

    try:
        save_project(
            "LFZ-P001",
            "North Drainage Construction",
            "N4-N5",
            db_path,
        )
    except sqlite3.IntegrityError:
        pass
    else:
        assert False, "Expected duplicate project code to be rejected"

    projects = get_projects(db_path)
    assert len(projects) == 1
    assert projects[0]["project_name"] == "South Drainage Construction"
