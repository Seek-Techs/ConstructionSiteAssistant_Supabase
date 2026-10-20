
from datetime import date

from action_tracking import get_overdue_observations
from observation_model import SiteObservation


def make_observation(
    observation_id: str,
    due_date: str,
    status: str = "Open",
) -> SiteObservation:
    return SiteObservation(
        observation_id=observation_id,
        report_date="2026-10-15",
        site="South Drainage",
        location="E8, Chainage 0+360",
        contractor="Sample Contractor",
        category="HSE",
        information_source="Direct observation",
        description="Edge protection was not provided.",
        required_action="Provide suitable edge protection.",
        responsible_party="Contractor",
        status=status,
        due_date=due_date,
    )


def test_overdue_open_observation_is_identified():
    observation = make_observation("OBS-0001", "2026-10-19")

    result = get_overdue_observations(
        [observation],
        today=date(2026, 10, 20),
    )

    assert result == [observation]


def test_action_due_today_is_not_overdue():
    observation = make_observation("OBS-0002", "2026-10-20")

    result = get_overdue_observations(
        [observation],
        today=date(2026, 10, 20),
    )

    assert result == []


def test_closed_observation_is_not_overdue():
    observation = make_observation(
        "OBS-0003",
        "2026-10-19",
        status="Closed",
    )

    result = get_overdue_observations(
        [observation],
        today=date(2026, 10, 20),
    )

    assert result == []


def test_observation_without_due_date_is_not_overdue():
    observation = make_observation("OBS-0004", "")

    result = get_overdue_observations(
        [observation],
        today=date(2026, 10, 20),
    )

    assert result == []
