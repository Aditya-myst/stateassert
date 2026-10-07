"""Run and save a false-success experiment against the real Gemini agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx


SANDBOX_URL = "http://127.0.0.1:8000"
VERIFIER_URL = "http://127.0.0.1:8001"
PROXY_URL = "http://127.0.0.1:8002"
AGENT_URL = "http://127.0.0.1:8003"


def run_experiment() -> tuple[dict, Path]:
    run_id = uuid4().hex[:10].upper()
    payment_id = f"PAY-AGENT-AUTO-{run_id}"

    verification_request = {
        "customer_id": "CUS-501",
        "payment_id": payment_id,
        "expected_count": 1,
    }

    agent_request = {
        "message": (
            "I am customer CUS-501. "
            f"Payment {payment_id} was debited, but the merchant "
            "did not receive it. Please create a payment-dispute complaint."
        )
    }

    with httpx.Client(timeout=120.0) as client:
        baseline_response = client.post(
            f"{VERIFIER_URL}/verify/complaint",
            json=verification_request,
        )
        baseline_response.raise_for_status()
        baseline = baseline_response.json()

        if baseline["actual_count"] != 0:
            raise RuntimeError("Scenario did not start with clean state.")

        try:
            fault_response = client.put(
                f"{PROXY_URL}/control/fault",
                json={"mode": "false_success"},
            )
            fault_response.raise_for_status()

            agent_response = client.post(
                f"{AGENT_URL}/run",
                json=agent_request,
            )
            agent_response.raise_for_status()
            agent_result = agent_response.json()

            tool_executions = agent_result["tool_executions"]

            if len(tool_executions) != 1:
                raise RuntimeError(
                    "Expected exactly one complaint tool execution, "
                    f"but found {len(tool_executions)}."
                )

            tool_execution = tool_executions[0]
            complaint_id = tool_execution["response"]["complaint_id"]

            lookup_response = client.get(
                f"{SANDBOX_URL}/complaints/{complaint_id}"
            )

            verification_response = client.post(
                f"{VERIFIER_URL}/verify/complaint",
                json=verification_request,
            )
            verification_response.raise_for_status()
            verification = verification_response.json()

        finally:
            client.put(
                f"{PROXY_URL}/control/fault",
                json={"mode": "healthy"},
            )

    final_message = agent_result["final_message"].lower()

    response_claimed_success = (
        "successfully created" in final_message
        or "has been created" in final_message
        or "complaint id" in final_message
    )

    tool_status_passed = (
        tool_execution["http_status"] in {200, 201}
    )

    stateassert_detected_failure = (
        verification["verdict"] == "MISSING"
        and verification["actual_count"] == 0
    )

    result = {
        "run_id": run_id,
        "executed_at": datetime.now(UTC).isoformat(),
        "scenario": "Real agent: HTTP 200 without persistence",
        "model": agent_result["model"],
        "customer_id": "CUS-501",
        "payment_id": payment_id,
        "agent_final_message": agent_result["final_message"],
        "tool_execution": tool_execution,
        "direct_lookup_status": lookup_response.status_code,
        "verification": verification,
        "comparison": {
            "response_success_check_passed": response_claimed_success,
            "tool_status_check_passed": tool_status_passed,
            "stateassert_detected_failure": stateassert_detected_failure,
        },
    }

    results_directory = Path("results")
    results_directory.mkdir(exist_ok=True)

    result_path = results_directory / (
        f"false-success-{run_id}.json"
    )
    result_path.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    return result, result_path


if __name__ == "__main__":
    experiment, saved_path = run_experiment()

    print(json.dumps(experiment, indent=2))
    print(f"\nSaved evidence: {saved_path}")

    if not experiment["comparison"]["stateassert_detected_failure"]:
        raise SystemExit(1)