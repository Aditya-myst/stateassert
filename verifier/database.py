"""Read-only access to authoritative sandbox state."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class VerificationDatabase:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path).resolve()

        if not self.database_path.exists():
            raise FileNotFoundError(
                f"Sandbox database does not exist: {self.database_path}"
            )

    def connect(self) -> sqlite3.Connection:
        """
        Open SQLite in read-only mode.

        mode=ro prevents the verifier from inserting, updating
        or deleting business records.
        """
        database_uri = f"{self.database_path.as_uri()}?mode=ro"

        connection = sqlite3.connect(
            database_uri,
            uri=True,
        )
        connection.row_factory = sqlite3.Row
        return connection

    def find_complaints(
        self,
        customer_id: str,
        payment_id: str,
    ) -> list[dict]:
        """
        Find complaints using business identifiers.

        We deliberately do not rely only on the complaint ID returned
        by the tool because that ID could be incorrect or fabricated.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    complaint_id,
                    customer_id,
                    payment_id,
                    reason,
                    status,
                    created_at
                FROM complaints
                WHERE customer_id = ?
                  AND payment_id = ?
                ORDER BY created_at ASC
                """,
                (customer_id, payment_id),
            ).fetchall()

        return [dict(row) for row in rows]


    def find_complaints_by_payment(
    self,
    payment_id: str,
    ) -> list[dict]:
        """
        Find all complaints for a payment, regardless of customer.

        This allows the verifier to detect when a complaint was written
        under the wrong customer.
        """
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    complaint_id,
                    customer_id,
                    payment_id,
                    reason,
                    status,
                    created_at
                FROM complaints
                WHERE payment_id = ?
                ORDER BY created_at ASC
                """,
                (payment_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def count_complaints(
        self,
        customer_id: str,
        payment_id: str,
    ) -> int:
        """Count matching complaints to detect missing or duplicate effects."""
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS complaint_count
                FROM complaints
                WHERE customer_id = ?
                  AND payment_id = ?
                """,
                (customer_id, payment_id),
            ).fetchone()

        return int(row["complaint_count"])