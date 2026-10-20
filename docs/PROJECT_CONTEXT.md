# Construction Site Assistant
## Master Project Brief, Development History and AI Handover

**Document purpose:** Provide a single, self-contained reference explaining the project's intention, requirements, current implementation, technical decisions, development principles, limitations and future direction.

**Project type:** Personal construction site supervision and documentation application.

**Current stage:** Local Python and Streamlit MVP development and verification.

**Primary development environment:** Windows.

---

# 1. Executive Summary

The Construction Site Assistant is a personal software application being developed to support the daily work of a construction site supervisor.

The application addresses a practical problem in construction supervision: site observations, contractor activities, quality issues, health and safety concerns, photographic evidence, corrective actions and follow-up decisions need to be recorded consistently and retrieved when required for management reporting.

The initial goal is not to build a large construction management platform. It is to build a dependable, useful application that solves a real documentation problem in the supervisor's existing workflow.

The application is being developed incrementally using Python, Streamlit and SQLite. It currently supports observation management, project association, photographic evidence, action tracking and report generation.

The longer-term vision is to explore how the application could evolve into a more comprehensive digital construction supervision tool. Any commercial or multi-company version must be considered separately after the personal MVP has been tested and its usefulness demonstrated.

The project also has an educational purpose: the owner wants to understand professional software development, not merely receive code that works.

# 2. Why the Project Exists

Construction supervision generates information that must remain traceable and useful beyond the moment it is observed.

Examples include:

- Quality defects and work that requires correction.
- HSE violations and unsafe site conditions.
- Traffic management and equipment-related observations.
- Contractor progress and activities completed or outstanding.
- Photographs documenting site conditions.
- Required corrective actions and responsible parties.
- Follow-up inspections and verification of corrective work.
- Information required for daily updates and management reports.

When these records are inconsistent, scattered across messages or difficult to retrieve, the supervisor may struggle to establish what happened, what action was requested, who is responsible and whether the issue has been resolved.

The application is intended to create a structured record of this information.

Its central purpose is:

**Record what happened, preserve the supporting evidence, identify the required action, track its status and produce an accurate report when needed.**

It should support professional judgment and documentation. It must not replace engineering judgment, authorized inspections, surveying, contractual procedures or management decisions.

# 3. Intended User and Operating Context

## Primary user

A construction site supervisor responsible for contractor monitoring, quality control, HSE observations, progress reporting and follow-up actions.

## Initial operating model

- One user.
- One local computer.
- A local application accessed through a web browser.
- Local database and file storage.
- Reports generated from records selected by the user.

The application is initially designed around practical construction supervision activities rather than the administrative needs of a large construction company.

The workflow should remain simple enough to use during normal site operations.

# 4. Original Project Specification

The original specification established the following requirements.

## Purpose

Build a personal application that helps a construction site supervisor record, retrieve, organize and report site observations and follow-up actions.

## First problem to solve

Site observations and follow-up actions need to be recorded consistently so important information can be retrieved and included in management reports.

## Minimum required capabilities

1. Record a site observation.
2. Identify the date, contractor, location and category.
3. Distinguish direct observations from contractor-reported information.
4. Record the required follow-up and current status.
5. Save and retrieve observation records.
6. Generate a structured report from saved records.

## Original limitations

The application was initially restricted to personal use, with fictional or anonymized information for testing.

The first milestone excluded photographic uploads, automated reminders, dashboards and cloud deployment.

These exclusions applied to the initial milestone. Photographic evidence and basic operational views were subsequently added as the project developed. Their addition did not change the underlying purpose of the application.

## Initial technology

- Python.
- Streamlit.
- Local data storage.

## Original definition of success

A user can create an observation, save it, retrieve it after reopening the application and produce a report containing the correct information.

## Learning principle

Implement one feature at a time. Understand the code, test its behaviour and record important technical decisions before adding complexity.

# 5. Core Design Principles

The following principles should guide all future development.

### 5.1 Documentation must be traceable

Records should preserve the difference between what the supervisor personally observed and what another party reported.

### 5.2 Evidence and verification are different

A photograph may document a condition, but it does not automatically establish compliance or prove that corrective action has been completed.

