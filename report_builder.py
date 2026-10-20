
def build_whatsapp_report(observations):
    """Build a structured, WhatsApp-ready report from observations."""

    if not observations:
        return (
            "*CONSTRUCTION SITE OBSERVATION REPORT*\n\n"
            "No observations were selected for this report."
        )

    categories = ["Quality", "HSE", "Traffic", "Other"]
    # Include any category outside the standard list so no record is
    # silently left out of the report.
    categories += sorted({
        observation.category
        for observation in observations
        if observation.category not in categories
    })
    sources = ["Direct observation", "Contractor-reported"]

    lines = ["*CONSTRUCTION SITE OBSERVATION REPORT*"]

    report_dates = sorted(
        {observation.report_date for observation in observations}
    )

    if len(report_dates) == 1:
        lines.append(f"*Date:* {report_dates[0]}")
    else:
        lines.append(
            f"*Period:* {report_dates[0]} to {report_dates[-1]}"
        )

    lines.append(f"*Observations included:* {len(observations)}")
    lines.append("")

    for category in categories:
        category_observations = [
            observation
            for observation in observations
            if observation.category == category
        ]

        if not category_observations:
            continue

        lines.append(f"*{category.upper()}*")

        for source in sources:
            source_observations = [
                observation
                for observation in category_observations
                if observation.information_source == source
            ]

            if not source_observations:
                continue

            lines.append(f"_{source}_")

            for observation in source_observations:
                lines.append(
                    f"\n*{observation.observation_id} — "
                    f"{observation.site}*"
                )
                lines.append(f"Date: {observation.report_date}")
                lines.append(f"Location: {observation.location}")
                lines.append(f"Contractor: {observation.contractor}")
                lines.append(f"Observation: {observation.description}")
                lines.append(
                    f"Required action: {observation.required_action}"
                )
                lines.append(
                    f"Responsible party: {observation.responsible_party}"
                )
                lines.append(f"Status: {observation.status}")

                if observation.verification_notes.strip():
                    lines.append(
                        "Verification notes: "
                        f"{observation.verification_notes}"
                    )

                lines.append("")

    lines.append(
        "_Report generated from saved site observation records._"
    )

    return "\n".join(lines).strip()
