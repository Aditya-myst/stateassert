"""Run and save a wrong-customer experiment against the real agent."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx


VERIFIER_URL = "http://127.0.0.1:8001"
PROXY_URL = "http://127.0.0.1:8002"
AGENT_URL = "http://127.0.0.1:8003"


def run_experiment() -> tuple[dict, Path]:
    run_id = uuid4().hex[:10].upper()
    payment_id = f"PAY-WRONG-AUTO-{run_id}"

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

        if (
            baseline["actual_count"] != 0
            or baseline["related_complaints"]
        ):
            raise RuntimeError(
                "Scenario did not start with clean state."
            )

        try:
            fault_response = client.put(
                f"{PROXY_URL}/control/fault",
                json={"mode": "wrong_customer"},
            )
            fault_response.raise_for_status()

            agent_response = client.post(
                f"{AGENT_URL}/run",
                json=agent_request,
            )

            if agent_response.is_error:
                raise RuntimeError(
                    "Agent service failed with "
                    f"HTTP {agent_response.status_code}: "
                    f"{agent_response.text}"
                )

            agent_result = agent_response.json()
            tool_executions = agent_result["tool_executions"]

            if len(tool_executions) != 1:
                raise RuntimeError(
                    "Expected exactly one complaint tool execution, "
                    f"but found {len(tool_executions)}."
                )

            tool_execution = tool_executions[0]

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

    related_complaints = verification[
        "related_complaints"
    ]

    stateassert_detected_failure = (
        verification["verdict"] == "WRONG_CUSTOMER"
        and verification["actual_count"] == 0
        and len(related_complaints) == 1
        and related_complaints[0]["customer_id"]
        == "CUS-INJECTED-WRONG"
    )

    result = {
        "run_id": run_id,
        "executed_at": datetime.now(UTC).isoformat(),
        "scenario": "Real agent: complaint persisted under wrong customer",
        "model": agent_result["model"],
        "customer_id": "CUS-501",
        "payment_id": payment_id,
        "agent_final_message": agent_result["final_message"],
        "tool_execution": tool_execution,
        "verification": verification,
        "comparison": {
            "response_success_check_passed": (
                response_claimed_success
            ),
            "tool_status_check_passed": tool_status_passed,
            "stateassert_detected_failure": (
                stateassert_detected_failure
            ),
        },
    }

    results_directory = Path("results")
    results_directory.mkdir(exist_ok=True)

    result_path = results_directory / (
        f"wrong-customer-{run_id}.json"
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