### 5.3 Corrective actions must remain accountable

Where applicable, records should identify the required action, responsible party, due date, status and verification notes.

### 5.4 Reports must reflect saved information

Reports should be generated from actual saved records. They must not silently invent missing details or represent unverified claims as established facts.

### 5.5 Preserve historical records

Changes to database structure must not unnecessarily destroy existing observations, photographs, project associations or follow-up history.

### 5.6 Build incrementally

Each feature should be implemented, understood and tested before unnecessary complexity is introduced.

### 5.7 Practical value comes before feature count

A feature should solve a real problem in the supervisor's workflow. The project should not become more complicated merely to appear more advanced.

# 6. Current Technical Architecture

## Technologies

| Component | Technology | Purpose |
|---|---|---|
| Programming language | Python | Application logic and data processing |
| User interface | Streamlit | Forms, controls, search, filtering and display |
| Database | SQLite | Persistent local structured records |
| Word reports | python-docx | Creating downloadable Word documents |
| Testing | pytest | Automated checks of application behaviour |
| Evidence storage | Local file system | Photographic evidence associated with observations |

## Main components

The project includes the following known files and directories:

- `app.py` — main Streamlit application and user interface.
- `storage.py` — database operations and persistent storage logic.
- `word_report_builder.py` — generation of structured Word reports.
- `tests/` — automated tests.
- `photo_evidence/` — local photographic evidence files.
- The SQLite database — persistent observation and related application data.
- `Project Spec` — original project requirements and the revision documenting current scope.
- `README.md` — setup, execution, testing and usage documentation.

The exact database filename, complete directory structure, dependency manifest and current contents of all files must be verified from the project itself rather than assumed.

## General data flow

1. The user enters information through the Streamlit interface.
2. The application validates the submitted information.
3. Storage functions save or retrieve records from SQLite.
4. Photographs are stored locally, with associated metadata in the database.
5. The user searches, filters, edits or selects records.
6. The report builder generates a text or Word output from the selected records.

Changes to these components should respect their responsibilities. For example, report formatting should primarily be handled in `word_report_builder.py`, rather than implemented as unrelated formatting logic throughout the interface.

# 7. Observation Data Model

The current observation model is represented by the following Python dataclass:

```python
@dataclass
class SiteObservation:
    observation_id: str
    report_date: str
    site: str
    location: str
    contractor: str
    category: str
    information_source: str
    description: str
    required_action: str
    responsible_party: str
    status: str = "Open"
    verification_notes: str = ""
    due_date: str = ""
    project_code: str = ""
```

The exact implementation in the current source code remains authoritative.

The fields serve these purposes:

- `observation_id`: identifies an observation.
- `report_date`: records the date associated with the observation.
- `site`: identifies the site.
- `location`: identifies the relevant work area or chainage.
- `contractor`: identifies the contractor involved.
- `category`: classifies the observation.
- `information_source`: identifies whether the information came from direct observation or a contractor report.
- `description`: records the observed or reported condition.
- `required_action`: states the follow-up action required.
- `responsible_party`: identifies who is responsible for the action.
- `status`: records the current action status.
- `verification_notes`: records relevant follow-up or verification findings.
- `due_date`: records the action deadline when applicable.
- `project_code`: links the observation to a registered project.

The application should preserve valid existing identifiers during edits. Editing an observation should not accidentally create a new observation or erase its action status and verification notes.

# 8. Implemented Features

The following features have been developed during the project. They should still be tested against the current source code before a release or formal completion claim.

## 8.1 Observation management

- Create and validate observations.
- Save records to SQLite.
- Retrieve records after restarting the application.
- Edit existing records.
- Preserve observation identifiers during edits.
- Record descriptions, required actions, responsible parties and statuses.
- Record verification notes and due dates.

## 8.2 Search and retrieval

- Search saved observations.
- Filter records.
- Select observations for reporting.
- Retrieve records without relying solely on temporary application-session state.

## 8.3 Project register

- Maintain a register of projects.
- Associate observations with a project using a project code.
- Display project details in the report where available.

Known example from development: project code `N2_ZTL`, project name `Land reclamation`, project location `N2`.

This example is a development record, not a default project that should be hardcoded into the application.

