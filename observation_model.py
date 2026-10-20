
from dataclasses import dataclass
from datetime import date


@dataclass
class SiteObservation:
    observation_id: str
    report_date: str
    site: str
    location: str
    contractor: str
    category: str
    information_source: str
    description: str
    required_action: str
    responsible_party: str
    status: str = "Open"
    verification_notes: str = ""
    due_date: str = ""
    project_code: str = ""



def validate_observation(observation: SiteObservation) -> list[str]:
    """Return a list of problems found in an observation."""
    errors = []

    required_fields = {
        "Observation ID": observation.observation_id,
        "Site": observation.site,
        "Location": observation.location,
        "Contractor": observation.contractor,
        "Description": observation.description,
        "Required action": observation.required_action,
        "Responsible party": observation.responsible_party,
    }

    for field_name, value in required_fields.items():
        if not value.strip():
            errors.append(f"{field_name} is required")

    try:
        date.fromisoformat(observation.report_date)
    except (ValueError, TypeError):
        errors.append("Report date must use YYYY-MM-DD format")

    if observation.due_date:
        try:
            parsed_due_date = date.fromisoformat(observation.due_date)

            if parsed_due_date.isoformat() != observation.due_date:
                errors.append("Due date must use YYYY-MM-DD format")

        except (ValueError, TypeError):
            errors.append("Due date must use YYYY-MM-DD format")

    allowed_categories = {"Quality", "HSE", "Traffic", "Other"}
    if observation.category not in allowed_categories:
        errors.append("Category must be Quality, HSE, Traffic or Other")

    allowed_sources = {
        "Direct observation",
        "Contractor-reported",
    }
    if observation.information_source not in allowed_sources:
        errors.append(
            "Information source must be Direct observation "
            "or Contractor-reported"
        )

    allowed_statuses = {"Open", "In Progress", "Closed"}
    if observation.status not in allowed_statuses:
        errors.append("Status must be Open, In Progress or Closed")
    
    if observation.status == "Closed" and not observation.verification_notes.strip():
        errors.append(
            "Verification notes are required before closing an observation"
        )

    return errors
