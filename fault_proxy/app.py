"""HTTP proxy that injects controlled failures into complaint creation."""

from __future__ import annotations
import asyncio

import os
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from fault_proxy.models import (
    FaultConfiguration,
    FaultMode,
    FaultStatus,
)
from sandbox.models import ComplaintCreate


DEFAULT_SANDBOX_URL = os.getenv(
    "STATEASSERT_SANDBOX_URL",
    "http://127.0.0.1:8000",
)


def create_proxy_app(
    sandbox_url: str = DEFAULT_SANDBOX_URL,
) -> FastAPI:
    app = FastAPI(
        title="StateAssert Fault Proxy",
        version="0.1.0",
        description="Injects controlled failures before requests reach the sandbox.",
    )

    # Every restart begins safely in healthy mode.
    app.state.fault_mode = FaultMode.HEALTHY
    app.state.sandbox_url = sandbox_url.rstrip("/")

    app.state.fault_triggered = False
    app.state.timeout_after_commit_seconds = float(
        os.getenv(
            "STATEASSERT_TIMEOUT_AFTER_COMMIT_SECONDS",
            "20",
        )
    )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "active_fault": app.state.fault_mode.value,
            "sandbox_url": app.state.sandbox_url,
        }

    @app.get(
        "/control/fault",
        response_model=FaultStatus,
    )
    def get_fault() -> FaultStatus:
        return FaultStatus(
            active_mode=app.state.fault_mode,
        )

    @app.put(
        "/control/fault",
        response_model=FaultStatus,
    )
    def set_fault(
        configuration: FaultConfiguration,
    ) -> FaultStatus:
        app.state.fault_mode = configuration.mode
        app.state.fault_triggered = False

        return FaultStatus(
            active_mode=app.state.fault_mode,
        )

    @app.post("/complaints")
    async def create_complaint(
        payload: ComplaintCreate,
    ):
        if app.state.fault_mode == FaultMode.FALSE_SUCCESS:
            # Return realistic success without calling the sandbox.
            fake_response = {
                "complaint_id": (
                    f"CMP-{uuid4().hex[:12].upper()}"
                ),
                "customer_id": payload.customer_id,
                "payment_id": payload.payment_id,
                "reason": payload.reason,
                "status": "OPEN",
                "created_at": datetime.now(UTC).isoformat(),
            }

            return JSONResponse(
                status_code=200,
                content=fake_response,
            )

        forwarded_payload = payload.model_dump()
        inject_timeout_after_commit = (
            app.state.fault_mode
            == FaultMode.TIMEOUT_AFTER_COMMIT
            and not app.state.fault_triggered
        )

        if inject_timeout_after_commit:
            # Mark it before forwarding to prevent concurrent calls
            # from triggering the same one-shot fault.
            app.state.fault_triggered = True

        inject_wrong_customer = (
            app.state.fault_mode
            == FaultMode.WRONG_CUSTOMER
        )

        if inject_wrong_customer:
            # Persist the complaint under a different customer.
            forwarded_payload["customer_id"] = (
                "CUS-INJECTED-WRONG"
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # There must be exactly one sandbox request.
                sandbox_response = await client.post(
                    f"{app.state.sandbox_url}/complaints",
                    json=forwarded_payload,
                )
        except httpx.RequestError as error:
            raise HTTPException(
                status_code=502,
                detail=f"Sandbox unavailable: {error}",
            ) from error

        response_body = sandbox_response.json()

        if inject_wrong_customer:
            # Hide the incorrect persisted owner from the caller.
            response_body["customer_id"] = payload.customer_id

        if inject_timeout_after_commit:
            # The sandbox has already committed the complaint.
            # Delay the acknowledgment until the caller times out.
            await asyncio.sleep(
                app.state.timeout_after_commit_seconds
            )

        return JSONResponse(
            status_code=sandbox_response.status_code,
            content=response_body,
        )

    return app


app = create_proxy_app()