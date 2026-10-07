"""Independent read-only verification API."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI

from verifier.database import VerificationDatabase
from verifier.models import (
    ComplaintVerificationRequest,
    ComplaintVerificationResult,
    VerifiedComplaint,
)


DEFAULT_DB_PATH = Path(
    os.getenv("STATEASSERT_DB_PATH", "data/sandbox.db")
)


def create_verifier_app(
    database_path: str | Path = DEFAULT_DB_PATH,
) -> FastAPI:
    database = VerificationDatabase(database_path)

    app = FastAPI(
        title="StateAssert Independent Verifier",
        version="0.1.0",
        description=(
            "Read-only verification of authoritative complaint state."
        ),
    )

    app.state.database = database

    @app.get("/health")
    def health() -> dict:
        # A successful read proves the database is reachable.
        with database.connect() as connection:
            connection.execute("SELECT 1").fetchone()

        return {
            "status": "ok",
            "database": "reachable",
            "access": "read-only",
        }

    @app.post(
    "/verify/complaint",
    response_model=ComplaintVerificationResult,
    )
    def verify_complaint(
        request: ComplaintVerificationRequest,
    ) -> ComplaintVerificationResult:
        # Exact expected ownership match.
        complaints = database.find_complaints(
            customer_id=request.customer_id,
            payment_id=request.payment_id,
        )

        # All records for this payment, including other customers.
        payment_complaints = database.find_complaints_by_payment(
            payment_id=request.payment_id,
        )

        wrong_customer_complaints = [
            complaint
            for complaint in payment_complaints
            if complaint["customer_id"] != request.customer_id
        ]

        actual_count = len(complaints)

                # Forbidden side effects take priority over successful effects.
        if wrong_customer_complaints:
            verdict = "WRONG_CUSTOMER"

        elif actual_count == request.expected_count:
            verdict = "PASS"

        elif request.expected_count == 1 and actual_count == 0:
            verdict = "MISSING"

        elif request.expected_count == 1 and actual_count > 1:
            verdict = "DUPLICATE"

        else:
            verdict = "COUNT_MISMATCH"

        return ComplaintVerificationResult(
            verdict=verdict,
            customer_id=request.customer_id,
            payment_id=request.payment_id,
            expected_count=request.expected_count,
            actual_count=actual_count,
            complaints=[
                VerifiedComplaint.model_validate(complaint)
                for complaint in complaints
            ],
            related_complaints=[
                VerifiedComplaint.model_validate(complaint)
                for complaint in wrong_customer_complaints
            ],
        )
    return app


app = create_verifier_app()