## 8.4 Photographic evidence

- Upload multiple supported image files, including JPG, JPEG and PNG.
- Store photographs in folders associated with observation identifiers.
- Store photograph metadata in the `observation_photos` database table.
- Retrieve and display photographs associated with saved observations.
- Include photographs in Word reports with filenames used as captions.

Photographic storage and database metadata must remain consistent. Database changes or file movement should be handled carefully to avoid broken evidence links.

## 8.5 Report generation

The application can produce WhatsApp-ready text and Word reports.

The Word report includes:

- A management summary.
- Project details where available.
- Selected observation information.
- Categorized observation sections.
- Action and status information.
- Photographic evidence and captions.

The management summary counts observations in the current report selection. It is not necessarily a complete project-wide summary.

The summary has included total selected observations, category counts for Quality, HSE, Traffic and Other, and counts for Open, In Progress and Closed statuses.

The implementation should be checked to confirm how it handles additional categories, missing project details and empty selections.

# 9. Database History and Important Decisions

The project has evolved from an initial observation-recording tool into a more capable local application.

## 9.1 Persistent storage

SQLite replaced the initial concept of keeping records only for the current session. Persistent storage is necessary because site records must remain available after the application closes.

## 9.2 Project association migration

The observations table originally lacked the `project_code` column.

A migration was added to introduce the field to an existing database:

```python
if "project_code" not in columns:
    connection.execute(
        """
        ALTER TABLE observations
        ADD COLUMN project_code TEXT NOT NULL DEFAULT ''
        """
    )
```

The `save_observation()` operation was also updated to include `project_code` when inserting records.

This change is important because adding a field to a Python dataclass alone does not add that field to an existing SQLite database.

Older records may have an empty project code. These associations should be restored only when the correct project can be established. They should not be guessed.

## 9.3 General migration rule

For future database changes:

1. Inspect the current database schema.
2. Identify how existing records will be affected.
3. Add a controlled migration.
4. Test both new and existing records.
5. Verify that the user can still retrieve historical data.

Do not delete the database and recreate it as a shortcut for resolving schema problems.

# 10. Reporting Integrity and Construction-Specific Requirements

The application supports documentation; it does not independently certify construction work.

Reports and records must preserve these distinctions:

- Directly observed versus contractor-reported information.
- Observed condition versus suspected cause.
- Required corrective action versus completed corrective action.
- Contractor-reported completion versus independently verified completion.
- Photograph available versus compliance demonstrated.
- Inspection requested versus inspection conducted.
- Inspection conducted versus formal approval or sign-off.

Where verification is outstanding, the record should explicitly indicate that it remains outstanding.

Where a follow-up inspection is required, the application should support a clear action and status rather than implying the issue has been resolved.

The application must not invent technical requirements, tolerances, contractual obligations or penalties. Such details must come from the relevant drawings, specifications, approved method statements, inspection requirements or contractual documents supplied by authorized parties.

# 11. Current Scope Boundaries

## Included in the personal MVP

- Observation creation and editing.
- Data validation and persistent storage.
- Search, filtering and retrieval.
- Project registration and association.
- Follow-up action tracking.
- Photographic evidence.
- Basic operational views and dashboard functionality already developed.
- WhatsApp-ready text.
- Word report generation.
- Automated tests and project documentation.

## Not included in the current MVP

- Multi-user accounts and role-based permissions.
- Simultaneous shared access by several supervisors.
- Cloud-hosted or company-wide deployment.
- Automated WhatsApp sending.
- AI-generated engineering approvals or automatic compliance decisions.
- Enterprise contract administration.
- Full BOQ, valuation, payment certification or cost-control systems.
- Comprehensive resource planning and contractor scheduling.
- Complex enterprise dashboards.
- Automated reminders unless separately approved as a future milestone.

A feature is not part of the current scope simply because it could be useful in a construction application.

New features should be assessed against the immediate user problem, development effort, reliability and maintenance requirements.

# 12. Future Product Vision

The long-term vision is to explore whether the Construction Site Assistant can become a broader digital construction supervision platform.

This is a direction to investigate, not a claim that these capabilities have already been built or validated.

## 12.1 Stronger observation and action management

Potential improvements include:

