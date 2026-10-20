
from datetime import date

from observation_model import SiteObservation


def get_overdue_observations(
    observations: list[SiteObservation],
    today: date | None = None,
) -> list[SiteObservation]:
    """Return outstanding observations whose due dates have passed."""
    if today is None:
        today = date.today()

    overdue = []

    for observation in observations:
        if observation.status not in {"Open", "In Progress"}:
            continue

        if not observation.due_date:
            continue

        due_date = date.fromisoformat(observation.due_date)

        if due_date < today:
            overdue.append(observation)

    return overdue
