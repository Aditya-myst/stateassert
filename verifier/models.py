"""Request and response models for independent verification."""

from typing import Literal

from pydantic import BaseModel, Field


class ComplaintVerificationRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    payment_id: str = Field(min_length=1, max_length=64)
    expected_count: int = Field(default=1, ge=0, le=10)


class VerifiedComplaint(BaseModel):
    complaint_id: str
    customer_id: str
    payment_id: str
    reason: str
    status: str
    created_at: str


class ComplaintVerificationResult(BaseModel):
    verdict: Literal[
        "PASS", 
        "MISSING",
        "DUPLICATE",
        "WRONG_CUSTOMER",
        "COUNT_MISMATCH",
    ]

    customer_id: str
    payment_id: str

    expected_count: int
    actual_count: int

    complaints: list[VerifiedComplaint]
    related_complaints: list[VerifiedComplaint] = []