- A clearer action register across multiple observations.
- Overdue and upcoming action identification.
- More explicit action histories.
- Follow-up inspection records.
- Links between original observations, corrective actions and verification evidence.
- More flexible reporting periods and project-level summaries.

These features should be prioritized only when testing identifies a real workflow need.

## 12.2 More complete construction records

Potential future capabilities include:

- Daily site reports.
- Contractor daily work plans and progress reports.
- Manpower and equipment records.
- Material delivery records.
- Inspection requests and inspection outcomes.
- Non-conformance reports.
- Toolbox talks and safety observations.
- Progress updates supported by photographs.
- Lookahead activities and delay records.

These functions would expand the application beyond its current observation-management scope. Each should be assessed as a separate feature or milestone.

## 12.3 Better project-level reporting

Possible future improvements include:

- Reports for a selected project and reporting period.
- Open and overdue action summaries.
- Category and contractor breakdowns.
- Progress and issue trend reporting.
- More flexible report templates.
- Export formats suited to management and site documentation workflows.

Summary calculations must have clearly defined populations and date ranges so users understand what is being counted.

## 12.4 Assistance from AI

AI may eventually help users organize information, draft reports or summarize existing records.

Potential examples include:

- Turning structured notes into clearer report wording.
- Drafting a management summary from verified records.
- Identifying missing documentation fields.
- Highlighting unresolved actions.
- Searching records using natural language.

Any such feature must preserve the source information and distinguish generated text from verified facts.

AI should not independently approve work, certify compliance, decide contractual liability or replace authorized professional judgment.

## 12.5 Multi-user and commercial possibility

A commercial version may eventually require:

- Multiple companies and projects.
- Authentication and role-based permissions.
- Strong separation of company data.
- Secure file storage and backups.
- Audit trails.
- Deployment and maintenance procedures.
- Data recovery and retention policies.
- Clear ownership and access rules.
- Reliability, security and performance testing.
- Evidence of demand and willingness to pay.

These requirements are materially different from those of a local single-user application.

The current database and architecture should not be described as production-ready for multiple companies without a dedicated assessment and appropriate redesign.

## 12.6 Commercial validation principle

The project should not assume that a technically successful application automatically represents a viable business.

Before significant investment in a commercial product, investigate:

1. Whether construction supervisors experience the problem frequently.
2. How they currently manage observations, evidence and follow-up.
3. Which existing tools they use.
4. What is missing from their current workflow.
5. Whether a new application provides measurable value.
6. Whether the intended users or organizations would pay for it.
7. Whether security, deployment and support costs are justified.

A decision not to commercialize the application is acceptable if evidence does not support the opportunity.

# 13. Development and Learning Approach

The owner wants to learn how to build professional software with AI assistance.

The objective is not merely to make the application run. The owner should understand why the code exists, how data flows through the application, how to test changes and how to diagnose errors.

The preferred development approach is:

1. Define one specific problem.
2. Identify the smallest useful implementation.
3. Explain the relevant concepts in beginner-friendly language.
4. Make a focused code change.
5. Explain exactly where the change belongs.
6. Run the application or a targeted test.
7. Review the result.
8. Correct any failure before proceeding.
9. Record important technical decisions.
10. Update documentation when the behavior or scope changes.

When a faster solution is requested, code can be provided directly, but important design choices and consequences should still be explained.

Avoid large, unexplained code replacements. Preserve working functionality and existing records.

# 14. Current Documentation

The documentation should have distinct responsibilities.

## Project Spec

Records the original purpose, intended user, initial requirements, learning principle, revised scope and definition of completion.

## README.md

Explains what the application does, its technologies, setup, how to run it, how to test it, storage considerations and known limitations.

## PROJECT_CONTEXT.md

This document provides the broader project history, design rationale, implementation status, scope boundaries, future vision and handover instructions for another developer or AI agent.

## Future technical documentation

As needed, add focused documents for:

- Database schema and migrations.
- Architecture and data flow.
- Testing strategy.
- Important technical decisions.
- Release and backup procedures.

Do not create documentation merely to increase the number of files. Each document should have a clear purpose.

# 15. Current Status and Outstanding Work

