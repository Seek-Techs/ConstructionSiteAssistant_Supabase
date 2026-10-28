"""Supabase evidence upload service."""

from evidence_helpers import (
    build_evidence_storage_path,
    validate_evidence_file,
)

EVIDENCE_BUCKET = "observation-evidence"

ALLOWED_EVIDENCE_CATEGORIES = {
    "Quality",
    "HSE",
    "Progress",
    "Testing",
    "Other",
}


def upload_evidence(
    client,
    *,
    owner_id: str,
    evidence_id: str,
    project_id: str | None,
    observation_id: str | None,
    filename: str,
    mime_type: str,
    file_bytes: bytes,
    caption: str = "",
    evidence_category: str = "Other",
) -> dict:
    """Insert evidence metadata and upload the file to private Storage."""

    if (project_id is None) == (observation_id is None):
        raise ValueError(
            "Evidence must be linked to exactly one project or observation."
        )

    if not isinstance(file_bytes, bytes):
        raise ValueError("File content must be bytes.")

    validate_evidence_file(
        mime_type=mime_type,
        file_size_bytes=len(file_bytes),
    )

    if evidence_category not in ALLOWED_EVIDENCE_CATEGORIES:
        raise ValueError("Unsupported evidence category.")

    if not isinstance(caption, str):
        raise ValueError("Caption must be text.")

    object_path = build_evidence_storage_path(
        owner_id=owner_id,
        evidence_id=evidence_id,
        filename=filename,
    )

    metadata = {
        "owner_id": owner_id,
        "evidence_id": evidence_id,
        "project_id": project_id,
        "observation_id": observation_id,
        "object_path": object_path,
        "original_filename": filename,
        "mime_type": mime_type,
        "file_size_bytes": len(file_bytes),
        "caption": caption,
        "evidence_category": evidence_category,
    }

    client.table("observation_evidence").insert(metadata).execute()
    storage = client.storage.from_(EVIDENCE_BUCKET)

    try:
        storage.upload(
            object_path,
            file_bytes,
            file_options={
                "content-type": mime_type,
                "upsert": "false",
            },
        )
    except Exception:
        cleanup_succeeded = False

        try:
            storage.remove([object_path])
        except Exception:
            # Keep metadata if we cannot confirm Storage cleanup.
            pass
        else:
            cleanup_succeeded = True

        if cleanup_succeeded:
            try:
                (
                    client.table("observation_evidence")
                    .delete()
                    .eq("owner_id", owner_id)
                    .eq("evidence_id", evidence_id)
                    .execute()
                )
            except Exception:
                # Leave metadata in place if database cleanup fails.
                pass

        # Re-raise the original upload exception, not a cleanup exception.
        raise

    return metadata

def delete_evidence(
    client,
    *,
    owner_id: str,
    evidence_id: str,
) -> None:
    """Delete an evidence object before deleting its metadata.

    The owner ID must come from the validated authenticated user.
    Storage and database policies remain responsible for authorization.
    """

    # Find only a record belonging to this owner.
    response = (
        client.table("observation_evidence")
        .select("object_path")
        .eq("owner_id", owner_id)
        .eq("evidence_id", evidence_id)
        .maybe_single()
        .execute()
    )

    record = response.data

    if not record:
        raise ValueError("Evidence record not found.")

    object_path = record.get("object_path")

    if not isinstance(object_path, str) or not object_path:
        raise ValueError("Evidence record has no valid storage path.")

    # Remove the stored object first. If this fails, keep the metadata.
    client.storage.from_(EVIDENCE_BUCKET).remove([object_path])

    # Delete metadata only after Storage removal succeeds.
    (
        client.table("observation_evidence")
        .delete()
        .eq("owner_id", owner_id)
        .eq("evidence_id", evidence_id)
        .execute()
    )


def list_evidence(client, *, owner_id: str) -> list[dict]:
    """List evidence metadata for one owner, newest first.

    Database RLS independently enforces access authorization.
    """
    response = (
        client.table("observation_evidence")
        .select(
            "evidence_id, project_id, observation_id, "
            "original_filename, mime_type, file_size_bytes, "
            "caption, evidence_category, created_at"
        )
        .eq("owner_id", owner_id)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


def update_evidence_metadata(
    client,
    *,
    owner_id: str,
    evidence_id: str,
    caption: str,
    evidence_category: str,
) -> list[dict]:
    """Update only the caption and category of owned evidence."""
    if not isinstance(caption, str):
        raise ValueError("Caption must be text.")

    if evidence_category not in ALLOWED_EVIDENCE_CATEGORIES:
        raise ValueError("Unsupported evidence category.")

    response = (
        client.table("observation_evidence")
        .update({
            "caption": caption,
            "evidence_category": evidence_category,
        })
        .eq("owner_id", owner_id)
        .eq("evidence_id", evidence_id)
        .select("evidence_id")
        .execute()
    )

    return response.data or []


def get_evidence_signed_url(
    client,
    *,
    owner_id: str,
    evidence_id: str,
) -> str:
    """Create a short-lived signed URL for evidence owned by this user."""
    response = (
        client.table("observation_evidence")
        .select("object_path")
        .eq("owner_id", owner_id)
        .eq("evidence_id", evidence_id)
        .maybe_single()
        .execute()
    )

    record = response.data

    if not record:
        raise ValueError("Evidence record not found.")

    object_path = record.get("object_path")

    if not isinstance(object_path, str) or not object_path:
        raise ValueError("Evidence record has no valid storage path.")

    response = (
        client.storage
        .from_(EVIDENCE_BUCKET)
        .create_signed_url(object_path, 60)
    )

    if isinstance(response, dict):
        signed_url = response.get("signedURL") or response.get("signedUrl")
    else:
        signed_url = (
            getattr(response, "signedURL", None)
            or getattr(response, "signedUrl", None)
        )

    if not isinstance(signed_url, str) or not signed_url:
        raise RuntimeError("Supabase did not return a valid signed URL.")

    return signed_url
