"""HTTP tools available to the Gemini agent."""

import httpx

from agent_service.models import ToolExecution


class ComplaintTools:
    def __init__(
        self,
        proxy_url: str = "http://127.0.0.1:8002",
        retry_on_timeout: bool = False,
    ):
        self.proxy_url = proxy_url.rstrip("/")
        self.retry_on_timeout = retry_on_timeout
        self.executions: list[ToolExecution] = []

    def create_payment_dispute(
        self,
        customer_id: str,
        payment_id: str,
        reason: str,
    ) -> dict:
        """Create a payment-dispute complaint.

        Use this tool when a customer explicitly asks to create or register
        a complaint about a payment problem.

        Args:
            customer_id: The authenticated customer's identifier.
            payment_id: The payment being disputed.
            reason: A concise explanation of the payment problem.

        Returns:
            The final HTTP status and complaint API response.
        """
        request_body = {
            "customer_id": customer_id,
            "payment_id": payment_id,
            "reason": reason,
        }

        maximum_attempts = (
            2 if self.retry_on_timeout else 1
        )

        for attempt_number in range(1, maximum_attempts + 1):
            try:
                response = httpx.post(
                    f"{self.proxy_url}/complaints",
                    json=request_body,
                    timeout=15.0,
                )

                try:
                    response_body = response.json()
                except ValueError:
                    response_body = {
                        "raw_response": response.text,
                    }

                execution = ToolExecution(
                    tool_name="create_payment_dispute",
                    request=request_body,
                    http_status=response.status_code,
                    response={
                        **response_body,
                        "_attempt_number": attempt_number,
                    },
                )
                self.executions.append(execution)

                return {
                    "http_status": response.status_code,
                    "body": response_body,
                    "attempt_number": attempt_number,
                }

            except httpx.TimeoutException as error:
                timeout_body = {
                    "error": str(error),
                    "outcome": "unknown_after_dispatch",
                    "_attempt_number": attempt_number,
                }

                execution = ToolExecution(
                    tool_name="create_payment_dispute",
                    request=request_body,
                    http_status=0,
                    response=timeout_body,
                )
                self.executions.append(execution)

                if attempt_number < maximum_attempts:
                    # Deliberately unsafe policy for this test:
                    # retry without first verifying business state.
                    continue

                return {
                    "http_status": 0,
                    "body": timeout_body,
                    "attempt_number": attempt_number,
                }

            except httpx.RequestError as error:
                error_body = {
                    "error": str(error),
                    "outcome": "request_failed",
                    "_attempt_number": attempt_number,
                }

                execution = ToolExecution(
                    tool_name="create_payment_dispute",
                    request=request_body,
                    http_status=0,
                    response=error_body,
                )
                self.executions.append(execution)

                return {
                    "http_status": 0,
                    "body": error_body,
                    "attempt_number": attempt_number,
                }

        raise RuntimeError("Complaint tool ended without a result.")