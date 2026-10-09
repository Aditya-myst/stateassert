# StateAssert

> **The AI said it worked. StateAssert checks whether it really worked.**

StateAssert is an experimental action-integrity testing harness for tool-using AI agents.

It injects controlled failures into state-changing tools and independently checks the resulting authoritative business state.

## Status

**Early technical prototype — not production software.**

The current prototype demonstrates a synthetic payment-dispute workflow using:

- A real Gemini tool-calling agent
- An external HTTP fault proxy
- A healthy FastAPI complaint sandbox
- SQLite authoritative business state
- An independent read-only verifier
- Automated JSON evidence and an HTML report

This is technical proxy evidence, not customer, compliance, security or market validation.

## Problem

An AI agent can tell a customer that an action succeeded because:

- Its tool returned HTTP 200
- It received a realistic-looking record ID
- Its final response sounded correct

But the actual business outcome may still be wrong:

- Nothing was persisted
- The record was assigned to another customer
- A retry created a duplicate effect

StateAssert compares:

```text
Agent claim
    vs.
Tool response
    vs.
Actual authoritative business state
```

## Implemented scenarios

### 1. False success

```text
Tool returns HTTP 200
Agent claims complaint was created
No matching complaint exists in SQLite
StateAssert verdict: MISSING
```

### 2. Wrong customer

```text
Tool response shows the requested customer
Database record belongs to another customer
Agent claims success
StateAssert verdict: WRONG_CUSTOMER
```

### 3. Timeout after commit and unsafe retry

```text
First request commits
Response is delayed until the caller times out
Naive retry creates a second complaint
Agent claims one successful complaint
StateAssert verdict: DUPLICATE
```

## Initial evidence

Current saved experiment set:

| Scenario | Saved runs | StateAssert result |
|---|---:|---:|
| HTTP 200 without persistence | 1 | Detected 1/1 |
| Wrong-customer persistence | 1 | Detected 1/1 |
| Timeout after commit and retry | 1 | Detected 1/1 |
| Healthy control | 1 | False alarms 0/1 |

Important limitations:

- Only one saved run currently exists per scenario.
- The backend and customer records are synthetic.
- The response-success baseline is deterministic, not an AI judge.
- A complete tool trace contained a timeout clue in the retry scenario.
- General evaluation platforms can implement custom state evaluators.
- These results do not establish general detection accuracy.
- No customer agent or production financial system has been tested yet.

## Architecture

```text
Customer instruction
        |
        v
Gemini agent service :8003
        |
        v
StateAssert fault proxy :8002
        |
        v
Complaint sandbox :8000
        |
        v
SQLite authoritative state
        ^
        |
Independent verifier :8001
```

### Components

| Component | Port | Purpose |
|---|---:|---|
| Sandbox API | 8000 | Healthy synthetic complaint service |
| Verifier API | 8001 | Read-only authoritative-state checks |
| Fault proxy | 8002 | Controlled failure injection |
| Agent service | 8003 | Real Gemini tool-calling agent |

## Requirements

- Python 3.11 or newer
- Google Gemini API key
- Windows PowerShell commands are shown below

## Installation

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a private `.env` file:

```env
GEMINI_API_KEY=your_private_key
GEMINI_MODEL=gemini-3.5-flash-lite
STATEASSERT_AGENT_RETRY_ON_TIMEOUT=false
```

Never commit or share `.env`.

Confirm it is ignored:

```powershell
git check-ignore .env
git ls-files .env
```

`git ls-files .env` must print nothing.

## Run the services

Open four terminals in the repository root.

### Terminal 1 — Sandbox

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn "sandbox.app:app" --host 127.0.0.1 --port 8000
```

### Terminal 2 — Verifier

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn "verifier.app:app" --host 127.0.0.1 --port 8001
```

### Terminal 3 — Fault proxy

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn "fault_proxy.app:app" --host 127.0.0.1 --port 8002
```

### Terminal 4 — Agent service

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn "agent_service.app:app" --host 127.0.0.1 --port 8003
```

## API documentation

```text
Sandbox:  http://127.0.0.1:8000/docs
Verifier: http://127.0.0.1:8001/docs
Proxy:    http://127.0.0.1:8002/docs
Agent:    http://127.0.0.1:8003/docs
```

## Run automated experiments

### Healthy control

```powershell
python -m runner.run_agent_healthy
```

### False success

```powershell
python -m runner.run_agent_false_success
```

### Wrong customer

```powershell
python -m runner.run_agent_wrong_customer
```

### Timeout-after-commit duplicate

This experiment deliberately enables an unsafe retry policy.

Set:

```env
STATEASSERT_AGENT_RETRY_ON_TIMEOUT=true
```

Restart the agent service, then run:

```powershell
python -m runner.run_agent_timeout_duplicate
```

After the experiment, restore:

```env
STATEASSERT_AGENT_RETRY_ON_TIMEOUT=false
```

Restart the agent service again.

## Generate the evidence summary

```powershell
python -m runner.summarize_results
```

Output:

```text
results/summary.json
```

## Generate the visual report

```powershell
python -m runner.generate_report
Start-Process .\results\stateassert_evidence_report.html
```

## Run tests

```powershell
pytest -q
```

## Safe operating rules

1. Run only against synthetic, sandbox or staging systems.
2. Never inject faults into production financial systems.
3. Keep the fault-control API bound to `127.0.0.1`.
4. Always return the proxy to `healthy` mode after experiments.
5. Keep `STATEASSERT_AGENT_RETRY_ON_TIMEOUT=false` by default.
6. Do not expose API keys, customer data or production credentials.
7. Verify state before retrying an action with an unknown outcome.

## Current limitations

- Fault-control endpoints do not yet require authentication.
- The prototype uses one synthetic workflow.
- Scenario isolation uses unique payment IDs rather than complete database resets.
- The agent connector is not yet provider-neutral.
- The verifier directly reads a local SQLite sandbox.
- No external vendor agent has been connected.
- The prototype is not a compliance or certification product.

## Intended initial customer

Indian voice, chat and WhatsApp AI-agent vendors selling customer-service automation to fintechs, lenders and NBFCs.

## Initial workflow

Payment disputes and complaint creation.

## Next validation milestone

The next goal is not another synthetic failure.

It is to connect one external vendor’s sandbox agent and determine whether StateAssert finds a release issue their existing testing process would miss.

## Positioning

General evaluation platforms provide tracing, simulation and customizable evaluation infrastructure.

StateAssert is exploring a narrower product:

> Ready-made fault injection and authoritative outcome-verification tests for consequential financial-agent actions.
