from unittest.mock import MagicMock

from cloud_data_service import (
    create_observation,
    list_owned_observations,
    list_owned_projects,
)


OWNER_ID = "5e550458-8f82-4536-8b7d-6dee0e981f17"
PROJECT_ID = "223e4567-e89b-12d3-a456-426614174000"


def make_client():
    return MagicMock()


def test_list_owned_projects_filters_by_owner_and_orders_by_name():
    client = make_client()
    table = client.table.return_value
    records = [{"id": PROJECT_ID, "project_name": "Drainage Project"}]

    (
        table.select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value.data
    ) = records

    result = list_owned_projects(client, owner_id=OWNER_ID)

    assert result == records
    client.table.assert_called_once_with("projects")
    table.select.assert_called_once_with(
        "id, project_code, project_name, location, created_at"
    )
    table.select.return_value.eq.assert_called_once_with(
        "owner_id", OWNER_ID
    )
    table.select.return_value.eq.return_value.order.assert_called_once_with(
        "project_name"
    )


def test_list_owned_observations_filters_by_owner():
    client = make_client()
    table = client.table.return_value
    records = [{"observation_id": "OBS-001", "project_id": PROJECT_ID}]

    (
        table.select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value.data
    ) = records

    result = list_owned_observations(client, owner_id=OWNER_ID)

    assert result == records
    client.table.assert_called_once_with("observations")
    table.select.return_value.eq.assert_called_once_with(
        "owner_id", OWNER_ID
    )
    table.select.return_value.eq.return_value.order.assert_called_once_with(
        "report_date", desc=True
    )


def test_list_owned_observations_can_filter_by_project():
    client = make_client()
    table = client.table.return_value

    (
        table.select.return_value
        .eq.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value.data
    ) = []

    result = list_owned_observations(
        client,
        owner_id=OWNER_ID,
        project_id=PROJECT_ID,
    )

    assert result == []
    table.select.return_value.eq.assert_called_once_with(
        "owner_id", OWNER_ID
    )
    (
        table.select.return_value.eq.return_value
        .eq.assert_called_once_with("project_id", PROJECT_ID)
    )


def test_empty_results_return_empty_lists():
    client = make_client()

    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = None

    assert list_owned_projects(client, owner_id=OWNER_ID) == []

    client.reset_mock()
    client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = None

    assert list_owned_observations(client, owner_id=OWNER_ID) == []

def test_create_project_inserts_trimmed_fields_for_owner():
    from cloud_data_service import create_project

    client = make_client()
    table = client.table.return_value
    expected = {
        "id": PROJECT_ID,
        "project_code": "DR-001",
        "project_name": "Drainage Project",
        "location": "Lagos",
        "created_at": "2026-10-28T10:00:00Z",
    }

    (
        table.insert.return_value
        .select.return_value
        .execute.return_value.data
    ) = [expected]

    result = create_project(
        client,
        owner_id=OWNER_ID,
        project_code=" DR-001 ",
        project_name=" Drainage Project ",
        location=" Lagos ",
    )

    assert result == expected
    client.table.assert_called_once_with("projects")
    table.insert.assert_called_once_with(
        {
            "owner_id": OWNER_ID,
            "project_code": "DR-001",
            "project_name": "Drainage Project",
            "location": "Lagos",
        }
    )


def test_create_project_rejects_blank_required_fields():
    from cloud_data_service import create_project

    client = make_client()

    for field, values in [
        ("project_code", {"project_code": "  "}),
        ("project_name", {"project_name": "  "}),
        ("location", {"location": "  "}),
    ]:
        arguments = {
            "owner_id": OWNER_ID,
            "project_code": "DR-001",
            "project_name": "Drainage Project",
            "location": "Lagos",
        }
        arguments.update(values)

        try:
            create_project(client, **arguments)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Blank {field} should be rejected.")

    client.table.assert_not_called()


