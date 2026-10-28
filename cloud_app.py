"""Cloud version of Construction Site Assistant."""

import streamlit as st
from datetime import date
from auth_helpers import (
    create_supabase_client,
    register_user,
    sign_in_user,
    request_password_reset,
    sign_out_user,
    get_validated_user,
)

from cloud_data_service import (
    create_observation,
    create_project,
    list_owned_observations,
    list_owned_projects,
)
from evidence_service import (
    ALLOWED_EVIDENCE_CATEGORIES,
    delete_evidence,
    get_evidence_signed_url,
    list_evidence,
    update_evidence_metadata,
    upload_evidence,
)
from historical_import_ui import render_historical_import_preview
from uuid import uuid4


st.set_page_config(
    page_title="Construction Site Assistant — Cloud",
    page_icon="🏗️",
    layout="wide",
)

# Reset observation fields only after a successful save.
if st.session_state.pop("reset_observation_form", False):
    st.session_state["create_observation_date"] = date.today()
    st.session_state["create_observation_site"] = ""
    st.session_state["create_observation_location"] = ""
    st.session_state["create_observation_contractor"] = ""
    st.session_state["create_observation_category"] = "Quality"
    st.session_state["create_observation_information_source"] = (
        "Direct observation"
    )
    st.session_state["create_observation_description"] = ""
    st.session_state["create_observation_required_action"] = ""
    st.session_state["create_observation_responsible_party"] = ""
    st.session_state["create_observation_due_date_enabled"] = False
    st.session_state["create_observation_due_date"] = date.today()

success_message = st.session_state.pop(
    "observation_save_success",
    None,
)
if success_message:
    st.success(success_message)
# CONSTRUCTION_SITE_ASSISTANT_CENTERED_LAYOUT
st.markdown("""
<style>
[data-testid="stMainBlockContainer"] {
    max-width: 760px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
}
</style>
""", unsafe_allow_html=True)
st.title("Construction Site Assistant")
st.caption("Cloud workspace — authentication milestone")

# Keep the client within this browser's Streamlit session.
# Do not use st.cache_resource for a shared authenticated client.
if "supabase_client" not in st.session_state:
    try:
        st.session_state["supabase_client"] = create_supabase_client()
    except Exception:
        st.error(
            "Could not initialize the Supabase client. "
            "Check the project's Streamlit secrets configuration."
        )
        st.stop()

client = st.session_state["supabase_client"]

# This initial milestone displays authentication screens only.
# No project or observation data is loaded here.
if "authenticated_user" not in st.session_state:
    st.session_state["authenticated_user"] = None

user = st.session_state["authenticated_user"]

if user is not None:
    try:
        validated_user = get_validated_user(client)
    except Exception:
        st.error(
            "Unable to verify your session right now. "
            "Check your connection and try again."
        )
        st.stop()

    if validated_user is None:
        st.session_state["authenticated_user"] = None
        st.info("Your session could not be verified. Please sign in again.")
        st.rerun()

    st.session_state["authenticated_user"] = validated_user
    user = validated_user

