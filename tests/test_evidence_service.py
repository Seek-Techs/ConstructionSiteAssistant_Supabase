from unittest.mock import MagicMock

import pytest

from evidence_service import upload_evidence


OWNER_ID = "5e550458-8f82-4536-8b7d-6dee0e981f17"
EVIDENCE_ID = "123e4567-e89b-12d3-a456-426614174000"
PROJECT_ID = "223e4567-e89b-12d3-a456-426614174000"


def make_client():
    client = MagicMock()
    return client


def test_upload_inserts_metadata_before_uploading_file():
    client = make_client()
    file_bytes = b"sample photo data"

    result = upload_evidence(
        client,
        owner_id=OWNER_ID,
        evidence_id=EVIDENCE_ID,
        project_id=PROJECT_ID,
        observation_id=None,
        filename="Drainage Photo.jpg",
        mime_type="image/jpeg",
        file_bytes=file_bytes,
        caption="Drainage inspection",
        evidence_category="Quality",
    )

    table = client.table.return_value
    storage = client.storage.from_.return_value

    assert table.insert.call_count == 1
    assert storage.upload.call_count == 1

    payload = table.insert.call_args.args[0]
    expected_path = (
        f"{OWNER_ID}/{EVIDENCE_ID}/Drainage_Photo.jpg"
    )

    assert payload["owner_id"] == OWNER_ID
    assert payload["evidence_id"] == EVIDENCE_ID
    assert payload["project_id"] == PROJECT_ID
    assert payload["observation_id"] is None
    assert payload["object_path"] == expected_path
    assert payload["original_filename"] == "Drainage Photo.jpg"
    assert payload["mime_type"] == "image/jpeg"
    assert payload["file_size_bytes"] == len(file_bytes)
    assert payload["caption"] == "Drainage inspection"
    assert payload["evidence_category"] == "Quality"

    storage.upload.assert_called_once_with(
        expected_path,
        file_bytes,
        file_options={
            "content-type": "image/jpeg",
            "upsert": "false",
        },
    )

    assert result["object_path"] == expected_path


def test_upload_rejects_missing_or_multiple_parent_records():
    client = make_client()

    with pytest.raises(ValueError, match="exactly one"):
        upload_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
            project_id=None,
            observation_id=None,
            filename="photo.jpg",
            mime_type="image/jpeg",
            file_bytes=b"photo",
        )

    with pytest.raises(ValueError, match="exactly one"):
        upload_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
            project_id=PROJECT_ID,
            observation_id="observation-1",
            filename="photo.jpg",
            mime_type="image/jpeg",
            file_bytes=b"photo",
        )

    client.table.assert_not_called()
    client.storage.from_.assert_not_called()


def test_upload_rejects_unsupported_file_before_database_access():
    client = make_client()

    with pytest.raises(ValueError, match="Unsupported"):
        upload_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
            project_id=PROJECT_ID,
            observation_id=None,
            filename="program.exe",
            mime_type="application/x-msdownload",
            file_bytes=b"not allowed",
        )

    client.table.assert_not_called()
    client.storage.from_.assert_not_called()


def test_storage_failure_attempts_to_remove_inserted_metadata():
    client = make_client()
    table = client.table.return_value

    table.insert.return_value.execute.return_value.data = []
    table.delete.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
    client.storage.from_.return_value.upload.side_effect = RuntimeError(
        "Simulated storage failure"
    )

    with pytest.raises(RuntimeError, match="Simulated storage failure"):
        upload_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
            project_id=PROJECT_ID,
            observation_id=None,
            filename="Drainage Photo.jpg",
            mime_type="image/jpeg",
            file_bytes=b"photo bytes",
        )

    table.insert.assert_called_once()
    table.delete.assert_called_once()
    client.storage.from_.return_value.upload.assert_called_once()


def test_database_failure_does_not_attempt_storage_upload():
    client = make_client()
    client.table.return_value.insert.return_value.execute.side_effect = (
        RuntimeError("Simulated database failure")
    )

    with pytest.raises(RuntimeError, match="Simulated database failure"):
        upload_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
            project_id=PROJECT_ID,
            observation_id=None,
            filename="Drainage Photo.jpg",
            mime_type="image/jpeg",
            file_bytes=b"photo bytes",
        )

    client.storage.from_.assert_not_called()

def test_storage_cleanup_failure_preserves_metadata():
    client = make_client()
    table = client.table.return_value
    storage = client.storage.from_.return_value

    storage.upload.side_effect = RuntimeError("Simulated upload failure")
    storage.remove.side_effect = RuntimeError("Simulated cleanup failure")

    with pytest.raises(RuntimeError, match="Simulated upload failure"):
        upload_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
            project_id=PROJECT_ID,
            observation_id=None,
            filename="Drainage Photo.jpg",
            mime_type="image/jpeg",
            file_bytes=b"photo bytes",
        )

    storage.remove.assert_called_once_with(
        [f"{OWNER_ID}/{EVIDENCE_ID}/Drainage_Photo.jpg"]
    )
    table.delete.assert_not_called()

