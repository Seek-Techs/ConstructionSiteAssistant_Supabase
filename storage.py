from uuid import uuid4
import sqlite3
from pathlib import Path

from observation_model import SiteObservation


# The database file will be created beside this Python file.
DB_PATH = Path(__file__).with_name("observations.db")


from contextlib import contextmanager


@contextmanager
def database_connection(db_path):
    """Manage a SQLite transaction and always close the connection."""
    connection = sqlite3.connect(db_path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

def initialize_database(db_path=DB_PATH):
    """Create the observations table if it does not already exist."""

    with database_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                observation_id TEXT PRIMARY KEY,
                report_date TEXT NOT NULL,
                site TEXT NOT NULL,
                location TEXT NOT NULL,
                contractor TEXT NOT NULL,
                category TEXT NOT NULL,
                information_source TEXT NOT NULL,
                description TEXT NOT NULL,
                required_action TEXT NOT NULL,
                responsible_party TEXT NOT NULL,
                status TEXT NOT NULL,
                verification_notes TEXT NOT NULL,
                due_date TEXT NOT NULL DEFAULT ''

            )
            """
              
        )
        connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS projects (
                        project_code TEXT PRIMARY KEY,
                        project_name TEXT NOT NULL,
                        location TEXT NOT NULL
                    )
                    """
                )
                  
        
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(observations)"
            ).fetchall()
        }

        if "due_date" not in columns:
            connection.execute(
                """
                ALTER TABLE observations
                ADD COLUMN due_date TEXT NOT NULL DEFAULT ''
                """
            )
        if "project_code" not in columns:
            connection.execute(
                """
                ALTER TABLE observations
                ADD COLUMN project_code TEXT NOT NULL DEFAULT ''
                """
            )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS observation_photos (
                photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                observation_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                FOREIGN KEY (observation_id)
                    REFERENCES observations (observation_id)
            )
            """
        )

        photo_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(observation_photos)"
            ).fetchall()
        }

        if "caption" not in photo_columns:
            connection.execute(
                """
                ALTER TABLE observation_photos
                ADD COLUMN caption TEXT NOT NULL DEFAULT ''
                """
            )


def save_project(project_code, project_name, location, db_path=DB_PATH):
    initialize_database(db_path)

    project_code = project_code.strip()
    project_name = project_name.strip()
    location = location.strip()

    if not project_code or not project_name or not location:
        raise ValueError(
            "Project code, project name and location are required."
        )

    with database_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO projects (
                project_code,
                project_name,
                location
            )
            VALUES (?, ?, ?)
            """,
            (project_code, project_name, location),
        )


