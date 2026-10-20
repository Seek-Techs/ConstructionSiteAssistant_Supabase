
def filter_observations(
    observations,
    search_text="",
    contractor="All",
    category="All",
    status="All",
    start_date=None,
    end_date=None,
):
    """Return observations matching the supplied filters."""

    search_text = search_text.strip().casefold()
    results = []

    for observation in observations:
        # Keyword search across useful record fields.
        searchable_text = " ".join([
            observation.observation_id,
            observation.site,
            observation.location,
            observation.contractor,
            observation.description,
        ]).casefold()

        if search_text and search_text not in searchable_text:
            continue

        if contractor != "All" and observation.contractor != contractor:
            continue

        if category != "All" and observation.category != category:
            continue

        if status != "All" and observation.status != status:
            continue

        if start_date and observation.report_date < start_date.isoformat():
            continue

        if end_date and observation.report_date > end_date.isoformat():
            continue

        results.append(observation)

    return results
