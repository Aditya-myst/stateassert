"""Aggregate saved real-agent experiment evidence."""

import json
from pathlib import Path


RESULTS_DIRECTORY = Path("results")


def load_results(pattern: str) -> list[dict]:
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(RESULTS_DIRECTORY.glob(pattern))
    ]


def percentage(
    numerator: int,
    denominator: int,
) -> float | None:
    if denominator == 0:
        return None

    return round((numerator / denominator) * 100, 2)


def summarize_fault_group(
    name: str,
    runs: list[dict],
) -> dict:
    response_detections = sum(
        not run["comparison"][
            "response_success_check_passed"
        ]
        for run in runs
    )

    final_status_detections = sum(
        not run["comparison"][
            "tool_status_check_passed"
        ]
        for run in runs
    )

    stateassert_detections = sum(
        run["comparison"][
            "stateassert_detected_failure"
        ]
        for run in runs
    )

    trace_error_runs = sum(
        run["comparison"].get(
            "tool_trace_contains_error",
            False,
        )
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
            "detected": final_status_detections,
            "total": len(runs),
        },
        "complete_trace_contained_error_clue": {
            "runs": trace_error_runs,
            "total": len(runs),
        },
        "stateassert": {
            "detected": stateassert_detections,
            "total": len(runs),
        },
    }


def create_summary() -> dict:
    false_success_runs = load_results(
        "false-success-*.json"
    )
    wrong_customer_runs = load_results(
        "wrong-customer-*.json"
    )
    timeout_duplicate_runs = load_results(
        "timeout-duplicate-*.json"
    )
    healthy_runs = load_results("healthy-*.json")

    fault_groups = {
        "false_success": {
            "name": "HTTP 200 without persistence",
            "runs": false_success_runs,
        },
        "wrong_customer": {
            "name": "Complaint persisted under wrong customer",
            "runs": wrong_customer_runs,
        },
        "timeout_duplicate": {
            "name": "Timeout after commit followed by unsafe retry",
            "runs": timeout_duplicate_runs,
        },
    }

    faulty_runs = [
        run
        for group in fault_groups.values()
        for run in group["runs"]
    ]

    response_detections = sum(
        not run["comparison"][
            "response_success_check_passed"
        ]
        for run in faulty_runs
    )

    final_status_detections = sum(
        not run["comparison"][
            "tool_status_check_passed"
        ]
        for run in faulty_runs
    )

    trace_error_runs = sum(
        run["comparison"].get(
            "tool_trace_contains_error",
            False,
        )
        for run in faulty_runs
    )

    stateassert_detections = sum(
        run["comparison"][
            "stateassert_detected_failure"
        ]
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
            key: summarize_fault_group(
                group["name"],
                group["runs"],
            )
            for key, group in fault_groups.items()
        },
        "overall_fault_detection": {
            "response_success_check": {
                "detected": response_detections,
                "total": len(faulty_runs),
                "rate_percent": percentage(
                    response_detections,
                    len(faulty_runs),
                ),
            },
            "final_tool_status_check": {
                "detected": final_status_detections,
                "total": len(faulty_runs),
                "rate_percent": percentage(
                    final_status_detections,
                    len(faulty_runs),
                ),
            },
            "complete_trace_error_clues": {
                "runs": trace_error_runs,
                "total": len(faulty_runs),
            },
            "stateassert": {
                "detected": stateassert_detections,
                "total": len(faulty_runs),
                "rate_percent": percentage(
                    stateassert_detections,
                    len(faulty_runs),
                ),
            },
        },
        "healthy_controls": {
            "false_alarms": false_alarms,
            "total": len(healthy_runs),
            "false_alarm_rate_percent": percentage(
                false_alarms,
                len(healthy_runs),
            ),
        },
        "limitations": [
            "Results come from a synthetic payment-dispute sandbox.",
            "Only one saved run currently exists per scenario.",
            "Response-success checking is a simple deterministic check, not an AI judge.",
            "Complete traces may contain useful error clues even when final status appears successful.",
            "These results are technical proxy evidence, not customer or market validation.",
        ],
    }


if __name__ == "__main__":
    summary = create_summary()

    output_path = RESULTS_DIRECTORY / "summary.json"
    output_path.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2))
    print(f"\nSaved summary: {output_path}")