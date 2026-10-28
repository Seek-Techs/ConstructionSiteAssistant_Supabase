"""Owner-scoped data access for the cloud application."""


def list_owned_projects(client, *, owner_id: str) -> list[dict]:
    """Return projects belonging to one authenticated user."""
    response = (
        client.table("projects")
        .select("id, project_code, project_name, location, created_at")
        .eq("owner_id", owner_id)
        .order("project_name")
        .execute()
    )

    return response.data or []


def list_owned_observations(
    client,
    *,
    owner_id: str,
    project_id: str | None = None,
) -> list[dict]:
    """Return observations belonging to one user, optionally by project."""
    query = (
        client.table("observations")
        .select(
            "observation_id, project_id, report_date, site, location, "
            "contractor, category, information_source, description, "
            "required_action, responsible_party, status, created_at"
        )
        .eq("owner_id", owner_id)
    )

    if project_id is not None:
        query = query.eq("project_id", project_id)

    response = query.order("report_date", desc=True).execute()

    return response.data or []

def create_project(
    client,
    *,
    owner_id: str,
    project_code: str,
    project_name: str,
    location: str,
) -> dict:
    """Create a project for the authenticated owner's workspace."""
    owner_id = owner_id.strip()
    project_code = project_code.strip()
    project_name = project_name.strip()
    location = location.strip()

    if not owner_id:
        raise ValueError("A valid owner is required.")
    if not project_code:
        raise ValueError("Project code is required.")
    if not project_name:
        raise ValueError("Project name is required.")
    if not location:
        raise ValueError("Project location is required.")

    response = (
        client.table("projects")
        .insert(
            {
                "owner_id": owner_id,
                "project_code": project_code,
                "project_name": project_name,
                "location": location,
            }
        )
        .select("id, project_code, project_name, location, created_at")
        .execute()
    )

    records = response.data or []
    if isinstance(records, dict):
        return records
    if not records:
        raise RuntimeError(
            "The project insert returned no record. "
            "Check the database response and permissions."
        )

    return records[0]


def create_observation(
    client,
    *,
    owner_id: str,
    report_date: str,
    site: str,
    location: str,
    contractor: str,
    category: str,
    information_source: str,
    description: str,
    required_action: str,
    responsible_party: str,
    project_id: str | None = None,
    due_date: str | None = None,
    status: str = "Open",
    verification_notes: str | None = None,
) -> dict:
    """Validate and create an observation in the owner's workspace."""
    from datetime import date

    owner_id = owner_id.strip()

    if not owner_id:
        raise ValueError("A valid owner is required.")

    required_fields = {
        "Site": site,
        "Location": location,
        "Contractor": contractor,
        "Description": description,
        "Required action": required_action,
        "Responsible party": responsible_party,
    }

    for label, value in required_fields.items():
        if not value.strip():
            raise ValueError(f"{label} is required.")

    try:
        parsed_date = date.fromisoformat(report_date)
        if parsed_date.isoformat() != report_date:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError(
            "Report date must use YYYY-MM-DD format."
        ) from None

    if due_date:
        try:
            parsed_due_date = date.fromisoformat(due_date)
            if parsed_due_date.isoformat() != due_date:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError(
                "Due date must use YYYY-MM-DD format."
            ) from None

    if category not in {"Quality", "HSE", "Traffic", "Other"}:
        raise ValueError(
            "Category must be Quality, HSE, Traffic or Other."
        )

    if information_source not in {
        "Direct observation",
        "Contractor-reported",
    }:
        raise ValueError(
            "Information source must be Direct observation "
            "or Contractor-reported."
        )

    if status not in {"Open", "In Progress", "Closed"}:
        raise ValueError(
            "Status must be Open, In Progress or Closed."
        )

    verification_notes = (verification_notes or "").strip()

    if status == "Closed" and not verification_notes:
        raise ValueError(
            "Verification notes are required before closing "
            "an observation."
        )

    existing = list_owned_observations(
        client,
        owner_id=owner_id,
    )

    highest_number = 0

    for observation in existing:
        try:
            number = int(
                observation["observation_id"].removeprefix("OBS-")
            )
            highest_number = max(highest_number, number)
        except (ValueError, KeyError, TypeError):
            continue

    record = {
        "observation_id": f"OBS-{highest_number + 1:04d}",
        "owner_id": owner_id,
        "report_date": report_date,
        "site": site.strip(),
        "location": location.strip(),
        "contractor": contractor.strip(),
        "category": category,
        "information_source": information_source,
        "description": description.strip(),
        "required_action": required_action.strip(),
        "responsible_party": responsible_party.strip(),
        "status": status,
        "verification_notes": verification_notes or None,
        "due_date": due_date or None,
        "project_id": project_id or None,
    }

    response = (
        client.table("observations")
        .insert(record)
        .select(
            "observation_id, project_id, report_date, site, location, "
            "contractor, category, information_source, description, "
            "required_action, responsible_party, status, "
            "verification_notes, due_date, created_at"
        )
        .execute()
    )

    records = response.data or []

    if isinstance(records, dict):
        return records

    if not records:
        raise RuntimeError(
            "The observation insert returned no record. "
            "Check the database response and permissions."
        )

    return records[0]