def test_create_project_rejects_blank_owner():
    from cloud_data_service import create_project

    client = make_client()

    try:
        create_project(
            client,
            owner_id=" ",
            project_code="DR-001",
            project_name="Drainage Project",
            location="Lagos",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Blank owner should be rejected.")

    client.table.assert_not_called()


from datetime import date


def valid_observation_arguments():
    """Return valid input data for observation-creation tests."""
    return {
        "owner_id": OWNER_ID,
        "report_date": "2026-10-28",
        "site": "E8",
        "location": "0+360",
        "contractor": "SinoSky International Nig. FZE",
        "category": "Quality",
        "information_source": "Direct observation",
        "description": "Base slab thickness requires verification.",
        "required_action": "Verify the slab thickness against the approved drawings.",
        "responsible_party": "Site Contractor",
        "project_id": PROJECT_ID,
        "due_date": "2026-10-30",
    }


def configure_observation_insert(client, records):
    """Configure the mocked Supabase insert response."""
    (
        client.table.return_value
        .insert.return_value
        .select.return_value
        .execute.return_value.data
    ) = records


def test_create_observation_inserts_trimmed_fields_for_owner():
    client = make_client()
    table = client.table.return_value

    # No existing observations: the first ID should be OBS-0001.
    (
        table.select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value.data
    ) = []

    expected = {
        "observation_id": "OBS-0001",
        "project_id": PROJECT_ID,
        "report_date": "2026-10-28",
        "site": "E8",
        "location": "0+360",
        "contractor": "SinoSky International Nig. FZE",
        "category": "Quality",
        "information_source": "Direct observation",
        "description": "Base slab thickness requires verification.",
        "required_action": (
            "Verify the slab thickness against the approved drawings."
        ),
        "responsible_party": "Site Contractor",
        "status": "Open",
        "verification_notes": None,
        "due_date": "2026-10-30",
        "created_at": "2026-10-28T10:00:00Z",
    }
    configure_observation_insert(client, [expected])

    arguments = valid_observation_arguments()
    arguments["site"] = " E8 "
    arguments["location"] = " 0+360 "
    arguments["contractor"] = " SinoSky International Nig. FZE "

    result = create_observation(client, **arguments)

    assert result == expected
    table.insert.assert_called_once_with(
        {
            "observation_id": "OBS-0001",
            "owner_id": OWNER_ID,
            "report_date": "2026-10-28",
            "site": "E8",
            "location": "0+360",
            "contractor": "SinoSky International Nig. FZE",
            "category": "Quality",
            "information_source": "Direct observation",
            "description": (
                "Base slab thickness requires verification."
            ),
            "required_action": (
                "Verify the slab thickness against the approved drawings."
            ),
            "responsible_party": "Site Contractor",
            "status": "Open",
            "verification_notes": None,
            "due_date": "2026-10-30",
            "project_id": PROJECT_ID,
        }
    )


def test_create_observation_generates_next_sequential_id():
    client = make_client()

    (
        client.table.return_value.select.return_value
        .eq.return_value.order.return_value.execute.return_value.data
    ) = [
        {"observation_id": "OBS-0001"},
        {"observation_id": "OBS-0004"},
        {"observation_id": "OTHER-ID"},
    ]

    configure_observation_insert(
        client,
        [{"observation_id": "OBS-0005"}],
    )

    result = create_observation(
        client,
        **valid_observation_arguments(),
    )

    assert result["observation_id"] == "OBS-0005"


def test_create_observation_rejects_blank_owner():
    client = make_client()
    arguments = valid_observation_arguments()
    arguments["owner_id"] = " "

    try:
        create_observation(client, **arguments)
    except ValueError as error:
        assert "owner" in str(error).lower()
    else:
        raise AssertionError("Blank owner should be rejected.")

    client.table.assert_not_called()


def test_create_observation_rejects_blank_required_fields():
    required_fields = [
        "site",
        "location",
        "contractor",
        "description",
        "required_action",
        "responsible_party",
    ]

    for field in required_fields:
        client = make_client()
        arguments = valid_observation_arguments()
        arguments[field] = "  "

        try:
            create_observation(client, **arguments)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"Blank {field} should be rejected."
            )

        client.table.assert_not_called()


def test_create_observation_rejects_invalid_dates():
    for field, invalid_value in [
        ("report_date", "28-10-2026"),
        ("report_date", "not-a-date"),
        ("due_date", "30-10-2026"),
    ]:
        client = make_client()
        arguments = valid_observation_arguments()
        arguments[field] = invalid_value

        try:
            create_observation(client, **arguments)
        except ValueError as error:
            assert "date" in str(error).lower()
        else:
            raise AssertionError(
                f"Invalid {field} should be rejected."
            )

        client.table.assert_not_called()


def test_create_observation_rejects_invalid_category_and_source():
    invalid_cases = [
        ("category", "Progress"),
        ("information_source", "Unknown source"),
    ]

    for field, invalid_value in invalid_cases:
        client = make_client()
        arguments = valid_observation_arguments()
        arguments[field] = invalid_value

        try:
            create_observation(client, **arguments)
        except ValueError:
            pass
        else:
            raise AssertionError(
                f"Invalid {field} should be rejected."
            )

        client.table.assert_not_called()


def test_create_observation_requires_notes_when_closed():
    client = make_client()
    arguments = valid_observation_arguments()
    arguments["status"] = "Closed"

    try:
        create_observation(client, **arguments)
    except ValueError as error:
        assert "verification notes" in str(error).lower()
    else:
        raise AssertionError(
            "Closing an observation without verification notes "
            "should be rejected."
        )

    client.table.assert_not_called()


def test_create_observation_accepts_closed_with_verification_notes():
    client = make_client()

    (
        client.table.return_value.select.return_value
        .eq.return_value.order.return_value.execute.return_value.data
    ) = []

    configure_observation_insert(
        client,
        [{
            "observation_id": "OBS-0001",
            "status": "Closed",
            "verification_notes": "Compliance verified on site.",
        }],
    )

    arguments = valid_observation_arguments()
    arguments["status"] = "Closed"
    arguments["verification_notes"] = " Compliance verified on site. "

    result = create_observation(client, **arguments)

    assert result["observation_id"] == "OBS-0001"
    client.table.return_value.insert.assert_called_once()
    inserted_record = (
        client.table.return_value.insert.call_args.args[0]
    )
    assert inserted_record["status"] == "Closed"
    assert (
        inserted_record["verification_notes"]
        == "Compliance verified on site."
    )


def test_create_observation_rejects_invalid_status():
    client = make_client()
    arguments = valid_observation_arguments()
    arguments["status"] = "Pending"

    try:
        create_observation(client, **arguments)
    except ValueError as error:
        assert "status" in str(error).lower()
    else:
        raise AssertionError("Invalid status should be rejected.")

    client.table.assert_not_called()
