"""Validation and filename helpers for Construction Site Assistant."""

import re


ALLOWED_EVIDENCE_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
    }
)

MAX_EVIDENCE_FILE_SIZE_BYTES = 50 * 1024 * 1024


def validate_evidence_file(
    mime_type: str,
    file_size_bytes: int,
) -> None:
    """Raise ValueError if an evidence file fails basic validation."""

    if not isinstance(file_size_bytes, int) or isinstance(file_size_bytes, bool):
        raise ValueError("File size must be a positive integer.")

    if file_size_bytes <= 0:
        raise ValueError("File size must be greater than zero.")

    if mime_type not in ALLOWED_EVIDENCE_MIME_TYPES:
        raise ValueError(f"Unsupported evidence file type: {mime_type!r}")

    if file_size_bytes > MAX_EVIDENCE_FILE_SIZE_BYTES:
        raise ValueError("File exceeds the maximum allowed size of 50 MiB.")


def sanitize_storage_filename(filename: str) -> str:
    """Return a safe filename without directory paths or unsafe characters."""

    if not isinstance(filename, str):
        raise ValueError("Filename must be text.")

    # Normalize Windows and Unix separators, then keep only the filename.
    basename = filename.replace("\\", "/").split("/")[-1]

    # Replace spaces and unsafe characters with underscores.
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)

    # Remove leading/trailing dots and underscores.
    safe_name = safe_name.strip("._")

    if not safe_name:
        return "evidence"

    return safe_name

def build_evidence_storage_path(
    owner_id: str,
    evidence_id: str,
    filename: str,
) -> str:
    """Build a user-scoped path for an evidence file."""

    import uuid

    # Validate both identifiers before using them in a storage path.
    try:
        safe_owner_id = str(uuid.UUID(owner_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid owner UUID.") from exc

    try:
        safe_evidence_id = str(uuid.UUID(evidence_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Invalid evidence UUID.") from exc

    # Do not silently replace an empty filename with a default name here.
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Filename must not be empty.")

    safe_filename = sanitize_storage_filename(filename)

    return f"{safe_owner_id}/{safe_evidence_id}/{safe_filename}"
