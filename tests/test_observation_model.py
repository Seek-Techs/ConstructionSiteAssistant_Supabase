from observation_model import SiteObservation, validate_observation


def test_valid_observation_has_no_errors():
    observation = SiteObservation(
        observation_id="OBS-0001",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
    )

    assert validate_observation(observation) == []


def test_invalid_category_is_rejected():
    observation = SiteObservation(
        observation_id="OBS-0002",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="Safety",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
    )

    errors = validate_observation(observation)

    assert "Category must be Quality, HSE, Traffic or Other" in errors


def test_impossible_date_is_rejected():
    observation = SiteObservation(
        observation_id="OBS-0003",
        report_date="2026-02-30",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Standing water was observed.",
        required_action="Assess and address the standing water.",
        responsible_party="Contractor",
    )

    errors = validate_observation(observation)

    assert "Report date must use YYYY-MM-DD format" in errors


def test_closed_observation_requires_verification_notes():
    observation = SiteObservation(
        observation_id="OBS-0004",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
        status="Closed",
        verification_notes="",
    )

    errors = validate_observation(observation)

    assert (
        "Verification notes are required before closing an observation"
        in errors
    )


def test_closed_observation_with_verification_notes_is_valid():
    observation = SiteObservation(
        observation_id="OBS-0005",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
        status="Closed",
        verification_notes=(
            "Follow-up inspection confirmed that suitable "
            "edge protection was provided."
        ),
    )

    errors = validate_observation(observation)

    assert errors == []


from observation_model import SiteObservation
from storage import (
    initialize_database,
    save_observation,
    get_observations,
    next_observation_id,
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


def test_database_can_be_initialized(tmp_path):
    db_path = tmp_path / "test_observations.db"

    initialize_database(db_path)

    assert db_path.exists()


def test_saved_observation_can_be_retrieved(tmp_path):
    db_path = tmp_path / "test_observations.db"
    observation = make_observation()

    save_observation(observation, db_path)
    retrieved = get_observations(db_path)

    assert len(retrieved) == 1
    assert retrieved[0] == observation


def test_observation_id_increments(tmp_path):
    db_path = tmp_path / "test_observations.db"

    assert next_observation_id(db_path) == "OBS-0001"

    save_observation(make_observation(), db_path)

    assert next_observation_id(db_path) == "OBS-0002"

def test_empty_due_date_is_valid():
    observation = SiteObservation(
        observation_id="OBS-0006",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
        due_date="",
    )

    assert validate_observation(observation) == []


def test_valid_due_date_is_accepted():
    observation = SiteObservation(
        observation_id="OBS-0007",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
        due_date="2026-10-20",
    )

    assert validate_observation(observation) == []


def test_impossible_due_date_is_rejected():
    observation = SiteObservation(
        observation_id="OBS-0008",
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
        due_date="2026-02-30",
    )

    errors = validate_observation(observation)

    assert "Due date must use YYYY-MM-DD format" in errors