def get_projects(db_path=DB_PATH):
    initialize_database(db_path)

    with database_connection(db_path) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT project_code, project_name, location
            FROM projects
            ORDER BY project_code
            """
        ).fetchall()

    return [dict(row) for row in rows]



def save_observation(observation, db_path=DB_PATH):
    initialize_database(db_path)

    with database_connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO observations (
                observation_id,
                report_date,
                site,
                location,
                contractor,
                category,
                information_source,
                description,
                required_action,
                responsible_party,
                status,
                verification_notes,
                due_date,
                project_code
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                observation.observation_id,
                observation.report_date,
                observation.site,
                observation.location,
                observation.contractor,
                observation.category,
                observation.information_source,
                observation.description,
                observation.required_action,
                observation.responsible_party,
                observation.status,
                observation.verification_notes,
                observation.due_date,
                observation.project_code,
            ),
        )


def save_observation_photo(
    observation_id,
    file_path,
    original_filename,
    db_path=DB_PATH,
    caption="",
):
    """Save a photo's file reference against an observation."""

    initialize_database(db_path)

    with database_connection(db_path) as connection:
        exists = connection.execute(
            "SELECT 1 FROM observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()

        if exists is None:
            raise ValueError("Observation not found")

        connection.execute(
            """
            INSERT INTO observation_photos (
                observation_id,
                file_path,
                original_filename,
                caption
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                observation_id,
                str(file_path),
                original_filename,
                (caption or "").strip(),
            ),
        )

def get_observations(db_path=DB_PATH):
    """Retrieve saved observations, oldest first."""

    initialize_database(db_path)

    with database_connection(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT *
            FROM observations
            ORDER BY rowid
            """
        ).fetchall()

    return [
        SiteObservation(**dict(row))
        for row in rows
    ]


def get_observation_photos(
    observation_id,
    db_path=DB_PATH,
):
    """Retrieve photo records associated with one observation."""

    initialize_database(db_path)

    with database_connection(db_path) as connection:
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT photo_id, observation_id, file_path,
                   original_filename, caption
            FROM observation_photos
            WHERE observation_id = ?
            ORDER BY photo_id
            """,
            (observation_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def next_observation_id(db_path=DB_PATH):
    """Generate the next sequential observation ID."""

    observations = get_observations(db_path)

    highest_number = 0

    for observation in observations:
        try:
            number = int(observation.observation_id.removeprefix("OBS-"))
            highest_number = max(highest_number, number)
        except ValueError:
            continue

    return f"OBS-{highest_number + 1:04d}"


def update_observation_status(
    observation_id,
    status,
    verification_notes,
    db_path=DB_PATH,
):
    """Update an observation's status and verification notes."""

    allowed_statuses = {"Open", "In Progress", "Closed"}

    if status not in allowed_statuses:
        raise ValueError("Invalid observation status")

    if not isinstance(verification_notes, str):
        raise ValueError("Verification notes must be text")

    if status == "Closed" and not verification_notes.strip():
        raise ValueError(
            "Verification notes are required before closing an observation"
        )

    initialize_database(db_path)

    with database_connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE observations
            SET status = ?, verification_notes = ?
            WHERE observation_id = ?
            """,
            (status, verification_notes.strip(), observation_id),
        )

        if cursor.rowcount == 0:
            raise ValueError("Observation not found")


def update_observation(observation, db_path=DB_PATH):
    """Edit observation details without changing its ID or follow-up status."""

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE observations
            SET
                report_date = ?,
                site = ?,
                location = ?,
                contractor = ?,
                category = ?,
                information_source = ?,
                description = ?,
                required_action = ?,
                responsible_party = ?,
                due_date = ?
            WHERE observation_id = ?
            """,
            (
                observation.report_date,
                observation.site,
                observation.location,
                observation.contractor,
                observation.category,
                observation.information_source,
                observation.description,
                observation.required_action,
                observation.responsible_party,
                observation.due_date,
                observation.observation_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError("Observation not found")

def store_uploaded_photo(
    observation_id,
    uploaded_file,
    db_path=DB_PATH,
    caption="",
):
    """Save an uploaded image file and register it against an observation."""

    allowed_extensions = {".jpg", ".jpeg", ".png"}

    original_filename = Path(uploaded_file.name).name
    extension = Path(original_filename).suffix.lower()

    if extension not in allowed_extensions:
        raise ValueError("Only JPG, JPEG, and PNG images are allowed.")

    photo_folder = (
        Path(db_path).parent
        / "photo_evidence"
        / observation_id
    )
    photo_folder.mkdir(parents=True, exist_ok=True)

    photo_path = photo_folder / f"{uuid4().hex}{extension}"

    try:
        with photo_path.open("xb") as photo_file:
            photo_file.write(uploaded_file.getvalue())

        save_observation_photo(
            observation_id=observation_id,
            file_path=str(photo_path),
            original_filename=original_filename,
            db_path=db_path,
            caption=caption,
        )
    except Exception:
        photo_path.unlink(missing_ok=True)
        raise

    return str(photo_path)


def resolve_photo_path(photo, db_path=DB_PATH):
    """Return the Path of a photo file, or None if it cannot be found.

    Photo records store the full path that was valid when the photo was
    uploaded. If the project folder is later moved or copied to another
    computer, that stored path stops working. In that case we look for
    the same file inside this project's own photo_evidence folder, using
    the observation ID and the stored file name. The stored record is not
    changed.
    """

    stored_path = Path(photo["file_path"])

    if stored_path.is_file():
        return stored_path

    fallback = (
        Path(db_path).parent
        / "photo_evidence"
        / photo["observation_id"]
        / stored_path.name
    )

    if fallback.is_file():
        return fallback

    return None


def assign_project_to_observation(
    observation_id,
    project_code,
    db_path=DB_PATH,
):
    """Link an older observation to a registered project.

    This only fills in a missing project code. It refuses to overwrite an
    existing association, and the project must exist in the register, so
    historical records cannot be re-assigned by accident.
    """

    initialize_database(db_path)

    with sqlite3.connect(db_path) as connection:
        project = connection.execute(
            "SELECT 1 FROM projects WHERE project_code = ?",
            (project_code,),
        ).fetchone()

        if project is None:
            raise ValueError("Project not found in the register")

        row = connection.execute(
            "SELECT project_code FROM observations WHERE observation_id = ?",
            (observation_id,),
        ).fetchone()

        if row is None:
            raise ValueError("Observation not found")

        if row[0]:
            raise ValueError(
                "Observation is already linked to a project"
            )

        connection.execute(
            """
            UPDATE observations
            SET project_code = ?
            WHERE observation_id = ?
            """,
            (project_code, observation_id),
        )
