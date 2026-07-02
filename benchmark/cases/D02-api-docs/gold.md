# Ledger Export API
Version: 2026-07-15

## Endpoint
`POST /v2/ledger_exports` creates an asynchronous export job.

### Request fields
| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| workspace_id | string | yes | Must match `ws_` prefix. |
| period_start | date | yes | Inclusive ISO date. |
| period_end | date | yes | Exclusive ISO date. |
| include_voided | boolean | no | Defaults to false. |

> Warning: `period_end` is exclusive even when the UI label says Through.

<!-- page 2 -->

## Example request
```json
{"workspace_id":"ws_north_01","period_start":"2026-06-01","period_end":"2026-07-01","include_voided":false}
```

## Response
```json
{"job_id":"job_7841","status":"queued","download_url":null}
```

Retry policy: clients should retry `429` after the `Retry-After` header and should not retry `400`.

<!-- page 3 -->

## Error codes
| Code | Name | Retryable | Meaning |
| --- | --- | --- | --- |
| 400 | invalid_period | no | Date range failed validation. |
| 401 | missing_auth | no | API key was absent or invalid. |
| 409 | export_exists | yes | Identical export is still running. |
| 429 | rate_limited | yes | Workspace exceeded burst limit. |

The exact phrase `export_exists` must remain in monospace or plain text.

<!-- page 4 -->

## Webhook payload
```ts
type LedgerExportWebhook = {
  job_id: string;
  status: 'completed' | 'failed';
  download_url: string | null;
};
```

Security note: never expose the raw `OPENAI_API_KEY` or `GOOGLE_VERTEX_API_KEY` in logs.
