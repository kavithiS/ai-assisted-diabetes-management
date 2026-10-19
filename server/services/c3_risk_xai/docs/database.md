# C3 database (Postgres schema `c3`)

FR13 history, FR15 model + schema versions, FR16 deletion, NFR12 auditability.
Only schema `c3` is used; C3 never reads c1, c2 or c4. The connection comes from
`DATABASE_URL` (environment or the local, gitignored `.env`), never from code.

## Tables

| Table | Holds | Notes |
|---|---|---|
| `risk_profiles` | One questionnaire submission (answers as JSONB), `schema_version`, `consent` | Demo data only until ethics approval (`consent` stays false) |
| `assessments` | Device pseudonym, link to the profile, status, band, `model_version`, `schema_version`, explanation (factors tagged `evidence_level: real_data`), `dhs` (null until the DHS phase), time | Deleting a profile deletes its assessments (cascade) |
| `dhs_history` | DHS score + components over time, `provisional` | Filled by the DHS phase |
| `audit_log` | Pseudonym, action (`assess`, `history_read`, `delete_device_records`), short detail (status or count), time | Never answers or results |
| `external_inputs` | C1 nutrition / C2 forecast snapshots, `source`, `is_mock` | Mock until a C1/C2 contract exists |

The user key is the random device pseudonym made by the app (32 hex characters), sent
in the `X-Device-Id` header so it never appears in access logs. No names or contacts.

## API

| Call (through the gateway) | Does |
|---|---|
| `POST /api/v1/risk/assess` + `X-Device-Id` | Answers as before and saves it; response has `saved: true/false` |
| `GET /api/v1/risk/history` + `X-Device-Id` | This device's results, newest first (no answers returned) |
| `DELETE /api/v1/risk/history` + `X-Device-Id` | Deletes this device's records; audit entry with the count |
| `GET /api/v1/risk/status` | Also `database`: `ok`, `unreachable`, `not_set_up` or `off` |

Best-effort: if Postgres is stopped, assessments are still answered (`saved: false`),
history/delete answer 503, and the app shows this session's results with a notice.

## Commands (PowerShell, repository root)

```powershell
# Create / update the c3 tables (reads DATABASE_URL from .env)
.\.venv\Scripts\python.exe -m alembic -c server/services/c3_risk_xai/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m alembic -c server/services/c3_risk_xai/alembic.ini current   # expect 0001_c3_initial (head)

# Look at the tables (asks for the password; do not put it on the command line)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -p 5433 -U diacare -d diacare -c "\dt c3.*"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h 127.0.0.1 -p 5433 -U diacare -d diacare -c "select action, detail, created_at from c3.audit_log order by created_at desc limit 10"
```

`.env` keys used: `DATABASE_URL` (port 5433 on the C3 owner's laptop). Optional:
`C3_PERSISTENCE=false` turns saving off.