The application has implemented its principal observation-management workflow, project association, photographic evidence and Word report generation.

However, feature implementation is not the same as verified completion.

The following checks remain part of the agreed completion process:

1. Finalize and review the Word report layout, including page numbering, headers, footers and photographic presentation.
2. Run the regression test suite and resolve failures.
3. Complete a realistic end-to-end test.
4. Review historical observations with missing project associations.
5. Verify report content, summary counts, selected-record behavior and evidence retrieval.
6. Confirm that setup and testing instructions match the actual project.
7. Complete and review the project documentation.

A previous development checkpoint reported five passing tests, while an earlier checkpoint reported a larger suite. The current authoritative test count must be established by running the tests in the current virtual environment.

If `python -m pytest -q` reports that pytest is not installed, verify that the correct virtual environment is active before changing dependencies or modifying the application.

## Suggested end-to-end test

Use fictional or anonymized data to:

1. Create a project.
2. Create an observation linked to that project.
3. Record its category, information source and required action.
4. Save the observation.
5. Close and restart the application.
6. Retrieve the saved record.
7. Edit it and confirm the identifier and existing action details remain correct.
8. Add photographic evidence.
9. Update the action status and verification notes.
10. Select the observation for a report.
11. Generate the Word report.
12. Open the report and verify the project details, management summary, observation information and photographs.
13. Confirm that the report does not claim verification or completion without supporting information.

After this test, document any failures and resolve them before declaring the MVP complete.

# 16. Definition of MVP Completion

The personal MVP is ready for its completion review when:

- Observations can be created, validated, saved, retrieved and edited reliably.
- Records persist after restarting the application.
- Project associations work correctly.
- Follow-up actions and statuses remain accurate.
- Photographic evidence can be stored and retrieved.
- Reports accurately represent the selected saved records.
- Existing records survive database changes.
- The available automated tests pass.
- The main end-to-end workflow succeeds.
- Documentation matches the actual implementation.
- Known limitations are explicitly recorded.

Completion means the agreed personal workflow is reliable. It does not mean the application is ready for cloud deployment, multi-user access or commercial release.

# 17. Instructions for Future AI Agents

An AI agent continuing this project should follow these rules.

### First: establish the current state

Inspect the actual project files and relevant database schema before making assumptions about the code, features or storage structure.

Use this document as background context, not as proof that every described feature still works in the current version.

### Second: preserve existing work

Do not replace the application wholesale, delete the SQLite database, recreate records unnecessarily or remove existing features to simplify a change.

Inspect relevant functions and tests before editing them.

### Third: work incrementally

Explain the objective of each change, identify the file and function to modify, make a focused change and ask the owner to test it where appropriate.

### Fourth: protect record integrity

Pay particular attention to database migrations, observation identifiers, project codes, action statuses, verification notes, photograph metadata and the relationship between database records and stored files.

### Fifth: test the actual behavior

Run relevant automated tests and, where needed, manual end-to-end tests. Report what passed, what failed and what has not yet been tested.

Do not claim success solely because code was written.

### Sixth: distinguish facts from plans

When describing the project, separate:

- Implemented features.
- Features verified by tests.
- Features that need additional verification.
- Planned improvements.
- Long-term possibilities.

Do not describe future ideas as existing capabilities.

### Seventh: preserve the learning objective

The owner wants to understand the application and the reasoning behind technical decisions. Avoid unexplained code dumps and unnecessary complexity.

### Eighth: maintain scope discipline

Prioritize completing and verifying the personal MVP before starting cloud deployment, multi-user features, AI compliance features or commercial product development.

### Ninth: maintain documentation

Update the README, Project Spec or this handover document when a meaningful change affects setup, requirements, architecture, scope, known limitations or development status.

### Tenth: ask when information is missing

Do not invent database filenames, environment variables, dependencies, file paths, business requirements or current test results. Inspect the project or ask the owner when the missing information materially affects the work.

# 18. Immediate Next Steps

Follow this sequence unless inspection of the current project reveals a more urgent defect:

