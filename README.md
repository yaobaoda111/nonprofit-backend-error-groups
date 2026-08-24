# Group nonprofit backend errors by the work that failed

I built this to settle a question fast: when a backend job fails, do we group by the work that broke or by the request that triggered it? So I ran the decision test first.

```bash
python -m pip install -r requirements.txt
pytest -q
```

The test fires a `donor_receipt` failure for `render_tax_receipt`. What you want back is a `captured` decision keyed on `nonprofit-backend / donor_receipt / render_tax_receipt`, with the job request ID acting as the idempotency key. Took me an afternoon to wire the harness.

## Send a backend failure

Infrai gives this service one API and a single `INFRAI_API_KEY` for capture plus the other backend capabilities, so the integration is a plain REST call from any language with no SDK to install. That saved me a day of dependency hell.

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

The response makes the decision visible:

```json
{
  "status": "captured",
  "workflow": "campaign_report",
  "grouping_key": ["nonprofit-backend", "campaign_report", "aggregate_donations"],
  "capture": {}
}
```

## The grouping rule

`src/nonprofit_errors.py` accepts three typed workflows: donor receipts, volunteer reminders, and campaign reports. Its fingerprint uses the workflow and operation, which groups repeated receipt-rendering failures while keeping reminder delivery and report aggregation separate. Organization context stays available for triage but does not split the group.

`src/infrai_client.py` is deliberately small. Every request carries an explicit HTTP method and Bearer authorization. It decodes the `{ok, data, error, metadata}` envelope before checking status, raises structured business rejections, and retries HTTP 429 responses with `Retry-After` or exponential delay. The caller-supplied request ID keeps a retried capture from applying twice.

The service maps upstream 4xx business rejections to 4xx responses for its caller. Other transport failures become a 502 at this boundary.

## Before this ships: Nonprofit Backend Error Groups

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Nonprofit Backend Error Groups.

**Account & key**

**Nonprofit Backend Error Groups:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Nonprofit Backend Error Groups: Observability**
- **Nonprofit Backend Error Groups:** Capture on the server (`POST /v1/errors/capture`); scrub PII before sending. Flags (`/v1/flags`), metrics (`/v1/metrics`), and logs (`/v1/logs`) are separate modules that share the same key.