"""Domain decision for grouping nonprofit backend failures."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .infrai_client import InfraiClient


class Workflow(str, Enum):
    DONOR_RECEIPT = "donor_receipt"
    VOLUNTEER_REMINDER = "volunteer_reminder"
    CAMPAIGN_REPORT = "campaign_report"


class BackendFailure(BaseModel):
    request_id: str = Field(min_length=1)
    workflow: Workflow
    operation: str = Field(min_length=1, max_length=80)
    exception_type: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=500)
    traceback: str = Field(min_length=1)
    organization_id: str = Field(min_length=1)


class CaptureDecision(BaseModel):
    status: str
    workflow: Workflow
    grouping_key: list[str]
    capture: dict[str, Any]


def grouping_key(failure: BackendFailure) -> list[str]:
    """Keep repeated failures together without mixing distinct operations."""
    return ["nonprofit-backend", failure.workflow.value, failure.operation]


def capture_backend_failure(
    failure: BackendFailure, client: InfraiClient
) -> CaptureDecision:
    fingerprint = grouping_key(failure)
    result = client.capture_exception(
        {
            "title": f"{failure.workflow.value}: {failure.operation}",
            "message": failure.message,
            "level": "error",
            "fingerprint": fingerprint,
            "exception": failure.traceback,
            "context": {
                "workflow": failure.workflow.value,
                "operation": failure.operation,
                "exception_type": failure.exception_type,
                "organization_id": failure.organization_id,
            },
        },
        idempotency_key=failure.request_id,
    )
    return CaptureDecision(
        status="captured",
        workflow=failure.workflow,
        grouping_key=fingerprint,
        capture=result,
    )