1. Save this document as `PROJECT_CONTEXT.md`.
2. Confirm that `README.md` has been created and saved.
3. Inspect the project structure and dependency files.
4. Verify the virtual environment and test dependencies.
5. Run the existing regression tests.
6. Review and improve the Word report layout.
7. Perform the realistic end-to-end test.
8. Investigate missing project associations in older records.
9. Update documentation to reflect the verified state.
10. Conduct an MVP completion review before defining the next milestone.

# 19. Final Project Principle

The Construction Site Assistant should grow from a useful, reliable construction supervision workflow—not from an assumption that more features automatically make a better product.

The immediate objective is to build a tool that helps a supervisor maintain accurate records, preserve evidence, track follow-up actions and produce dependable management reports.

The longer-term objective is to learn from real use, improve the application carefully and determine whether its value justifies broader development.

**Build the useful tool first. Verify that it works. Learn from actual use. Expand only when the evidence supports it.**

---

# 20. Verified Status (updated 2026-10-19)

Verified by inspecting the code and running it on Linux with Python 3.13 and fictional data. Not yet verified on the owner's Windows machine or with the real database.

## Verified by automated tests (48 passing)

- Observation validation, save, retrieve, edit (ID, status, notes and project preserved), status updates and the rule that closing needs verification notes.
- Migration of an old database (no `due_date`, `project_code` or photo table) with no data loss.
- Project register, and assigning a project to an older observation only when it has none.
- Photo upload, storage, retrieval, and rejection of photos for unknown observations.
- Photos still found after the project folder is moved.
- Word report: contents, summary counts and scope note, project details, due dates, photo embedding, page numbering, unavailable or corrupt photos, categories outside the standard four.
- Full workflow: project, observation, edit, photos, status change, report, retrieval.

## Verified manually (rendered and inspected)

- Word report converted to PDF and checked visually: header, "Page X of Y" footer, observation blocks kept together, tall and wide photos fit the page.
- Streamlit app run headlessly (AppTest): loads without errors, dashboard counts, linking an older observation to a project, report downloads appear.

## Not verified

- Browser behaviour on Windows, real photo uploads from the browser, opening the report in Microsoft Word (checked in LibreOffice only), and the owner's real database.

## Changes made in this pass

- `word_report_builder.py`: now takes `db_path` (it previously always read the default `observations.db`, even when given other data); header and footer with page numbers; scope statement; due dates; photo size limit and keep-with-caption; unreadable photos no longer crash the report; unlisted categories are included.
- `report_builder.py`: unlisted categories are included.
- `storage.py`: `resolve_photo_path()`, `assign_project_to_observation()`, and a check that a photo's observation exists.
- `app.py`: removed the DEBUG output, shows project and due date, "Link to Project" control, uses `resolve_photo_path()`, replaced a deprecated Streamlit argument.
- Tests: the existing Word test now uses a temporary database; added `tests/test_end_to_end.py` and `tests/helpers.py`.
- Added `requirements.txt`. Updated `README.md`.

## Report presentation upgrade (2026-10-19, second pass)

- Word report rebuilt for a professional layout: report-details table, summary tables (by category and by status, with the selection-only scope note), one bordered table per observation, numbered photo captions ("Photo 1: ..."), "Basis of this Report" statement, and a Prepared by / Checked by block. Dates are shown as "20 Oct 2026". Contractor-reported items are labelled "not directly observed by the preparer".
- New optional photo caption (`observation_photos.caption`, added by a non-destructive migration; older photos have an empty caption and the file name is used instead).
- New optional report inputs in the app: report reference, prepared by, checked by.
- Rendered and inspected as PDF (LibreOffice). Microsoft Word rendering is not yet checked.

## Known limitations and risks

- Photo file paths are stored as absolute paths. The fallback lookup covers moved folders, but a future migration to relative paths would be cleaner.
- The observation is saved before its photos; if a photo fails, the observation remains saved and the app says so.
- SQLite foreign keys are not enforced by the database. The storage code checks photo ownership instead.
- Photo captions can only be entered when an observation is created; there is no screen yet to edit a caption afterwards.
- `report_exercise.py` and `test_observation_manual.py` are learning scripts in the project root. They are harmless but are not part of the application.
- Project code and name are not editable once created.

## Recommended next milestone

Run the owner's real workflow on Windows, link older observations to projects, then decide on the next feature from what that run shows.