if user is not None:
    st.success(f"Signed in as {user.email}")

    if st.button("Sign out"):
        try:
            sign_out_user(client)
            st.session_state["authenticated_user"] = None
            st.rerun()
        except Exception:
            st.error("Sign-out failed. Please try again.")

    # Load cloud records only after validating the signed-in user.
    owner_id = str(user.id)

    try:
        projects = list_owned_projects(client, owner_id=owner_id)
        observations = list_owned_observations(
            client,
            owner_id=owner_id,
        )
    except Exception:
        st.error(
            "Could not load your cloud workspace. "
            "Check your connection and database permissions, then try again."
        )
        st.stop()

    all_observations = list(observations)

    project_tab, observation_tab, evidence_tab, import_tab = st.tabs(
        [
            "Projects",
            "Site observations",
            "Evidence management",
            "Historical import (preview)",
        ]
    )

    with project_tab:
        st.subheader("Create a project")

        with st.form("create_cloud_project_form"):
            project_code = st.text_input(
                "Project code",
                placeholder="e.g. LFZ-SWQ",
            )
            project_name = st.text_input(
                "Project name",
                placeholder="Enter the project name",
            )
            project_location = st.text_input(
                "Project location",
                placeholder="Enter the site location",
            )

            submitted = st.form_submit_button("Create project")

        if submitted:
            try:
                created_project = create_project(
                    client,
                    owner_id=owner_id,
                    project_code=project_code,
                    project_name=project_name,
                    location=project_location,
                )
                st.success(
                    f"Project '{created_project.get('project_code', project_code.strip())}' "
                    "created successfully."
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error(
                    "The project could not be created. Check that the project "
                    "code is unique in your account and that your connection "
                    "and database permissions are working."
                )

        st.divider()
        st.subheader("My projects")

        if projects:
            st.dataframe(
                projects,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No projects are available in this account yet.")


    with observation_tab:
        st.subheader("Record a site observation")

        if not projects:
            st.warning(
                "Create a project in the Projects tab before recording "
                "an observation."
            )
        else:
            project_options = {
                (
                    f"{project.get('project_code', '')} — "
                    f"{project.get('project_name', '')}"
                ).strip(" —"): project["id"]
                for project in projects
            }

            with st.form("create_cloud_observation_form"):
                selected_project_label = st.selectbox(
                    "Project",
                    options=list(project_options.keys()),
                    key="create_observation_project",
                )

                report_date = st.date_input(
                    "Observation date",
                    value=date.today(),
                    key="create_observation_date",
                )

                site = st.text_input(
                    "Site",
                    placeholder="e.g. E8 South Drainage",
                    key="create_observation_site",
                )
                location = st.text_input(
                    "Location / Chainage",
                    placeholder="e.g. 0+360",
                    key="create_observation_location",
                )
                contractor = st.text_input(
                    "Contractor",
                    placeholder="Enter the contractor's name",
                    key="create_observation_contractor",
                )

                category = st.selectbox(
                    "Category",
                    ["Quality", "HSE", "Traffic", "Other"],
                    key="create_observation_category",
                )

                information_source = st.selectbox(
                    "Information source",
                    ["Direct observation", "Contractor-reported"],
                    key="create_observation_information_source",
                )

                description = st.text_area(
                    "Observation description",
                    placeholder="Record the factual observation.",
                    key="create_observation_description",
                )
                required_action = st.text_area(
                    "Required action",
                    placeholder="State the corrective or follow-up action.",
                    key="create_observation_required_action",
                )
                responsible_party = st.text_input(
                    "Responsible party",
                    placeholder="e.g. Contractor Site Engineer",
                    key="create_observation_responsible_party",
                )

                due_date_enabled = st.checkbox(
                    "Set a due date",
                    key="create_observation_due_date_enabled",
                )

                due_date = None
                if due_date_enabled:
                    due_date = st.date_input(
                        "Due date",
                        value=date.today(),
                        key="create_observation_due_date",
                    )

                submitted_observation = st.form_submit_button(
                    "Save observation"
                )

            if submitted_observation:
                try:
                    created_observation = create_observation(
                        client,
                        owner_id=owner_id,
                        report_date=report_date.isoformat(),
                        site=site,
                        location=location,
                        contractor=contractor,
                        category=category,
                        information_source=information_source,
                        description=description,
                        required_action=required_action,
                        responsible_party=responsible_party,
                        project_id=project_options[
                            selected_project_label
                        ],
                        due_date=(
                            due_date.isoformat()
                            if due_date_enabled and due_date
                            else None
                        ),
                    )

                    st.session_state["observation_save_success"] = (
                        "Observation "
                        f"{created_observation['observation_id']} "
                        "saved successfully."
                    )
                    st.session_state["reset_observation_form"] = True
                    st.rerun()

                except ValueError as exc:
                    st.error(str(exc))
                except Exception:
                    st.error(
                        "The observation could not be saved. Check your "
                        "connection, project selection and database "
                        "permissions, then try again."
                    )

        st.divider()
        st.subheader("My site observations")

        if projects:
            filter_project_options = {
                "All projects": None,
                **{
                    (
                        f"{project.get('project_code', '')} — "
                        f"{project.get('project_name', '')}"
                    ).strip(" —"): project["id"]
                    for project in projects
                },
            }

            selected_filter = st.selectbox(
                "Filter by project",
                options=list(filter_project_options.keys()),
                key="observation_project_filter",
            )

            selected_filter_id = filter_project_options[selected_filter]

            if selected_filter_id is not None:
                observations = list_owned_observations(
                    client,
                    owner_id=owner_id,
                    project_id=selected_filter_id,
                )


        if observations:
            today = date.today()
            overdue_observations = []

            for observation in observations:
                due_date_value = observation.get("due_date")
                status = observation.get("status")

                if status not in {"Open", "In Progress"}:
                    continue

                if not due_date_value:
                    continue

                try:
                    parsed_due_date = date.fromisoformat(
                        str(due_date_value)
                    )
                except ValueError:
                    continue

                if parsed_due_date < today:
                    overdue_observations.append(observation)

            st.metric(
                "Overdue Actions",
                len(overdue_observations),
            )

            if overdue_observations:
                st.warning(
                    "Some open actions have passed their due dates. "
                    "Review the records below."
                )

                st.dataframe(
                    [
                        {
                            "Observation ID": item.get("observation_id"),
                            "Project": item.get("project_id"),
                            "Contractor": item.get("contractor"),
                            "Site": item.get("site"),
                            "Due Date": item.get("due_date"),
                            "Status": item.get("status"),
                            "Required Action": item.get("required_action"),
                        }
                        for item in overdue_observations
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            st.dataframe(
                observations,
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.metric("Overdue Actions", 0)
            st.info("No observations match this selection.")


    with evidence_tab:
        st.subheader("Evidence management")
        st.caption(
            "Upload and manage private project or site-observation evidence."
        )

        # Load the evidence register for the validated account.
        try:
            evidence_records = list_evidence(
                client,
                owner_id=owner_id,
            )
            evidence_load_failed = False
        except Exception:
            evidence_records = []
            evidence_load_failed = True
            st.error(
                "Could not load the evidence register. "
                "Check your connection and database permissions."
            )

        if evidence_records:
            st.markdown("#### Evidence register")
            display_records = [
                {
                    "Filename": item["original_filename"],
                    "Category": item["evidence_category"],
                    "Caption": item["caption"],
                    "Project ID": item["project_id"],
                    "Observation ID": item["observation_id"],
                    "Uploaded": item["created_at"],
                    "Size (MiB)": round(
                        item["file_size_bytes"] / (1024 * 1024), 2
                    ),
                }
                for item in evidence_records
            ]
            st.dataframe(
                display_records,
                use_container_width=True,
                hide_index=True,
            )
        elif not evidence_load_failed:
            st.info("No evidence has been uploaded to this account yet.")

        # Prepare parent choices from records belonging to this user.
        parent_types = []
        if projects:
            parent_types.append("Project")
        if all_observations:
            parent_types.append("Observation")

        st.markdown("#### Upload evidence")

        if not parent_types:
            st.info(
                "Create a project or a site observation first. "
                "Evidence must be attached to exactly one existing record."
            )
        else:
            attachment_type = st.radio(
                "Attach evidence to",
                options=parent_types,
                horizontal=True,
                key="evidence_parent_type",
            )

            selected_project_id = None
            selected_observation_id = None

            if attachment_type == "Project":
                project_labels = {
                    (
                        f"{project.get('project_code', '')} — "
                        f"{project.get('project_name', '')}"
                    ).strip(" —"): project
                    for project in projects
                }
                selected_project_label = st.selectbox(
                    "Project",
                    options=list(project_labels.keys()),
                    key="evidence_project_choice",
                )
                selected_project_id = project_labels[
                    selected_project_label
                ]["id"]

            else:
                observation_labels = {
                    (
                        f"{item['observation_id']} — "
                        f"{item.get('contractor') or 'No contractor'} — "
                        f"{item.get('report_date') or 'No date'}"
                    ): item
                    for item in all_observations
                }
                selected_observation_label = st.selectbox(
                    "Site observation",
                    options=list(observation_labels.keys()),
                    key="evidence_observation_choice",
                )
                selected_observation_id = observation_labels[
                    selected_observation_label
                ]["observation_id"]

            uploaded_file = st.file_uploader(
                "Choose a file (maximum 50 MiB)",
                type=[
                    "jpg", "jpeg", "png", "webp", "pdf",
                    "doc", "docx", "xls", "xlsx",
                    "ppt", "pptx", "txt", "csv",
                ],
                max_upload_size=50,
                key="evidence_file_upload",
            )

            evidence_category = st.selectbox(
                "Evidence category",
                options=sorted(ALLOWED_EVIDENCE_CATEGORIES),
                key="evidence_upload_category",
            )
            caption = st.text_input(
                "Caption or description",
                key="evidence_upload_caption",
            )

            if st.button("Upload evidence", key="upload_evidence_button"):
                if uploaded_file is None:
                    st.warning("Choose a file before uploading.")
                else:
                    try:
                        upload_evidence(
                            client,
                            owner_id=owner_id,
                            evidence_id=str(uuid4()),
                            project_id=selected_project_id,
                            observation_id=selected_observation_id,
                            filename=uploaded_file.name,
                            mime_type=uploaded_file.type or "",
                            file_bytes=uploaded_file.getvalue(),
                            caption=caption,
                            evidence_category=evidence_category,
                        )
                        st.success("Evidence uploaded successfully.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error(
                            "Evidence upload failed. "
                            "Check the file and your connection, then try again."
                        )

        if evidence_records:
            evidence_labels = {
                (
                    f"{item['original_filename']} — "
                    f"{item['evidence_id'][:8]}"
                ): item
                for item in evidence_records
            }
            label_options = list(evidence_labels.keys())

            st.markdown("#### View or download evidence")
            selected_view_label = st.selectbox(
                "Select evidence",
                options=label_options,
                key="evidence_view_choice",
            )
            selected_view_record = evidence_labels[selected_view_label]

            if st.button(
                "Generate temporary file link",
                key="generate_evidence_link",
            ):
                try:
                    signed_url = get_evidence_signed_url(
                        client,
                        owner_id=owner_id,
                        evidence_id=selected_view_record["evidence_id"],
                    )
                    st.link_button(
                        "Open or download file",
                        signed_url,
                    )
                    st.caption(
                        "This private-file link expires after approximately "
                        "60 seconds. Do not share it."
                    )
                except Exception:
                    st.error(
                        "Could not create a temporary file link. "
                        "Try again or check Storage permissions."
                    )

            st.markdown("#### Edit evidence details")
            with st.expander("Edit caption or category"):
                selected_edit_label = st.selectbox(
                    "Evidence to edit",
                    options=label_options,
                    key="evidence_edit_choice",
                )
                selected_edit_record = evidence_labels[selected_edit_label]
                edit_id = selected_edit_record["evidence_id"]

                edited_caption = st.text_input(
                    "Caption",
                    value=selected_edit_record["caption"],
                    key=f"edit_caption_{edit_id}",
                )
                current_category = selected_edit_record["evidence_category"]
                category_index = (
                    sorted(ALLOWED_EVIDENCE_CATEGORIES).index(current_category)
                    if current_category in ALLOWED_EVIDENCE_CATEGORIES
                    else sorted(ALLOWED_EVIDENCE_CATEGORIES).index("Other")
                )
                edited_category = st.selectbox(
                    "Category",
                    options=sorted(ALLOWED_EVIDENCE_CATEGORIES),
                    index=category_index,
                    key=f"edit_category_{edit_id}",
                )

                if st.button(
                    "Save evidence details",
                    key="save_evidence_details",
                ):
                    try:
                        updated = update_evidence_metadata(
                            client,
                            owner_id=owner_id,
                            evidence_id=edit_id,
                            caption=edited_caption,
                            evidence_category=edited_category,
                        )
                        if updated:
                            st.success("Evidence details updated.")
                            st.rerun()
                        else:
                            st.warning(
                                "No record was updated. Refresh and try again."
                            )
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error("Could not update the evidence details.")

            st.markdown("#### Delete evidence")
            with st.expander("Delete an evidence file"):
                selected_delete_label = st.selectbox(
                    "Evidence to delete",
                    options=label_options,
                    key="evidence_delete_choice",
                )
                selected_delete_record = evidence_labels[
                    selected_delete_label
                ]
                confirm_delete = st.checkbox(
                    "I confirm that I want to permanently delete this file "
                    "and its metadata.",
                    key="confirm_evidence_delete",
                )

                if st.button(
                    "Delete evidence",
                    key="delete_evidence_button",
                    disabled=not confirm_delete,
                ):
                    try:
                        delete_evidence(
                            client,
                            owner_id=owner_id,
                            evidence_id=selected_delete_record["evidence_id"],
                        )
                        st.success("Evidence deleted.")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
                    except Exception:
                        st.error(
                            "Deletion failed. The file may still exist; "
                            "refresh the evidence register before retrying."
                        )

    with import_tab:
        # Preview only: this screen has no access to the database client.
        render_historical_import_preview()


else:
    sign_in_tab, register_tab, reset_tab = st.tabs(
        ["Sign in", "Create account", "Reset password"]
    )

    with sign_in_tab:
        with st.form("sign_in_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input(
                "Password",
                type="password",
                key="login_password",
            )
            submitted = st.form_submit_button("Sign in")

        if submitted:
            if not email.strip() or not password:
                st.warning("Enter your email address and password.")
            else:
                try:
                    response = sign_in_user(client, email, password)
                    if response.user is not None and response.session is not None:
                        st.session_state["authenticated_user"] = response.user
                        st.success("Sign-in successful.")
                        st.rerun()
                    else:
                        st.error(
                            "No active session was returned. "
                            "If email confirmation is required, check your inbox."
                        )
                except Exception:
                    st.error(
                        "Sign-in failed. Check your credentials "
                        "and try again."
                    )

    with register_tab:
        with st.form("register_form"):
            new_email = st.text_input("Email address", key="register_email")
            new_password = st.text_input(
                "Password",
                type="password",
                key="register_password",
            )
            confirm_password = st.text_input(
                "Confirm password",
                type="password",
                key="confirm_password",
            )
            register_submitted = st.form_submit_button("Create account")

        if register_submitted:
            if not new_email.strip() or not new_password:
                st.warning("Enter an email address and password.")
            elif new_password != confirm_password:
                st.warning("The passwords do not match.")
            else:
                try:
                    response = register_user(client, new_email, new_password)
                    if response.session is not None and response.user is not None:
                        st.session_state["authenticated_user"] = response.user
                        st.success("Account created and signed in.")
                        st.rerun()
                    else:
                        st.success(
                            "Registration request submitted. If email "
                            "confirmation is enabled, check your inbox "
                            "before signing in."
                        )
                except Exception:
                    st.error(
                        "Registration failed. Check the email, password "
                        "requirements, and Supabase Auth settings."
                    )

    with reset_tab:
        with st.form("reset_password_form"):
            reset_email = st.text_input(
                "Account email address",
                key="reset_email",
            )
            reset_submitted = st.form_submit_button("Request reset email")

        if reset_submitted:
            if not reset_email.strip():
                st.warning("Enter your account email address.")
            else:
                try:
                    request_password_reset(client, reset_email)
                    st.success(
                        "If an account matches that address, a password-reset "
                        "email may be sent. Check your inbox."
                    )
                except Exception:
                    st.error(
                        "The password-reset request could not be completed. "
                        "Check the Supabase Auth configuration."
                    )




from datetime import date


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

    owner_id = owner_id.strip()

    if not owner_id:
        raise ValueError("A valid owner is required.")

    text_fields = {
        "site": site,
        "location": location,
        "contractor": contractor,
        "description": description,
        "required_action": required_action,
        "responsible_party": responsible_party,
    }

    cleaned = {
        name: value.strip()
        for name, value in text_fields.items()
    }

    field_labels = {
        "site": "Site",
        "location": "Location",
        "contractor": "Contractor",
        "description": "Description",
        "required_action": "Required action",
        "responsible_party": "Responsible party",
    }

    for field, value in cleaned.items():
        if not value:
            raise ValueError(f"{field_labels[field]} is required.")

    try:
        parsed_report_date = date.fromisoformat(report_date)
        if parsed_report_date.isoformat() != report_date:
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

    # Determine the next sequential ID within this owner's workspace.
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

    observation_id = f"OBS-{highest_number + 1:04d}"

    record = {
        "observation_id": observation_id,
        "owner_id": owner_id,
        "report_date": report_date,
        "site": cleaned["site"],
        "location": cleaned["location"],
        "contractor": cleaned["contractor"],
        "category": category,
        "information_source": information_source,
        "description": cleaned["description"],
        "required_action": cleaned["required_action"],
        "responsible_party": cleaned["responsible_party"],
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
