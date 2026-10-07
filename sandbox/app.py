"""Healthy payment-dispute sandbox HTTP API.

Run locally:
    uvicorn sandbox.app:app --reload
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status

from sandbox.database import ComplaintDatabase
from sandbox.models import Complaint, ComplaintCreate, HealthResponse

DEFAULT_DB_PATH = Path(os.getenv("STATEASSERT_DB_PATH", "data/sandbox.db"))


def create_app(db_path: str | Path = DEFAULT_DB_PATH) -> FastAPI:
    database = ComplaintDatabase(db_path)
    database.initialize()

    app = FastAPI(
        title="StateAssert Payment-Dispute Sandbox",
        version="0.1.0",
        description="A healthy synthetic complaint API. Fault injection is not enabled.",
    )
    app.state.database = database

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        ready = database.is_ready()
        if not ready:
            raise HTTPException(status_code=503, detail="Database unavailable")
        return HealthResponse(status="ok", database="ready")

    @app.post(
        "/complaints",
        response_model=Complaint,
        status_code=status.HTTP_201_CREATED,
    )
    def create_complaint(payload: ComplaintCreate) -> Complaint:
        complaint = Complaint(
            complaint_id=f"CMP-{uuid4().hex[:12].upper()}",
            customer_id=payload.customer_id,
            payment_id=payload.payment_id,
            reason=payload.reason,
            status="OPEN",
            created_at=datetime.now(UTC),
        )
        return database.create(complaint)

    @app.get("/complaints/{complaint_id}", response_model=Complaint)
    def get_complaint(complaint_id: str) -> Complaint:
        complaint = database.get(complaint_id)
        if complaint is None:
            raise HTTPException(status_code=404, detail="Complaint not found")
        return complaint

    return app


app = create_app()
