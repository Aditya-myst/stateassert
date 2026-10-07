"""Generate a self-contained HTML report from saved evidence."""

import html
import json
from pathlib import Path


RESULTS = Path("results")
OUTPUT = RESULTS / "stateassert_evidence_report.html"

EVIDENCE_PATTERNS = [
    ("False Success", "false-success-*.json"),
    ("Wrong Customer", "wrong-customer-*.json"),
    ("Timeout Duplicate", "timeout-duplicate-*.json"),
    ("Healthy Control", "healthy-*.json"),
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def escape(value) -> str:
    return html.escape(str(value))


def load_evidence() -> list[tuple[str, Path, dict]]:
    evidence = []

    for label, pattern in EVIDENCE_PATTERNS:
        for path in sorted(RESULTS.glob(pattern)):
            evidence.append((label, path, load_json(path)))

    return evidence


def evidence_card(
    label: str,
    path: Path,
    run: dict,
) -> str:
    verification = run.get("verification", {})
    comparison = run.get("comparison", {})

    executions = run.get("tool_executions")

    if executions is None:
        single_execution = run.get("tool_execution")
        executions = (
            [single_execution]
            if single_execution
            else []
        )

    verdict = verification.get(
        "verdict",
        "HEALTHY CONTROL",
    )

    actual_count = verification.get(
        "actual_count",
        "Not available",
    )

    tool_rows = []

    for index, execution in enumerate(executions, start=1):
        tool_rows.append(
            f"""
            <tr>
                <td>{index}</td>
                <td>{escape(execution.get("tool_name"))}</td>
                <td>{escape(execution.get("http_status"))}</td>
                <td><code>{escape(
                    execution.get("response", {})
                )}</code></td>
            </tr>
            """
        )

    tool_table = "".join(tool_rows) or """
        <tr>
            <td colspan="4">No tool execution captured.</td>
        </tr>
    """

    related = verification.get(
        "related_complaints",
        [],
    )

    detected = comparison.get(
        "stateassert_detected_failure",
        comparison.get(
            "stateassert_confirmed_success",
            False,
        ),
    )

    return f"""
    <section class="evidence-card">
        <div class="card-heading">
            <div>
                <span class="scenario-label">{escape(label)}</span>
                <h2>{escape(run.get("scenario", label))}</h2>
            </div>
            <span class="verdict">{escape(verdict)}</span>
        </div>

        <div class="metadata">
            <span><strong>Run:</strong> {escape(run.get("run_id"))}</span>
            <span><strong>Model:</strong> {escape(run.get("model"))}</span>
            <span><strong>Payment:</strong> {escape(run.get("payment_id"))}</span>
            <span><strong>Evidence:</strong> {escape(path.name)}</span>
        </div>

        <h3>Agent’s customer-facing claim</h3>
        <blockquote>{escape(run.get("agent_final_message", "Not captured"))}</blockquote>

        <h3>Tool attempts</h3>
        <table>
            <thead>
                <tr>
                    <th>Attempt</th>
                    <th>Tool</th>
                    <th>HTTP status</th>
                    <th>Response evidence</th>
                </tr>
            </thead>
            <tbody>
                {tool_table}
            </tbody>
        </table>

        <div class="outcome-grid">
            <div>
                <span>Expected effects</span>
                <strong>{escape(verification.get("expected_count", 1))}</strong>
            </div>
            <div>
                <span>Matching effects</span>
                <strong>{escape(actual_count)}</strong>
            </div>
            <div>
                <span>Related forbidden effects</span>
                <strong>{len(related)}</strong>
            </div>
            <div>
                <span>StateAssert check</span>
                <strong>{"Confirmed" if detected else "Not confirmed"}</strong>
            </div>
        </div>
    </section>
    """


def generate_report() -> Path:
    summary = load_json(RESULTS / "summary.json")
    evidence = load_evidence()

    overall = summary["overall_fault_detection"]
    stateassert = overall["stateassert"]
    response_check = overall["response_success_check"]
    status_check = overall["final_tool_status_check"]
    trace_clues = overall["complete_trace_error_clues"]
    healthy = summary["healthy_controls"]

    evidence_html = "".join(
        evidence_card(label, path, run)
        for label, path, run in evidence
    )

    limitations_html = "".join(
        f"<li>{escape(item)}</li>"
        for item in summary.get("limitations", [])
    )

    document = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>StateAssert Evidence Report</title>
<style>
:root {
    --navy: #101828;
    --blue: #155eef;
    --blue-light: #eff4ff;
    --green: #067647;
    --green-light: #ecfdf3;
    --red: #b42318;
    --surface: #ffffff;
    --background: #f2f4f7;
    --border: #d0d5dd;
    --muted: #667085;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    color: var(--navy);
    background: var(--background);
    font-family: Inter, Arial, sans-serif;
    line-height: 1.5;
}
header {
    color: white;
    padding: 54px 7%;
    background: linear-gradient(135deg, #101828, #1849a9);
}
header h1 {
    margin: 0 0 10px;
    font-size: 42px;
}
header p {
    max-width: 760px;
    margin: 0;
    color: #d1e0ff;
    font-size: 18px;
}
main {
    width: min(1180px, 92%);
    margin: -24px auto 60px;
}
.panel, .evidence-card {
    margin-bottom: 24px;
    padding: 28px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(16,24,40,.06);
}
.metrics {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
}
.metric {
    padding: 20px;
    background: var(--blue-light);
    border-radius: 12px;
}
.metric span {
    display: block;
    color: var(--muted);
    font-size: 13px;
}
.metric strong {
    display: block;
    margin-top: 6px;
    color: var(--blue);
    font-size: 30px;
}
table {
    width: 100%;
    border-collapse: collapse;
}
th, td {
    padding: 12px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
}
th {
    color: var(--muted);
    font-size: 13px;
}
.card-heading {
    display: flex;
    justify-content: space-between;
    gap: 20px;
}
.card-heading h2 {
    margin: 6px 0 0;
}
.scenario-label {
    color: var(--blue);
    font-weight: 700;
}
.verdict {
    height: fit-content;
    padding: 8px 12px;
    color: var(--green);
    background: var(--green-light);
    border-radius: 999px;
    font-weight: 700;
}
.metadata {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    margin: 18px 0;
    color: var(--muted);
}
blockquote {
    margin: 10px 0 24px;
    padding: 18px;
    background: #f9fafb;
    border-left: 4px solid var(--blue);
}
.outcome-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-top: 22px;
}
.outcome-grid div {
    padding: 16px;
    background: #f9fafb;
    border-radius: 10px;
}
.outcome-grid span {
    display: block;
    color: var(--muted);
    font-size: 12px;
}
.outcome-grid strong {
    display: block;
    margin-top: 6px;
}
.warning {
    border-left: 5px solid #f79009;
}
code {
    word-break: break-word;
    white-space: normal;
}
footer {
    padding: 28px;
    color: var(--muted);
    text-align: center;
}
@media (max-width: 800px) {
    .metrics, .outcome-grid {
        grid-template-columns: 1fr 1fr;
    }
}
</style>
</head>
<body>
<header>
    <h1>StateAssert</h1>
    <p>
        The AI said it worked. StateAssert checked what actually
        changed in authoritative business state.
    </p>
</header>
<main>
""" + f"""
<section class="panel">
    <h2>Controlled experiment summary</h2>
    <div class="metrics">
        <div class="metric">
            <span>Injected faulty runs</span>
            <strong>{summary["total_faulty_runs"]}</strong>
        </div>
        <div class="metric">
            <span>StateAssert detections</span>
            <strong>{stateassert["detected"]}/{stateassert["total"]}</strong>
        </div>
        <div class="metric">
            <span>Healthy false alarms</span>
            <strong>{healthy["false_alarms"]}/{healthy["total"]}</strong>
        </div>
        <div class="metric">
            <span>Trace error clues</span>
            <strong>{trace_clues["runs"]}/{trace_clues["total"]}</strong>
        </div>
    </div>
</section>

<section class="panel">
    <h2>Baseline comparison</h2>
    <table>
        <thead>
            <tr>
                <th>Method</th>
                <th>Failures detected</th>
                <th>What it checked</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Response-success check</td>
                <td>{response_check["detected"]}/{response_check["total"]}</td>
                <td>Whether the final response claimed success</td>
            </tr>
            <tr>
                <td>Final tool-status check</td>
                <td>{status_check["detected"]}/{status_check["total"]}</td>
                <td>Whether the final tool attempt reported success</td>
            </tr>
            <tr>
                <td>StateAssert</td>
                <td>{stateassert["detected"]}/{stateassert["total"]}</td>
                <td>Fresh authoritative business state and forbidden effects</td>
            </tr>
        </tbody>
    </table>
</section>

{evidence_html}

<section class="panel warning">
    <h2>Limitations and honest interpretation</h2>
    <ul>{limitations_html}</ul>
</section>
</main>
<footer>
    StateAssert synthetic technical experiment — not customer,
    production, compliance or market validation.
</footer>
</body>
</html>
"""

    OUTPUT.write_text(document, encoding="utf-8")
    return OUTPUT


if __name__ == "__main__":
    output = generate_report()
    print(f"Generated report: {output}")