def test_delete_evidence_removes_storage_object_before_metadata():
    from evidence_service import delete_evidence

    client = make_client()
    table = client.table.return_value
    storage = client.storage.from_.return_value
    object_path = f"{OWNER_ID}/{EVIDENCE_ID}/Drainage_Photo.jpg"

    table.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "object_path": object_path
    }

    events = []
    storage.remove.side_effect = lambda paths: events.append("storage")
    table.delete.return_value.eq.return_value.eq.return_value.execute.side_effect = (
        lambda: events.append("metadata")
    )

    delete_evidence(
        client,
        owner_id=OWNER_ID,
        evidence_id=EVIDENCE_ID,
    )

    assert events == ["storage", "metadata"]
    storage.remove.assert_called_once_with([object_path])


def test_delete_evidence_keeps_metadata_if_storage_removal_fails():
    from evidence_service import delete_evidence

    client = make_client()
    table = client.table.return_value
    storage = client.storage.from_.return_value
    object_path = f"{OWNER_ID}/{EVIDENCE_ID}/Drainage_Photo.jpg"

    table.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = {
        "object_path": object_path
    }
    storage.remove.side_effect = RuntimeError("Simulated removal failure")

    with pytest.raises(RuntimeError, match="Simulated removal failure"):
        delete_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
        )

    table.delete.assert_not_called()


def test_delete_evidence_rejects_missing_record():
    from evidence_service import delete_evidence

    client = make_client()
    table = client.table.return_value
    table.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value.data = None

    with pytest.raises(ValueError, match="not found"):
        delete_evidence(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
        )

    client.storage.from_.assert_not_called()

def test_list_evidence_filters_by_owner_and_orders_newest_first():
    from evidence_service import list_evidence

    client = make_client()
    table = client.table.return_value
    records = [
        {"evidence_id": EVIDENCE_ID, "caption": "Drainage inspection"}
    ]

    (
        table.select.return_value
        .eq.return_value
        .order.return_value
        .execute.return_value.data
    ) = records

    result = list_evidence(client, owner_id=OWNER_ID)

    assert result == records
    client.table.assert_called_once_with("observation_evidence")
    table.select.return_value.eq.assert_called_once_with(
        "owner_id", OWNER_ID
    )
    table.select.return_value.eq.return_value.order.assert_called_once_with(
        "created_at", desc=True
    )


def test_update_evidence_metadata_changes_only_caption_and_category():
    from evidence_service import update_evidence_metadata

    client = make_client()
    table = client.table.return_value

    (
        table.update.return_value
        .eq.return_value
        .eq.return_value
        .select.return_value
        .execute.return_value.data
    ) = [{"evidence_id": EVIDENCE_ID}]

    result = update_evidence_metadata(
        client,
        owner_id=OWNER_ID,
        evidence_id=EVIDENCE_ID,
        caption="Verified drainage work",
        evidence_category="Quality",
    )

    assert result == [{"evidence_id": EVIDENCE_ID}]

    table.update.assert_called_once_with({
        "caption": "Verified drainage work",
        "evidence_category": "Quality",
    })

    table.update.return_value.eq.assert_called_once_with(
        "owner_id", OWNER_ID
    )
    (
        table.update.return_value.eq.return_value.eq
        .assert_called_once_with("evidence_id", EVIDENCE_ID)
    )


def test_get_evidence_signed_url_uses_owned_record_and_short_expiry():
    from evidence_service import get_evidence_signed_url

    client = make_client()
    table = client.table.return_value
    storage = client.storage.from_.return_value
    object_path = f"{OWNER_ID}/{EVIDENCE_ID}/Drainage_Photo.jpg"

    (
        table.select.return_value
        .eq.return_value
        .eq.return_value
        .maybe_single.return_value
        .execute.return_value.data
    ) = {"object_path": object_path}

    storage.create_signed_url.return_value = {
        "signedURL": "https://example.test/temporary-link"
    }

    result = get_evidence_signed_url(
        client,
        owner_id=OWNER_ID,
        evidence_id=EVIDENCE_ID,
    )

    assert result == "https://example.test/temporary-link"

    table.select.return_value.eq.assert_called_once_with(
        "owner_id", OWNER_ID
    )
    (
        table.select.return_value.eq.return_value.eq
        .assert_called_once_with("evidence_id", EVIDENCE_ID)
    )
    storage.create_signed_url.assert_called_once_with(object_path, 60)


def test_get_evidence_signed_url_rejects_missing_record():
    from evidence_service import get_evidence_signed_url

    client = make_client()
    table = client.table.return_value

    (
        table.select.return_value
        .eq.return_value
        .eq.return_value
        .maybe_single.return_value
        .execute.return_value.data
    ) = None

    with pytest.raises(ValueError, match="not found"):
        get_evidence_signed_url(
            client,
            owner_id=OWNER_ID,
            evidence_id=EVIDENCE_ID,
        )

    client.storage.from_.assert_not_called()
