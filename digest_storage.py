
"""Persistent storage for WhatsApp digest review items.

This database is separate from the construction observations database.
"""

import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from digest_model import DigestItem, SiteDigest


DIGEST_DB_PATH = Path(__file__).with_name("whatsapp_digest.db")


def initialize_digest_database(db_path=DIGEST_DB_PATH):
    """Create the digest tables without changing existing site records."""
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS digest_batches (
                batch_id TEXT PRIMARY KEY,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS digest_items (
                item_id TEXT PRIMARY KEY,
                batch_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                sender TEXT,
                statement TEXT NOT NULL,
                category TEXT NOT NULL,
                evidence_source TEXT NOT NULL,
                source_line INTEGER NOT NULL,
                contractor TEXT,
                location TEXT,
                follow_up TEXT,
                review_status TEXT NOT NULL,
                FOREIGN KEY (batch_id)
                    REFERENCES digest_batches(batch_id)
            )
            """
        )


def save_digest(digest, batch_id, db_path=DIGEST_DB_PATH):
    """Save a digest and its review items as a new batch."""
    if not batch_id.strip():
        raise ValueError("Batch ID cannot be empty.")

    initialize_digest_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.execute(
            """
            INSERT INTO digest_batches (
                batch_id, start_date, end_date, created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                batch_id,
                digest.start_date.isoformat(),
                digest.end_date.isoformat(),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

        for index, item in enumerate(digest.items, start=1):
            item_id = f"{batch_id}-{index:04d}"

            connection.execute(
                """
                INSERT INTO digest_items (
                    item_id, batch_id, timestamp, sender, statement,
                    category, evidence_source, source_line, contractor,
                    location, follow_up, review_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    batch_id,
                    item.timestamp.isoformat(),
                    item.sender,
                    item.statement,
                    item.category,
                    item.evidence_source,
                    item.source_line,
                    item.contractor,
                    item.location,
                    item.follow_up,
                    item.review_status,
                ),
            )

    return batch_id


def get_digest_items(batch_id, db_path=DIGEST_DB_PATH):
    """Retrieve digest items, including saved review decisions."""
    initialize_digest_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT *
            FROM digest_items
            WHERE batch_id = ?
            ORDER BY timestamp, source_line
            """,
            (batch_id,),
        ).fetchall()

    return [
        DigestItem(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            sender=row["sender"],
            statement=row["statement"],
            category=row["category"],
            evidence_source=row["evidence_source"],
            source_line=row["source_line"],
            contractor=row["contractor"],
            location=row["location"],
            follow_up=row["follow_up"],
            review_status=row["review_status"],
        )
        for row in rows
    ]


def update_saved_digest_item(
    batch_id,
    item_index,
    item,
    db_path=DIGEST_DB_PATH,
):
    """Update review fields for one item without changing its source text."""
    initialize_digest_database(db_path)

    item_id = f"{batch_id}-{item_index:04d}"

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row

        existing = connection.execute(
            """
            SELECT * FROM digest_items
            WHERE item_id = ? AND batch_id = ?
            """,
            (item_id, batch_id),
        ).fetchone()

        if existing is None:
            raise ValueError("Digest item was not found.")

        # Only review fields are updated. Original message evidence stays fixed.
        connection.execute(
            """
            UPDATE digest_items
            SET category = ?,
                evidence_source = ?,
                contractor = ?,
                location = ?,
                follow_up = ?,
                review_status = ?
            WHERE item_id = ? AND batch_id = ?
            """,
            (
                item.category,
                item.evidence_source,
                item.contractor,
                item.location,
                item.follow_up,
                item.review_status,
                item_id,
                batch_id,
            ),
        )


def list_digest_batches(db_path=DIGEST_DB_PATH):
    """List saved digest batches, newest first."""
    initialize_digest_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT batch_id, start_date, end_date, created_at
            FROM digest_batches
            ORDER BY created_at DESC, batch_id
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_digest_batch(batch_id, db_path=DIGEST_DB_PATH):
    """Retrieve the saved date range for one digest batch."""
    initialize_digest_database(db_path)

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT batch_id, start_date, end_date, created_at
            FROM digest_batches
            WHERE batch_id = ?
            """,
            (batch_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "batch_id": row["batch_id"],
        "start_date": date.fromisoformat(row["start_date"]),
        "end_date": date.fromisoformat(row["end_date"]),
        "created_at": row["created_at"],
    }
