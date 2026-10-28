# Construction Site Assistant

A cloud-enabled application for construction site supervision, observation management, photographic evidence, and structured reporting.

## Overview

Construction Site Assistant helps site supervisors document construction activities, record quality and health, safety and environment (HSE) observations, track corrective actions, and maintain an organized record of site evidence.

The cloud version uses Supabase for authentication, database access, and private evidence storage, with Streamlit providing the user interface.

## Features

- **Project management:** Create and manage construction project records.
- **Site observations:** Record observation dates, sites, locations, contractors, categories, descriptions, and information sources.
- **Follow-up tracking:** Document required actions, responsible parties, and observation status.
- **Photographic evidence:** Upload, retrieve, and manage evidence linked to projects or observations.
- **Evidence classification:** Organize evidence under Quality, HSE, Progress, Testing, and Other categories.
- **User-scoped access:** Retrieve and manage records within the authenticated user's authorized scope.
- **Cloud storage:** Store evidence in a private Supabase Storage bucket.
- **Automated testing:** Maintain tests for core application services and supporting functionality.

## Technology Stack

- Python
- Streamlit
- Supabase Authentication
- Supabase PostgreSQL
- Supabase Storage
- `python-docx`
- `pytest`

## Project Structure

| File or directory | Purpose |
|---|---|
| `cloud_app.py` | Cloud application entry point |
| `auth_helpers.py` | Authentication and Supabase client helpers |
| `cloud_data_service.py` | Project and observation data operations |
| `evidence_service.py` | Evidence metadata and storage operations |
| `evidence_helpers.py` | Evidence validation and storage-path helpers |
| `supabase/migrations/` | Database schema migration files |
| `tests/` | Automated tests |
| `requirements.txt` | Python dependencies |

Additional modules support observation models, filtering, reporting, and WhatsApp digest workflows.

## Local Setup

### 1. Requirements

Install Python 3.11 or newer and Git.

### 2. Clone the repository

```powershell
git clone https://github.com/Seek-Techs/ConstructionSiteAssistant_Supabase.git
cd ConstructionSiteAssistant_Supabase
```

### 3. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 5. Configure Supabase credentials

Create a local file named `.streamlit/secrets.toml` with the following settings:

```toml
SUPABASE_URL = "https://YOUR_PROJECT_REF.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "YOUR_SUPABASE_PUBLISHABLE_KEY"
```

Replace the placeholders with the appropriate values from your Supabase project.

**Security:** Never commit `.streamlit/secrets.toml`, passwords, access tokens, or Supabase service-role keys to Git. Use the publishable key with the application's configured authentication and database access policies.

### 6. Run the application

```powershell
python -m streamlit run cloud_app.py
```

Streamlit will provide a local address for opening the application in a browser.

## Supabase Configuration

The application requires a configured Supabase project with the database tables, access policies, and private storage buckets expected by the application.

Database schema changes are documented under `supabase/migrations/`. Apply migrations only when setting up or intentionally updating the database schema, and verify the target database before executing any migration.

Do not rerun migrations against an already configured database without checking their status and purpose.

## Deployment

The cloud entry point is `cloud_app.py`.

To deploy using Streamlit Community Cloud:

1. Push the application code to the GitHub repository.
2. Create a new app in Streamlit Community Cloud and select this repository.
3. Select the `master` branch and set the main file path to `cloud_app.py`.
4. Add `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY` under the app's Secrets settings.
5. Deploy and verify authentication, project creation, observation management, and evidence upload using a test account.

Keep all credentials in Streamlit's Secrets settings rather than in the repository.

## Testing

Run the automated test suite locally:

```powershell
python -m pytest -q
```

Review any failures before deploying changes.

## Development Principles

- Preserve confidentiality of site records and photographic evidence.
- Enforce authenticated, authorized access to project and observation data.
- Validate uploaded evidence and maintain appropriate metadata.
- Keep changes testable and reviewable.
- Avoid committing local databases, private evidence, credentials, or temporary backup files.

## Project Status

This project is under active development. Verify the deployed application's functionality and configuration before relying on it for operational site records.

## Current Limitations

The application is under active development. The following limitations should be considered when using or evaluating it:

- **Authentication persistence:** Users may need to sign in again after a browser refresh or a new session. Persistent sign-in improvements remain a future enhancement.
- **Cloud deployment:** Availability depends on the hosting platform, network connectivity, and Supabase service availability.
- **Feature parity:** The cloud version may not yet include every feature available in the original local application.
- **Reporting:** Advanced reporting, automated management summaries, and downloadable report options may require further integration and validation.
- **Notifications:** Automated reminders for overdue corrective actions and pending inspections are not yet confirmed as implemented.
- **Offline operation:** The cloud application requires network access and is not designed for full offline data entry and synchronization.
- **Audit and review workflows:** Further development may be required for comprehensive audit history, formal approval workflows, and controlled record revisions.
- **Production readiness:** Access policies, file-upload controls, backup and recovery procedures, and application behavior should be tested before the application is used as the sole recordkeeping system for critical site operations.

These limitations should be reviewed as development progresses. Actual availability depends on the deployed version.

## Future Development Roadmap

The following features are planned enhancements, subject to development priorities and testing.

### Phase 1 — Reliability and Security

- Improve authentication and session persistence.
- Strengthen error handling and user feedback.
- Expand automated tests for cloud workflows.
- Review database access policies and private file-storage permissions.
- Establish practical backup, recovery, and deployment procedures.

### Phase 2 — Site Records and Reporting

- Enhance Word and PDF report generation.
- Produce daily, weekly, and project-level management summaries.
- Improve observation search, filtering, and status tracking.
- Add configurable project, contractor, and reporting references.
- Improve evidence captions, categorization, and downloadable evidence records.

### Phase 3 — Follow-up and Management Workflows

- Add reminders for overdue actions and upcoming inspection dates.
- Introduce review, verification, and approval workflows.
- Maintain a more comprehensive history of record changes.
- Improve dashboards for outstanding observations, recurring issues, and contractor performance indicators.

### Phase 4 — Field Productivity and Integration

- Explore mobile-friendly field data entry and photo capture.
- Investigate offline capture with controlled synchronization.
- Add configurable export and data-import workflows.
- Explore integration with email, messaging, and project-management tools.

### Phase 5 — Construction Intelligence

- Develop project-level quality and HSE trend analysis.
- Identify recurring nonconformities and outstanding corrective actions.
- Explore analytics for progress monitoring and contractor reporting.
- Evaluate AI-assisted report drafting and observation classification, with human review before records are finalized.

## Roadmap and Release Policy

The roadmap describes intended development, not guaranteed delivery dates. Features will be introduced incrementally after implementation, testing, and security review.

The application should be evaluated against the features available in the specific deployed release. Future enhancements must not be treated as existing capabilities until they have been implemented and verified.
