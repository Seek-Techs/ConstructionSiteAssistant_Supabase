
import streamlit as st
from datetime import date
import sqlite3

from observation_model import SiteObservation, validate_observation
from storage import (
    initialize_database,
    save_observation,
    get_observations,
    next_observation_id,
    update_observation_status,
    update_observation,
    save_project,
    get_projects,
    store_uploaded_photo,
    get_observation_photos,
    resolve_photo_path,
    assign_project_to_observation,
)
from report_builder import build_whatsapp_report
from word_report_builder import build_word_report
from observation_filters import filter_observations
from io import BytesIO
from action_tracking import get_overdue_observations
from docx.enum.text import WD_ALIGN_PARAGRAPH

st.set_page_config(
    page_title="Construction Site Assistant",
    page_icon="🏗️",
    layout="centered",
)

initialize_database()

projects = get_projects()

project_options = {
    project["project_code"]: (
        f'{project["project_code"]} — '
        f'{project["project_name"]}'
    )
    for project in projects
}

st.title("Construction Site Assistant")
st.caption("Milestone 1 — Daily Site Observation Recorder")

st.subheader("Record a Site Observation")

with st.form("observation_form"):
    if projects:
        project_code = st.selectbox(
            "Project",
            options=list(project_options.keys()),
            format_func=lambda code: project_options[code],
        )
    else:
        st.warning(
            "Register a project before recording an observation."
        )
        project_code = ""
    report_date = st.date_input(
        "Observation date",
        value=date.today(),
    )

    site = st.text_input("Site")
    location = st.text_input("Location / Chainage")
    contractor = st.text_input("Contractor")

    category = st.selectbox(
        "Category",
        ["Quality", "HSE", "Traffic", "Other"],
    )

    information_source = st.selectbox(
        "Information source",
        ["Direct observation", "Contractor-reported"],
    )

    description = st.text_area("Observation description")
    uploaded_photos = st.file_uploader(
    "Attach photographic evidence (optional)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key="new_observation_photos",
)
    photo_captions_text = st.text_area(
        "Photo captions (optional)",
        placeholder=(
            "One caption per line, in the same order as the photos.\n"
            "Example: Embankment profile at Chainage 0+100, looking north"
        ),
        key="new_observation_photo_captions",
    )
    required_action = st.text_area("Required follow-up action")
    
    due_date = st.date_input(
        "Action due date (optional)",
        value=None,
        key="new_observation_due_date",
    )

    responsible_party = st.text_input("Responsible party")

    submitted = st.form_submit_button(
    "Validate and Record",
    disabled=not projects,
)

if submitted:
    observation = SiteObservation(
        observation_id=next_observation_id(),
        report_date=report_date.isoformat(),
        site=site,
        location=location,
        contractor=contractor,
        category=category,
        information_source=information_source,
        description=description,
        required_action=required_action,
        due_date=due_date.isoformat() if due_date else "",
        responsible_party=responsible_party,
        project_code=project_code,
    )

    errors = validate_observation(observation)

    if errors:
        st.error("Please correct the following issues:")
        for error in errors:
            st.write(f"- {error}")
    else:
        try:
            save_observation(observation)

            saved_photo_count = 0

            photo_captions = photo_captions_text.splitlines()

            for photo_index, uploaded_photo in enumerate(uploaded_photos):
                store_uploaded_photo(
                    observation_id=observation.observation_id,
                    uploaded_file=uploaded_photo,
                    caption=(
                        photo_captions[photo_index]
                        if photo_index < len(photo_captions)
                        else ""
                    ),
                )
                saved_photo_count += 1

            st.success(
                f"Observation {observation.observation_id} saved "
                f"with {saved_photo_count} photo(s)."
            )

        except Exception as error:
            st.error(
                "An error occurred while saving the observation "
                "or its photos. The observation may already have "
                f"been saved. Details: {error}"
            )

st.divider()


st.header("Project Register")

with st.expander("Add a new project", expanded=False):
    with st.form("add_project_form"):
        project_code = st.text_input("Project Code")
        project_name = st.text_input("Project Name")
        project_location = st.text_input("Project Location")

        submitted = st.form_submit_button("Save Project")

        if submitted:
            try:
                save_project(
                    project_code,
                    project_name,
                    project_location,
                )
            except ValueError as error:
                st.error(str(error))
            except sqlite3.IntegrityError:
                st.error(
                    "This project code already exists. "
                    "Please use a unique project code."
                )
            else:
                st.success("Project saved successfully.")
                st.rerun()

