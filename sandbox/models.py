"""Validated API request and response models."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    payment_id: str = Field(min_length=1, max_length=64)
    reason: str = Field(min_length=5, max_length=500)


class Complaint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: str
    customer_id: str
    payment_id: str
    reason: str
    status: str
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    database: str
