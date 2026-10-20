import pytest
from observation_model import SiteObservation
from report_builder import build_whatsapp_report


def make_observation(
    observation_id="OBS-0001",
    category="Quality",
    information_source="Direct observation",
    status="Open",
    verification_notes="",
):
    return SiteObservation(
        observation_id=observation_id,
        report_date="2026-10-16",
        site="Lekki",
        location="E2",
        contractor="Sino",
        category=category,
        information_source=information_source,
        description="Debris was observed during haulage.",
        required_action="Remove debris from the affected area.",
        responsible_party="Contractor",
        status=status,
        verification_notes=verification_notes,
    )


def test_report_includes_observation_and_required_action():
    observation = make_observation()

    report = build_whatsapp_report([observation])

    assert "OBS-0001" in report
    assert "Lekki" in report
    assert "Remove debris from the affected area." in report
    assert "Status: Open" in report


def test_report_distinguishes_information_sources():
    direct = make_observation(observation_id="OBS-0001")
    contractor_report = make_observation(
        observation_id="OBS-0002",
        information_source="Contractor-reported",
    )

    report = build_whatsapp_report([direct, contractor_report])

    assert "Direct observation" in report
    assert "Contractor-reported" in report
    assert "OBS-0001" in report
    assert "OBS-0002" in report


def test_report_includes_verification_notes_when_available():
    observation = make_observation(
        status="Closed",
        verification_notes="Follow-up inspection confirmed debris removal.",
    )

    report = build_whatsapp_report([observation])

    assert "Status: Closed" in report
    assert "Follow-up inspection confirmed debris removal." in report


def test_empty_selection_returns_helpful_message():
    report = build_whatsapp_report([])

    assert "No observations were selected" in report
