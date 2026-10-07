"""End-to-end API tests for the healthy complaint sandbox."""

from fastapi.testclient import TestClient

from sandbox.app import create_app


VALID_COMPLAINT = {
    "customer_id": "CUS-501",
    "payment_id": "PAY-9001",
    "reason": "Payment debited but merchant did not receive it",
}


def test_health_endpoint_reports_database_ready(tmp_path):
    app = create_app(tmp_path / "sandbox.db")

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ready"}


def test_create_and_retrieve_persisted_complaint(tmp_path):
    app = create_app(tmp_path / "sandbox.db")

    with TestClient(app) as client:
        created_response = client.post("/complaints", json=VALID_COMPLAINT)
        assert created_response.status_code == 201

        created = created_response.json()
        assert created["complaint_id"].startswith("CMP-")
        assert created["customer_id"] == VALID_COMPLAINT["customer_id"]
        assert created["payment_id"] == VALID_COMPLAINT["payment_id"]
        assert created["reason"] == VALID_COMPLAINT["reason"]
        assert created["status"] == "OPEN"

        retrieved_response = client.get(
            f"/complaints/{created['complaint_id']}"
        )

    assert retrieved_response.status_code == 200
    assert retrieved_response.json() == created


def test_unknown_complaint_returns_404(tmp_path):
    app = create_app(tmp_path / "sandbox.db")

    with TestClient(app) as client:
        response = client.get("/complaints/CMP-DOES-NOT-EXIST")

    assert response.status_code == 404
    assert response.json() == {"detail": "Complaint not found"}


def test_invalid_request_is_rejected_without_creating_complaint(tmp_path):
    app = create_app(tmp_path / "sandbox.db")

    with TestClient(app) as client:
        response = client.post(
            "/complaints",
            json={"customer_id": "", "payment_id": "PAY-9001", "reason": "x"},
        )

    assert response.status_code == 422
