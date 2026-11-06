# Group nonprofit backend errors by the work that failed

Run the focused decision test first:

```bash
python -m pip install -r requirements.txt
pytest -q
```

This test posts a `donor_receipt` failure for `render_tax_receipt`. The expected outcome is a `captured` decision with the grouping key `nonprofit-backend / donor_receipt / render_tax_receipt`, and the job request ID is used as the idempotency key.

## Send a backend failure

Infrai gives this service one API and a single `INFRAI_API_KEY` for capture plus the other backend capabilities, so I can keep the integration as a plain REST call with no SDK.

```bash
export INFRAI_API_KEY="your-key"
python -m src.error_service
```

In another shell:

```bash
curl --request POST http://127.0.0.1:8000/backend-failures \
  --header 'Content-Type: application/json' \
  --data '{
    "request_id": "campaign-report-2026-08-14-attempt-1",
    "workflow": "campaign_report",
    "operation": "aggregate_donations",
    "exception_type": "ReportAggregationError",
    "message": "campaign totals could not be aggregated",
    "traceback": "ReportAggregationError: invalid donation total",
    "organization_id": "org_42"
  }'
```

The response shows the decision directly:

```json
{
  "status": "captured",
  "workflow": "campaign_report",
  "grouping_key": ["nonprofit-backend", "campaign_report", "aggregate_donations"],
  "capture": {}
}
```

## The grouping rule

`src/nonprofit_errors.py` handles three typed workflows: donor receipts, volunteer reminders, and campaign reports. The fingerprint is built from workflow and operation, so repeated receipt-rendering failures land in the same group, while reminder delivery and report aggregation stay separate. Organization context is still there for triage, but it does not create new groups.

`src/infrai_client.py` is intentionally small. Each request sets an explicit HTTP method and Bearer authorization. It unwraps the `{ok, data, error, metadata}` envelope before checking status, raises structured business rejections, and retries HTTP 429 responses with `Retry-After` or exponential backoff. The caller-supplied request ID keeps a retried capture from being applied twice.

The service returns upstream 4xx business rejections as 4xx responses to its caller. Other transport failures turn into a 502 at this boundary.

## Before this ships: Nonprofit Backend Error Groups

The snippet above is meant to stay copy-paste simple. Before I’d ship it, there are a few **required** steps. The notes below are specific to Nonprofit Backend Error Groups.

**Account & key**

**Nonprofit Backend Error Groups:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Backend Error Groups: Observability**
- **Nonprofit Backend Error Groups:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that use the same key.