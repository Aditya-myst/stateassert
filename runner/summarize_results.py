"""Summarize all saved StateAssert experiment evidence."""

import json
from pathlib import Path


RESULTS = Path("results")

SCENARIOS = {
    "false_success": (
        "HTTP 200 without persistence",
        "false-success-*.json",
    ),
    "wrong_customer": (
        "Complaint persisted under wrong customer",
        "wrong-customer-*.json",
    ),
    "timeout_duplicate": (
        "Timeout after commit followed by unsafe retry",
        "timeout-duplicate-*.json",
    ),
}


def load(pattern: str) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(RESULTS.glob(pattern))
    ]


def rate(value: int, total: int) -> float | None:
    if total == 0:
        return None

    return round((value / total) * 100, 2)


def summarize_group(
    name: str,
    runs: list[dict],
) -> dict:
    response_detections = sum(
        not run["comparison"]["response_success_check_passed"]
        for run in runs
    )

    status_detections = sum(
        not run["comparison"]["tool_status_check_passed"]
        for run in runs
    )

    trace_error_clues = sum(
        run["comparison"].get(
            "tool_trace_contains_error",
            False,
        )
        for run in runs
    )

    stateassert_detections = sum(
        run["comparison"]["stateassert_detected_failure"]
        for run in runs
    )

    return {
        "name": name,
        "runs": len(runs),
        "response_success_check": {
            "detected": response_detections,
            "total": len(runs),
        },
        "final_tool_status_check": {
            "detected": status_detections,
            "total": len(runs),
        },
        "complete_trace_error_clues": {
            "runs": trace_error_clues,
            "total": len(runs),
        },
        "stateassert": {
            "detected": stateassert_detections,
            "total": len(runs),
        },
    }


def create_summary() -> dict:
    groups = {
        key: {
            "name": name,
            "runs": load(pattern),
        }
        for key, (name, pattern) in SCENARIOS.items()
    }

    faulty_runs = [
        run
        for group in groups.values()
        for run in group["runs"]
    ]

    healthy_runs = load("healthy-*.json")

    response_detections = sum(
        not run["comparison"]["response_success_check_passed"]
        for run in faulty_runs
    )

    status_detections = sum(
        not run["comparison"]["tool_status_check_passed"]
        for run in faulty_runs
    )

    trace_error_clues = sum(
        run["comparison"].get(
            "tool_trace_contains_error",
            False,
        )
        for run in faulty_runs
    )

    stateassert_detections = sum(
        run["comparison"]["stateassert_detected_failure"]
        for run in faulty_runs
    )

    false_alarms = sum(
        run["comparison"]["stateassert_false_alarm"]
        for run in healthy_runs
    )

    return {
        "total_faulty_runs": len(faulty_runs),
        "total_healthy_runs": len(healthy_runs),
        "scenario_breakdown": {
            key: summarize_group(
                group["name"],
                group["runs"],
            )
            for key, group in groups.items()
        },
        "overall_fault_detection": {
            "response_success_check": {
                "detected": response_detections,
                "total": len(faulty_runs),
                "rate_percent": rate(
                    response_detections,
                    len(faulty_runs),
                ),
            },
            "final_tool_status_check": {
                "detected": status_detections,
                "total": len(faulty_runs),
                "rate_percent": rate(
                    status_detections,
                    len(faulty_runs),
                ),
            },
            "complete_trace_error_clues": {
                "runs": trace_error_clues,
                "total": len(faulty_runs),
            },
            "stateassert": {
                "detected": stateassert_detections,
                "total": len(faulty_runs),
                "rate_percent": rate(
                    stateassert_detections,
                    len(faulty_runs),
                ),
            },
        },
        "healthy_controls": {
            "false_alarms": false_alarms,
            "total": len(healthy_runs),
            "false_alarm_rate_percent": rate(
                false_alarms,
                len(healthy_runs),
            ),
        },
        "limitations": [
            "Synthetic sandbox evidence only.",
            "One saved run per scenario.",
            "Response check is deterministic, not an AI judge.",
            "A complete tool trace exposed a timeout clue in one run.",
            "These results are not customer or market validation.",
        ],
    }


if __name__ == "__main__":
    summary = create_summary()

    output = RESULTS / "summary.json"
    output.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print(f"\nSaved summary: {output}")