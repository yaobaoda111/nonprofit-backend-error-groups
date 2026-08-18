from typing import Any

from src.nonprofit_errors import BackendFailure, Workflow, capture_backend_failure


class RecordingClient:
    def __init__(self) -> None:
        self.payload: dict[str, Any] = {}
        self.idempotency_key = ""

    def capture_exception(
        self, exception_payload: dict[str, Any], *, idempotency_key: str
    ) -> dict[str, Any]:
        self.payload = exception_payload
        self.idempotency_key = idempotency_key
        return {"accepted": True}


def test_receipt_failures_group_by_workflow_and_operation() -> None:
    client = RecordingClient()
    failure = BackendFailure(
        request_id="receipt-job-2048-attempt-1",
        workflow=Workflow.DONOR_RECEIPT,
        operation="render_tax_receipt",
        exception_type="TemplateError",
        message="tax receipt template could not be rendered",
        traceback="TemplateError: missing receipt total",
        organization_id="org_42",
    )

    decision = capture_backend_failure(failure, client)  # type: ignore[arg-type]

    assert decision.status == "captured"
    assert decision.grouping_key == [
        "nonprofit-backend",
        "donor_receipt",
        "render_tax_receipt",
    ]
    assert client.payload["fingerprint"] == decision.grouping_key
    assert client.payload["context"]["organization_id"] == "org_42"
    assert client.idempotency_key == "receipt-job-2048-attempt-1"
