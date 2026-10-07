"""Tests for the independent read-only verifier."""

import sqlite3
from datetime import UTC, datetime

import pytest

from sandbox.database import ComplaintDatabase
from sandbox.models import Complaint
from verifier.database import VerificationDatabase


def create_test_complaint(database_path):
    sandbox_database = ComplaintDatabase(database_path)
    sandbox_database.initialize()

    complaint = Complaint(
        complaint_id="CMP-TEST-1001",
        customer_id="CUS-501",
        payment_id="PAY-9001",
        reason="Payment debited but merchant did not receive it",
        status="OPEN",
        created_at=datetime.now(UTC),
    )

    sandbox_database.create(complaint)


def test_verifier_finds_persisted_business_state(tmp_path):
    database_path = tmp_path / "sandbox.db"
    create_test_complaint(database_path)

    verifier = VerificationDatabase(database_path)

    complaints = verifier.find_complaints(
        customer_id="CUS-501",
        payment_id="PAY-9001",
    )

    assert verifier.count_complaints("CUS-501", "PAY-9001") == 1
    assert len(complaints) == 1
    assert complaints[0]["complaint_id"] == "CMP-TEST-1001"


def test_verifier_detects_missing_business_state(tmp_path):
    database_path = tmp_path / "sandbox.db"

    sandbox_database = ComplaintDatabase(database_path)
    sandbox_database.initialize()

    verifier = VerificationDatabase(database_path)

    assert verifier.count_complaints("CUS-501", "PAY-NOT-EXIST") == 0
    assert verifier.find_complaints("CUS-501", "PAY-NOT-EXIST") == []


def test_verifier_cannot_modify_business_state(tmp_path):
    database_path = tmp_path / "sandbox.db"
    create_test_complaint(database_path)

    verifier = VerificationDatabase(database_path)

    with pytest.raises(
        sqlite3.OperationalError,
        match="readonly",
    ):
        with verifier.connect() as connection:
            connection.execute(
                "DELETE FROM complaints WHERE complaint_id = ?",
                ("CMP-TEST-1001",),
            )

    assert verifier.count_complaints("CUS-501", "PAY-9001") == 1