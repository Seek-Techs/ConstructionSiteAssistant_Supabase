# Construction Site Assistant

## 1. Purpose

Build a personal application that helps a construction site supervisor record, retrieve, organize and report site observations and follow-up actions.

## 2. Intended user

A construction site supervisor responsible for contractor monitoring, quality control, HSE observations and progress reporting.

## 3. First problem to solve

Site observations and follow-up actions need to be recorded consistently so that important information can be retrieved and included in management reports.

## 4. First version

The application must allow the user to:

1. Record a site observation.
2. Identify the date, contractor, location and category.
3. Distinguish direct observations from contractor-reported information.
4. Record the required follow-up and current status.
5. Save and retrieve observation records.
6. Generate a structured report from saved records.

## 5. Initial limitations

- The application is for personal use.
- Test with fictional or anonymized information.
- Records must not be presented as independently verified unless verification has occurred.
- Photographic uploads, automated reminders, dashboards and cloud deployment are outside the first milestone.

## 6. Initial technology

- Python
- Streamlit
- Local data storage

## 7. Definition of success

A user can create an observation, save it, retrieve it after reopening the application, and produce a report containing the correct information.

## 8. Learning principle

Implement one feature at a time. Understand the code, test its behaviour and record important technical decisions before adding complexity.


## 9. Revision 1.1 — Current MVP Scope and Implementation Status

### 9.1 Updated purpose

The application remains a personal, local tool for recording site observations, maintaining supporting evidence, tracking corrective actions and preparing structured management reports.

The original purpose and learning principle remain unchanged.

### 9.2 Features implemented

The application currently includes:

- Creating, validating, saving, retrieving and editing site observation records.
- Recording observation dates, contractors, locations, categories, information sources, descriptions and required actions.
- Tracking responsible parties, due dates, status and verification notes.
- Searching and filtering observation records and selecting records for reports.
- Maintaining a project register and associating observations with projects.
- Uploading and retrieving photographic evidence linked to observations.
- Generating WhatsApp-ready text and Word reports from saved records.
- Including project details, a management summary, categorized observations and photographic evidence in Word reports.
- Storing observation records in a local SQLite database and photographic files in local folders.

### 9.3 Reporting rules

Reports must distinguish direct observations from information reported by contractors. Records must not imply that corrective actions have been completed or that compliance has been verified unless the relevant verification has taken place.

The Word report's management summary counts the observations selected for that report, not necessarily every observation recorded for the project.

### 9.4 Current limitations

The application remains a local, single-user MVP. The following are outside the current scope:

- Multi-user accounts, access permissions and simultaneous shared access.
- Cloud hosting and company-wide deployment.
- Automated WhatsApp message sending.
- AI-generated compliance decisions or automated inspection approvals.
- Complex enterprise-level project, contract, resource or cost management.
- Advanced dashboards beyond the basic operational views required by the MVP.

Automated reminders are also deferred unless introduced as a separate, approved milestone.

### 9.5 Remaining MVP completion checks

Before declaring the MVP complete:

1. Finalize and review Word report layout, including page numbering, headers, footers and photographic presentation.
2. Run the available regression tests and resolve any failures.
3. Test a realistic end-to-end workflow: create an observation, save it, close and reopen the application, retrieve and edit the record, track its action status, attach photographs and generate a report.
4. Review older observation records whose project associations may be empty, and restore associations where the correct project can be established.
5. Confirm that report content accurately reflects saved records and selected observations.
6. Document setup instructions, testing commands, known limitations and important technical decisions.

### 9.6 Definition of MVP completion

The MVP will be considered complete when its core observation-management workflow works reliably, records persist after restarting the application, photographic evidence can be retrieved, reports contain the correct information, and the available tests pass.

Completion of this milestone does not mean the application is ready for multi-user or commercial deployment.

### 9.7 Future direction

A commercial, multi-company product may be considered after the personal MVP has been tested and its usefulness demonstrated. Any move toward that goal will require a separate assessment of user needs, security, data separation, deployment, maintenance and commercial viability.