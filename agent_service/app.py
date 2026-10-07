"""Gemini-powered payment-dispute agent service."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import types

from agent_service.models import (
    AgentRunRequest,
    AgentRunResponse,
)
from agent_service.tools import ComplaintTools


load_dotenv()

DEFAULT_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite",
)

RETRY_ON_TIMEOUT = (
    os.getenv(
        "STATEASSERT_AGENT_RETRY_ON_TIMEOUT",
        "false",
    ).lower()
    == "true"
)

SYSTEM_INSTRUCTION = """
You are a customer-support agent handling payment disputes.

When the customer explicitly asks to create or register a payment
complaint and supplies a customer ID, payment ID and reason, call the
create_payment_dispute tool exactly once.

Never invent a complaint ID. After using the tool, explain the outcome
to the customer using only the tool result.
""".strip()


def create_agent_app(
    model_name: str = DEFAULT_MODEL,
) -> FastAPI:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing from the environment."
        )

    client = genai.Client(api_key=api_key)

    app = FastAPI(
        title="StateAssert Gemini Agent Under Test",
        version="0.1.0",
        description=(
            "A real Gemini tool-calling agent connected to the "
            "StateAssert fault proxy."
        ),
    )

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "model": model_name,
            "gemini_key_configured": True,
            "retry_on_timeout": RETRY_ON_TIMEOUT,
        }

    @app.post(
        "/run",
        response_model=AgentRunResponse,
    )
    def run_agent(
        request: AgentRunRequest,
    ) -> AgentRunResponse:
        tools = ComplaintTools(
            retry_on_timeout=RETRY_ON_TIMEOUT,
        )

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=request.message,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools=[tools.create_payment_dispute],
                    temperature=0,
                    automatic_function_calling=(
                        types.AutomaticFunctionCallingConfig(
                            maximum_remote_calls=2,
                        )
                    ),
                ),
            )
        except Exception as error:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Gemini agent execution failed: "
                    f"{type(error).__name__}: {error}"
                ),
            ) from error

        final_message = response.text or (
            "The agent returned no final customer message."
        )

        return AgentRunResponse(
            model=model_name,
            final_message=final_message,
            tool_executions=tools.executions,
        )

    return app


app = create_agent_app()