projects = get_projects()

if projects:
    st.dataframe(
        projects,
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No projects registered yet.")

st.subheader("Saved Observations")

observations = get_observations()
overdue_observations = get_overdue_observations(observations)

# Dashboard summary
st.write("### Site Supervision Dashboard")

total_observations = len(observations)

open_count = sum(
    observation.status == "Open"
    for observation in observations
)

in_progress_count = sum(
    observation.status == "In Progress"
    for observation in observations
)

closed_count = sum(
    observation.status == "Closed"
    for observation in observations
)

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Total Observations", total_observations)
col2.metric("Open", open_count)
col3.metric("In Progress", in_progress_count)
col4.metric("Closed", closed_count)
col5.metric("Overdue Actions", len(overdue_observations))

if overdue_observations:
    st.warning(
        f"{len(overdue_observations)} outstanding action(s) "
        "are past their due date."
    )

    with st.expander("View overdue actions", expanded=True):
        for observation in overdue_observations:
            st.write(
                f"**{observation.observation_id} — "
                f"{observation.contractor}**"
            )
            st.write(f"Site: {observation.site}")
            st.write(f"Location: {observation.location}")
            st.write(f"Due date: {observation.due_date}")
            st.write(f"Status: {observation.status}")
            st.write(f"Required action: {observation.required_action}")
            st.divider()
else:
    st.success("No overdue actions.")

st.divider()


# Observation breakdown by category
st.write("#### Observations by Category")

categories = ["Quality", "HSE", "Traffic", "Other"]

category_counts = {
    category: sum(
        observation.category == category
        for observation in observations
    )
    for category in categories
}

category_columns = st.columns(len(categories))

for column, category in zip(category_columns, categories):
    column.metric(category, category_counts[category])

st.divider()


# Outstanding actions
st.write("### Outstanding Actions")

outstanding_observations = [
    observation
    for observation in observations
    if observation.status in {"Open", "In Progress"}
]

if not outstanding_observations:
    st.success("There are no outstanding observations.")
else:
    st.caption(
        f"{len(outstanding_observations)} observation(s) "
        "require follow-up."
    )

    for observation in outstanding_observations:
        with st.expander(
            f"{observation.observation_id} | "
            f"{observation.contractor} | "
            f"{observation.status}"
        ):
            st.write(f"**Site:** {observation.site}")
            st.write(f"**Location:** {observation.location}")
            st.write(f"**Category:** {observation.category}")
            st.write(f"**Description:** {observation.description}")
            st.write(f"**Required action:** {observation.required_action}")
            st.write(
                f"**Responsible party:** "
                f"{observation.responsible_party}"
            )

st.divider()


if not observations:
    st.info("No observations saved yet.")
    filtered_observations = []
else:
    st.caption(f"Total saved observations: {len(observations)}")

    st.write("### Search and Filter")

    search_text = st.text_input(
        "Search observations",
        placeholder="ID, site, location, contractor or description",
    )

    contractors = sorted({
        observation.contractor
        for observation in observations
    })

    selected_contractor = st.selectbox(
        "Contractor",
        ["All"] + contractors,
    )

    selected_category = st.selectbox(
        "Category",
        ["All", "Quality", "HSE", "Traffic", "Other"],
    )

    selected_status = st.selectbox(
        "Follow-up status",
        ["All", "Open", "In Progress", "Closed"],
    )

    date_filter_enabled = st.checkbox("Filter by date range")

    start_date = None
    end_date = None

    if date_filter_enabled:
        date_col1, date_col2 = st.columns(2)

        with date_col1:
            start_date = st.date_input(
                "From date",
                value=min(
                    date.fromisoformat(obs.report_date)
                    for obs in observations
                ),
            )

        with date_col2:
            end_date = st.date_input(
                "To date",
                value=max(
                    date.fromisoformat(obs.report_date)
                    for obs in observations
                ),
            )

        if start_date > end_date:
            st.error("The start date cannot be later than the end date.")

    if not date_filter_enabled or start_date <= end_date:
        filtered_observations = filter_observations(
            observations,
            search_text=search_text,
            contractor=selected_contractor,
            category=selected_category,
            status=selected_status,
            start_date=start_date,
            end_date=end_date,
        )
    else:
        filtered_observations = []

    st.caption(
        f"Matching observations: {len(filtered_observations)} "
        f"of {len(observations)}"
    )

    if not filtered_observations:
        st.info("No observations match the selected search and filters.")


if not observations:
    st.info("No observations saved yet.")
else:
    st.caption(f"Total saved observations: {len(observations)}")

    for observation in filtered_observations:
        with st.expander(
            f"{observation.observation_id} — {observation.site}"
        ):
            st.write("**Date:**", observation.report_date)
            st.write(
                "**Project:**",
                project_options.get(
                    observation.project_code,
                    observation.project_code or "Not linked to a project",
                ),
            )
            st.write("**Location:**", observation.location)
            st.write("**Contractor:**", observation.contractor)
            st.write("**Category:**", observation.category)
            st.write("**Source:**", observation.information_source)
            st.write("**Description:**", observation.description)
            st.write("**Required action:**", observation.required_action)
            st.write("**Responsible party:**", observation.responsible_party)
            st.write(
                "**Action due date:**",
                observation.due_date or "Not set",
            )
            st.write("**Status:**", observation.status)

            # Older records may have no project. Never guess: the user
            # chooses the project, and only an empty link can be filled.
            if not observation.project_code and projects:
                with st.form(
                    f"assign_project_form_{observation.observation_id}"
                ):
                    chosen_project = st.selectbox(
                        "Link this observation to a project",
                        options=list(project_options.keys()),
                        format_func=lambda code: project_options[code],
                        key=f"assign_project_{observation.observation_id}",
                    )
                    assign_submitted = st.form_submit_button(
                        "Link to Project"
                    )

                if assign_submitted:
                    try:
                        assign_project_to_observation(
                            observation.observation_id,
                            chosen_project,
                        )
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))

            
            if observation.verification_notes:
                st.write(
                    "**Verification notes:**",
                    observation.verification_notes,
                )

            # Display photographic evidence
            photos = get_observation_photos(
                observation.observation_id
            )

            st.write("**Photographic Evidence**")

            if photos:
                photo_columns = st.columns(2)

                for index, photo in enumerate(photos):
                    photo_path = resolve_photo_path(photo)

                    with photo_columns[index % 2]:
                        if photo_path is not None:
                            st.image(
                                str(photo_path),
                                caption=(
                                    photo.get("caption")
                                    or photo["original_filename"]
                                ),
                                width="stretch",
                            )
                        else:
                            st.warning(
                                "Photo file not found: "
                                f"{photo['original_filename']}"
                            )
            else:
                st.caption("No photographs attached.")

            st.divider()

            st.write("**Edit Observation Details**")

            with st.form(f"edit_form_{observation.observation_id}"):
                edit_date = st.date_input(
                    "Observation date",
                    value=date.fromisoformat(observation.report_date),
                    key=f"edit_date_{observation.observation_id}",
                )

                edit_site = st.text_input(
                    "Site",
                    value=observation.site,
                    key=f"edit_site_{observation.observation_id}",
                )

                edit_location = st.text_input(
                    "Location / Chainage",
                    value=observation.location,
                    key=f"edit_location_{observation.observation_id}",
                )

                edit_contractor = st.text_input(
                    "Contractor",
                    value=observation.contractor,
                    key=f"edit_contractor_{observation.observation_id}",
                )

                edit_category = st.selectbox(
                    "Category",
                    ["Quality", "HSE", "Traffic", "Other"],
                    index=["Quality", "HSE", "Traffic", "Other"].index(
                        observation.category
                    ),
                    key=f"edit_category_{observation.observation_id}",
                )

                edit_source = st.selectbox(
                    "Information source",
                    ["Direct observation", "Contractor-reported"],
                    index=[
                        "Direct observation",
                        "Contractor-reported",
                    ].index(observation.information_source),
                    key=f"edit_source_{observation.observation_id}",
                )

                edit_description = st.text_area(
                    "Observation description",
                    value=observation.description,
                    key=f"edit_description_{observation.observation_id}",
                )

                edit_action = st.text_area(
                    "Required follow-up action",
                    value=observation.required_action,
                    key=f"edit_action_{observation.observation_id}",
                )

                edit_responsible = st.text_input(
                    "Responsible party",
                    value=observation.responsible_party,
                    key=f"edit_responsible_{observation.observation_id}",
                )

                edited_due_date = st.date_input(
                    "Action due date (optional)",
                    value=(
                        date.fromisoformat(observation.due_date)
                        if observation.due_date
                        else None
                    ),
                    key=f"edit_due_date_{observation.observation_id}",
                )

                edit_submitted = st.form_submit_button(
                    "Save Observation Changes"
                )

            if edit_submitted:
                edited_observation = SiteObservation(
                    observation_id=observation.observation_id,
                    report_date=edit_date.isoformat(),
                    site=edit_site,
                    location=edit_location,
                    contractor=edit_contractor,
                    category=edit_category,
                    information_source=edit_source,
                    description=edit_description,
                    required_action=edit_action,
                    responsible_party=edit_responsible,
                    due_date=edited_due_date.isoformat() if edited_due_date else "",
                    status=observation.status,
                    verification_notes=observation.verification_notes,
                    project_code=observation.project_code,
                )

                errors = validate_observation(edited_observation)

                if errors:
                    st.error("Please correct the following issues:")
                    for error in errors:
                        st.write(f"- {error}")
                else:
                    try:
                        update_observation(edited_observation)
                        st.success(
                            f"{observation.observation_id} updated successfully."
                        )
                        st.rerun()
                    except ValueError as error:
                        st.error(str(error))
                    except Exception as error:
                        st.error(
                            f"Could not update the observation: {error}"
                        )

            st.divider()
            st.write("**Update Follow-up Status**")

            with st.form(f"status_form_{observation.observation_id}"):
                new_status = st.selectbox(
                    "Status",
                    ["Open", "In Progress", "Closed"],
                    index=[
                        "Open",
                        "In Progress",
                        "Closed",
                    ].index(observation.status),
                    key=f"status_{observation.observation_id}",
                )

                verification_notes = st.text_area(
                    "Verification notes",
                    value=observation.verification_notes,
                    placeholder=(
                        "Record the follow-up inspection, "
                        "evidence checked and outcome."
                    ),
                    key=f"notes_{observation.observation_id}",
                )

                update_submitted = st.form_submit_button(
                    "Save Status Update"
                )

            if update_submitted:
                try:
                    update_observation_status(
                        observation.observation_id,
                        new_status,
                        verification_notes,
                    )
                    st.success(
                        f"{observation.observation_id} updated successfully."
                    )
                    st.rerun()

                except ValueError as error:
                    st.error(str(error))



