"""SQLite persistence for the complaint sandbox."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sandbox.models import Complaint, ComplaintCreate


class ComplaintDatabase:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS complaints (
                    complaint_id TEXT PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    payment_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def create(self, complaint: Complaint) -> Complaint:
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO complaints (
                    complaint_id, customer_id, payment_id,
                    reason, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    complaint.complaint_id,
                    complaint.customer_id,
                    complaint.payment_id,
                    complaint.reason,
                    complaint.status,
                    complaint.created_at.isoformat(),
                ),
            )
        return complaint

    def get(self, complaint_id: str) -> Complaint | None:
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT complaint_id, customer_id, payment_id,
                       reason, status, created_at
                FROM complaints
                WHERE complaint_id = ?
                """,
                (complaint_id,),
            ).fetchone()

        return Complaint.model_validate(dict(row)) if row else None

    def is_ready(self) -> bool:
        try:
            with self.connect() as connection:
                connection.execute("SELECT 1").fetchone()
            return True
        except sqlite3.Error:
            return False
