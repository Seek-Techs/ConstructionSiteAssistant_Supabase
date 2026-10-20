# Construction Site Assistant

A personal, local application for recording construction site observations, managing follow-up actions, maintaining photographic evidence and preparing structured management reports.

## 1. Purpose

The Construction Site Assistant helps a construction site supervisor record, retrieve, organize and report site observations consistently.

It is intended to support contractor monitoring, quality control, HSE observations, progress reporting and follow-up action tracking.

## 2. Current Features

- Create, validate, save and edit site observations.
- Record the observation date, contractor, site, location, category and information source.
- Distinguish direct observations from contractor-reported information.
- Record required actions, responsible parties, due dates, status and verification notes.
- Search and filter saved observations.
- Maintain a project register and associate observations with projects.
- Upload and retrieve photographic evidence.
- Generate WhatsApp-ready observation text.
- Generate Word reports with a report-details table (project, site, contractor, date, optional reference), a management summary in tables, categorized observation tables, numbered and captioned photographs, a basis-of-report statement and a prepared-by / checked-by sign-off block.
- Add an optional caption to each photograph when recording an observation (one caption per line, in photo order). Without a caption the file name is used.
- Store observation records locally using SQLite.

## 3. Technology

- Python
- Streamlit
- SQLite
- python-docx
- pytest

## 4. Requirements

Install Python 3.11 or newer (developed on Python 3.13). Install the dependencies listed in `requirements.txt` into the project's virtual environment:

```powershell
python -m pip install -r requirements.txt
```

The application is developed for Windows. The automated tests were also run on Linux.

## 5. Running the Application

Open a terminal in the project directory.

Activate the existing virtual environment in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, use Command Prompt to activate the environment instead:

```bat
.venv\Scripts\activate.bat
```

Start the application:

```powershell
python -m streamlit run app.py
```

Streamlit will display a local address in the terminal. Open that address in your browser to use the application.

## 6. Running Tests

Activate the project's virtual environment and run:

```powershell
python -m pytest -q
```

If pytest is not installed in the active environment, run `python -m pip install -r requirements.txt` and try again.

All tests use temporary databases. They never read or change your real `observations.db`.

## 7. Local Data and Photographic Evidence

Observation records are stored in a local SQLite database. Photographic evidence is stored in local folders associated with observation records, while photo metadata is maintained in the database.

Keep the database and photographic evidence folders intact. Back up both before making changes to the application's storage structure or moving the project to another computer.

Backup in PowerShell (run from the project folder; the backup is a dated copy beside it):

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmm"
New-Item -ItemType Directory "..\ConstructionSiteAssistant_backup_$stamp" | Out-Null
Copy-Item observations.db "..\ConstructionSiteAssistant_backup_$stamp\"
Copy-Item photo_evidence "..\ConstructionSiteAssistant_backup_$stamp\" -Recurse
```

Photo records store the full file path used at upload time. If the project folder is moved to another location or computer, the application and reports find the photographs again by looking in the project's own `photo_evidence/<observation ID>/` folder, so keep `observations.db` and `photo_evidence/` together.

Observations created before projects were introduced have no project. Open the observation in the app and use "Link to Project". The application never guesses a project, and it will not change an observation that is already linked.

## 8. Reporting and Verification

Reports are generated from saved observations selected by the user.

The management summary in the Word report describes the selected observations; it does not necessarily represent every observation recorded for a project.

Direct observations and contractor-reported information must remain distinguishable. An action must not be represented as completed, and compliance must not be represented as verified, unless the relevant verification has occurred.

## 9. Current Limitations

This is a local, single-user MVP.

The current scope excludes:

- Multi-user accounts and access permissions.
- Cloud hosting and company-wide deployment.
- Automated WhatsApp message sending.
- AI-generated compliance decisions or inspection approvals.
- Complex enterprise project, contract, resource and cost management.
- Advanced dashboards beyond the basic operational views required by the MVP.

Automated reminders are also deferred.

## 10. Development Principles

- Implement one feature at a time.
- Understand the code before extending it.
- Test changes and investigate failures before proceeding.
- Preserve existing records when modifying the database.
- Record important technical decisions.
- Use fictional or anonymized information for testing.
- Do not present unverified information as independently verified.

## 11. Current Development Status

Core observation management, project association, photographic evidence and Word report generation are implemented. The automated test suite (48 tests) passes, including an end-to-end workflow test. The Word report has a running header, "Page X of Y" footer, a scope statement in the management summary, due dates, numbered photo captions and a sign-off block.

Not yet done: a manual run of the app in your own browser on Windows with your real data, and reviewing your older records' project links with the "Link to Project" control. See `docs/PROJECT_CONTEXT.md` for the verified status and known limitations.

The MVP should only be declared complete after those checks have passed.

## 12. Project Scope

Refer to the Project Spec for the original purpose, intended user, initial requirements, learning principles and revised MVP completion criteria.