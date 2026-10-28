import pytest

from evidence_helpers import (
    ALLOWED_EVIDENCE_MIME_TYPES,
    MAX_EVIDENCE_FILE_SIZE_BYTES,
    sanitize_storage_filename,
    validate_evidence_file,
)


def test_allowed_mime_types_include_supported_photos_and_documents():
    assert "image/jpeg" in ALLOWED_EVIDENCE_MIME_TYPES
    assert "image/png" in ALLOWED_EVIDENCE_MIME_TYPES
    assert "application/pdf" in ALLOWED_EVIDENCE_MIME_TYPES
    assert (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        in ALLOWED_EVIDENCE_MIME_TYPES
    )


def test_file_size_limit_is_50_mib():
    assert MAX_EVIDENCE_FILE_SIZE_BYTES == 50 * 1024 * 1024


def test_valid_evidence_file_is_accepted():
    validate_evidence_file(
        mime_type="image/jpeg",
        file_size_bytes=1024,
    )


def test_file_at_size_limit_is_accepted():
    validate_evidence_file(
        mime_type="application/pdf",
        file_size_bytes=MAX_EVIDENCE_FILE_SIZE_BYTES,
    )


def test_unsupported_mime_type_is_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        validate_evidence_file(
            mime_type="application/x-msdownload",
            file_size_bytes=1024,
        )


def test_file_larger_than_limit_is_rejected():
    with pytest.raises(ValueError, match="50 MiB"):
        validate_evidence_file(
            mime_type="image/jpeg",
            file_size_bytes=MAX_EVIDENCE_FILE_SIZE_BYTES + 1,
        )


@pytest.mark.parametrize("file_size", [0, -1])
def test_zero_or_negative_file_size_is_rejected(file_size):
    with pytest.raises(ValueError):
        validate_evidence_file(
            mime_type="image/jpeg",
            file_size_bytes=file_size,
        )


def test_storage_filename_removes_path_traversal_and_unsafe_characters():
    result = sanitize_storage_filename("../../Site Photo #1.jpg")

    assert result == "Site_Photo_1.jpg"
    assert "/" not in result
    assert "\\" not in result
    assert result not in {".", ".."}


def test_windows_path_does_not_become_part_of_storage_filename():
    result = sanitize_storage_filename(
        r"C:\Users\Admin\Pictures\Drainage Photo.jpg"
    )

    assert result == "Drainage_Photo.jpg"

def test_storage_path_contains_owner_evidence_id_and_safe_filename():
    from evidence_helpers import build_evidence_storage_path

    result = build_evidence_storage_path(
        owner_id="5e550458-8f82-4536-8b7d-6dee0e981f17",
        evidence_id="123e4567-e89b-12d3-a456-426614174000",
        filename=r"C:\Users\Admin\Pictures\Drainage Photo.jpg",
    )

    assert result == (
        "5e550458-8f82-4536-8b7d-6dee0e981f17/"
        "123e4567-e89b-12d3-a456-426614174000/"
        "Drainage_Photo.jpg"
    )


def test_storage_path_rejects_invalid_owner_id():
    from evidence_helpers import build_evidence_storage_path

    with pytest.raises(ValueError):
        build_evidence_storage_path(
            owner_id="not-a-uuid",
            evidence_id="123e4567-e89b-12d3-a456-426614174000",
            filename="Drainage Photo.jpg",
        )


def test_storage_path_rejects_invalid_evidence_id():
    from evidence_helpers import build_evidence_storage_path

    with pytest.raises(ValueError):
        build_evidence_storage_path(
            owner_id="5e550458-8f82-4536-8b7d-6dee0e981f17",
            evidence_id="not-a-uuid",
            filename="Drainage Photo.jpg",
        )


def test_storage_path_rejects_empty_filename():
    from evidence_helpers import build_evidence_storage_path

    with pytest.raises(ValueError):
        build_evidence_storage_path(
            owner_id="5e550458-8f82-4536-8b7d-6dee0e981f17",
            evidence_id="123e4567-e89b-12d3-a456-426614174000",
            filename="   ",
        )
