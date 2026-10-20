
from datetime import date

from observation_model import SiteObservation
from observation_filters import filter_observations


def make_observation(
    observation_id,
    report_date,
    contractor,
    category,
    status,
    description,
):
    return SiteObservation(
        observation_id=observation_id,
        report_date=report_date,
        site="Test Drainage Project",
        location="E8",
        contractor=contractor,
        category=category,
        information_source="Direct observation",
        description=description,
        required_action="Inspect and follow up",
        responsible_party="Contractor",
        status=status,
    )


def test_search_finds_description_case_insensitively():
    observations = [
        make_observation(
            "OBS-0001", "2026-10-15", "SinoSky",
            "Quality", "Open", "Check concrete thickness",
        ),
        make_observation(
            "OBS-0002", "2026-10-16", "Illary",
            "HSE", "Closed", "Improve housekeeping",
        ),
    ]

    results = filter_observations(
        observations,
        search_text="CONCRETE",
    )

    assert [item.observation_id for item in results] == ["OBS-0001"]


def test_filters_can_be_combined():
    observations = [
        make_observation(
            "OBS-0001", "2026-10-15", "SinoSky",
            "Quality", "Open", "Check alignment",
        ),
        make_observation(
            "OBS-0002", "2026-10-16", "SinoSky",
            "Quality", "Closed", "Alignment corrected",
        ),
        make_observation(
            "OBS-0003", "2026-10-16", "Illary",
            "HSE", "Open", "Check site access",
        ),
    ]

    results = filter_observations(
        observations,
        contractor="SinoSky",
        category="Quality",
        status="Open",
    )

    assert [item.observation_id for item in results] == ["OBS-0001"]


def test_date_range_includes_boundary_dates():
    observations = [
        make_observation(
            "OBS-0001", "2026-10-14", "SinoSky",
            "Quality", "Open", "First observation",
        ),
        make_observation(
            "OBS-0002", "2026-10-15", "SinoSky",
            "Quality", "Open", "Start date",
        ),
        make_observation(
            "OBS-0003", "2026-10-16", "SinoSky",
            "Quality", "Open", "End date",
        ),
    ]

    results = filter_observations(
        observations,
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 16),
    )

    assert [item.observation_id for item in results] == [
        "OBS-0002",
        "OBS-0003",
    ]


def test_no_matching_observations_returns_empty_list():
    observations = [
        make_observation(
            "OBS-0001", "2026-10-15", "SinoSky",
            "Quality", "Open", "Check alignment",
        ),
    ]

    results = filter_observations(
        observations,
        search_text="nonexistent",
    )

    assert results == []