st.divider()
st.header("Management Report")

st.write(
    "Select the saved observations you want to include in your report."
)

if not observations:
    st.info("Record an observation before generating a report.")
else:
    observation_by_id = {
        observation.observation_id: observation
        for observation in observations
    }

    all_ids = list(observation_by_id.keys())

    filtered_ids = [
        observation.observation_id
        for observation in filtered_observations
    ]

    # Initialise report selection only once.
    if "report_selected_ids" not in st.session_state:
        st.session_state["report_selected_ids"] = []

    st.caption(
        f"{len(filtered_ids)} observations currently match "
        "your search and filters."
    )

    if st.button(
        "Select all matching observations",
        disabled=not filtered_ids,
    ):
        st.session_state["report_selected_ids"] = filtered_ids

    if st.button("Clear report selection"):
        st.session_state["report_selected_ids"] = []

    selected_ids = st.multiselect(
        "Observations to include in the report",
        options=all_ids,
        format_func=lambda observation_id: (
            f"{observation_id} — "
            f"{observation_by_id[observation_id].site} "
            f"({observation_by_id[observation_id].category})"
        ),
        key="report_selected_ids",
        help=(
            "You can select or remove individual records here. "
            "All saved observations are available, including records "
            "outside your current search and filters."
        ),
    )

    if selected_ids:
        selected_observations = [
            observation_by_id[observation_id]
            for observation_id in selected_ids
        ]
        report_text = build_whatsapp_report(selected_observations)

        st.subheader("WhatsApp-ready Report")
        st.caption(
            "Use the copy icon on the report block to copy the text."
        )
        st.code(report_text, language=None)

        st.download_button(
            label="Download Report as Text",
            data=report_text,
            file_name="construction_site_report.txt",
            mime="text/plain",
        )

        st.subheader("Word Report Details")

        report_reference = st.text_input(
            "Report reference (optional)",
            key="report_reference",
        )
        prepared_by = st.text_input(
            "Prepared by (optional)",
            key="report_prepared_by",
            help="Left blank, the report has an empty line to sign.",
        )
        checked_by = st.text_input(
            "Checked by (optional)",
            key="report_checked_by",
        )

        word_buffer = BytesIO()
        build_word_report(
            selected_observations,
            word_buffer,
            prepared_by=prepared_by,
            checked_by=checked_by,
            report_reference=report_reference,
        )

        st.download_button(
            label="Download Report as Word",
            data=word_buffer.getvalue(),
            file_name="construction_site_report.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
        )
    else:
        st.info("Select one or more observations to preview the report.")
