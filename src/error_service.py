"""HTTP entry point for nonprofit backend error capture."""

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .nonprofit_errors import BackendFailure, CaptureDecision, capture_backend_failure

service = FastAPI(title="Nonprofit backend error capture")


@service.post("/backend-failures", response_model=CaptureDecision)
def record_backend_failure(failure: BackendFailure) -> CaptureDecision:
    try:
        return capture_backend_failure(failure, InfraiClient())
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc.details.get("message", "rejected"))},
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.error_service:service", host="127.0.0.1", port=8000)
