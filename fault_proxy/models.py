"""Configuration models for controlled fault injection."""

from enum import Enum

from pydantic import BaseModel


class FaultMode(str, Enum):
    HEALTHY = "healthy"
    FALSE_SUCCESS = "false_success"
    WRONG_CUSTOMER = "wrong_customer"
    TIMEOUT_AFTER_COMMIT = "timeout_after_commit"


class FaultConfiguration(BaseModel):
    mode: FaultMode


class FaultStatus(BaseModel):
    active_mode: FaultMode