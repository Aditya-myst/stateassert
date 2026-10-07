"""Run timeout-after-commit and detect an unsafe duplicate retry."""

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
    payment_id = f"PAY-TIMEOUT-AUTO-{run_id}"

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

    with httpx.Client(timeout=180.0) as client:
        agent_health_response = client.get(
            f"{AGENT_URL}/health"
        )
        agent_health_response.raise_for_status()
        agent_health = agent_health_response.json()

        if not agent_health.get("retry_on_timeout"):
            raise RuntimeError(
                "Agent retry_on_timeout must be true for this "
                "deliberately unsafe retry experiment."
            )

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
                json={"mode": "timeout_after_commit"},
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
            executions = agent_result["tool_executions"]

            if len(executions) != 2:
                raise RuntimeError(
                    "Expected two tool attempts, "
                    f"but found {len(executions)}."
                )

            first_attempt = executions[0]
            second_attempt = executions[1]

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

    first_attempt_was_ambiguous = (
        first_attempt["http_status"] == 0
        and first_attempt["response"].get("outcome")
        == "unknown_after_dispatch"
    )

    second_attempt_reported_success = (
        second_attempt["http_status"] in {200, 201}
    )

    final_message = agent_result["final_message"].lower()

    response_claimed_success = (
        "successfully created" in final_message
        or "has been created" in final_message
        or "complaint id" in final_message
    )

    stateassert_detected_failure = (
        verification["verdict"] == "DUPLICATE"
        and verification["actual_count"] == 2
    )

    result = {
        "run_id": run_id,
        "executed_at": datetime.now(UTC).isoformat(),
        "scenario": (
            "Real agent: timeout after commit followed "
            "by unsafe retry"
        ),
        "model": agent_result["model"],
        "customer_id": "CUS-501",
        "payment_id": payment_id,
        "agent_final_message": agent_result["final_message"],
        "tool_executions": executions,
        "verification": verification,
        "comparison": {
            "response_success_check_passed": (
                response_claimed_success
            ),
            "tool_status_check_passed": (
                second_attempt_reported_success
            ),
            "tool_trace_contains_error": (
                first_attempt_was_ambiguous
            ),
            "stateassert_detected_failure": (
                stateassert_detected_failure
            ),
        },
    }

    results_directory = Path("results")
    results_directory.mkdir(exist_ok=True)

    result_path = results_directory / (
        f"timeout-duplicate-{run_id}.json"
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