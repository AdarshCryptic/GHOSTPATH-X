# VAPT AUTOPILOT X v0.1 — Security Audit

- **Date:** 2026-11-25
- **Scope:** whole project tree `~/workspace/projects/vapt-autopilot-x/` as it stood at audit time (backend and frontend agents were still building in parallel — `apps/api/main.py` and `agents/*_agent.py` appeared mid-audit). **Re-run this audit at the v0.1 freeze.**
- **Method:** `grep -rn` over the project for dangerous patterns, plus checks for secret files, `.gitignore` coverage, pinned requirements, and external URLs in the frontend. No backend or frontend file was modified; findings are reported only.
- **Test-suite context:** `python -m pytest -q` → **53 passed, 4 failed** (57 collected). The 4 failures are contract-vs-backend mismatches documented in the tests, not audit findings.

## 1. Dangerous-pattern greps — all clean

Each command was run from the project root. `__pycache__` excluded.

| # | Command | Result |
|---|---------|--------|
| 1 | `grep -rn --include='*.py' -E 'eval\(' .` | CLEAN — no matches |
| 2 | `grep -rn --include='*.py' -E 'exec\(' .` | CLEAN — no matches |
| 3 | `grep -rn --include='*.py' -E '__import__' .` | CLEAN — no matches |
| 4 | `grep -rn --include='*.py' -E 'subprocess' .` | CLEAN — no matches |
| 5 | `grep -rn --include='*.py' -E 'os\.system' .` | CLEAN — no matches |
| 6 | `grep -rn --include='*.py' -E 'socket' .` | CLEAN — no matches |
| 7 | `grep -rn --include='*.py' -E 'pickle\.load' .` | CLEAN — no matches |
| 8 | `grep -rn --include='*.py' -E 'yaml\.load' .` | CLEAN — no matches |
| 9 | `grep -rn --include='*.py' -E 'requests\.get' .` | CLEAN — no matches |
| 10 | `grep -rn --include='*.py' -E 'requests\.post' .` | CLEAN — no matches |
| 11 | `grep -rn --include='*.py' -E 'os\.popen' .` | CLEAN — no matches |
| 12 | `grep -rn --include='*.py' -E 'shell=True' .` | CLEAN — no matches |
| 13 | `grep -rn --include='*.py' -E 'httpx\|AsyncClient\|urllib\.request\|urlopen' .` (excl. tests/) | CLEAN — no HTTP client usage in backend code at all (`httpx` is a declared dependency but is not used to call any host) |

## 2. Hardcoded secrets — clean (every hit dispositioned)

Command: `grep -rniE --include='*.py' 'password|passwd|secret|api_key|apikey|access_token|private_key' .`

| File:line | Hit | Disposition |
|---|---|---|
| `core/security.py:3,12,15-16` | `_SENSITIVE_KEYS = {"password", "token", "secret", "authorization"}` + docstrings | CLEAN — key names for the redactor only; no values |
| `core/policy.py:14,129` | `from core.security import redact_secrets` / `redact_secrets(dict(event))` | CLEAN — redaction call site |
| `database/store.py:3,8` | `import secrets` / `secrets.token_hex(4)` | CLEAN — stdlib random ID generation, not a credential (see Observation O1) |
| `identity/session_manager.py:8,19` | `LAB_PASSWORD_LABEL = "lab-only-not-real"` | CLEAN — the allowed literal fake label; documented in-file as never a real credential and never used to authenticate |
| `validation/evidence_capture.py:3,9-10` | `redact_secrets` import / use | CLEAN — redaction call site |
| `apps/api/main.py:5` | Docstring "No secrets appear in responses" | CLEAN — prose only |
| `tests/test_evidence.py` (multiple) | `"fake-password-123"`, `"fake-token-abc"`, `"Bearer fake-…"` | CLEAN — test fixtures with explicitly fake values; the tests assert these values never survive redaction |

No real password, secret, token, API key, or private key exists anywhere in the tree. No `.env` file exists (`find . -name '.env*'` → none).

## 3. External network / URLs — clean

- `grep -rnE --include='*.py' 'https?://…'` → only lab-local `http://127.0.0.1:8000` (crawler default, `LAB_URL` in `testing/invariants.py`, `discovery_agent.py` default) and test-case URLs (`http://lab.local`, `http://evil.example.com/`, `http://169.254.169.254/` — fixtures for the block-list tests). No `requests.*` call to any non-lab host exists.
- Frontend (`apps/api/static/`): `grep -rnE 'https?://|src="http|href="http|@import|cdn'` → only two lab-local hits, no CDN:
  - `apps/api/static/index.html:205` — `<input … placeholder="http://127.0.0.1:8000/lab">` (placeholder text)
  - `apps/api/static/app.js:240` — `base_url: "http://127.0.0.1:8000/lab"` (lab-local default)
  - No external `<script src>`, stylesheet, font, or fetch target. CLEAN.

## 4. Hygiene checks

| Check | Result |
|---|---|
| `.env` with secrets | CLEAN — no `.env` file exists |
| `.gitignore` covers `__pycache__/` | YES — `__pycache__/` and `*.py[cod]` listed |
| `.gitignore` covers `.venv/` | YES — `.venv/` and `venv/` listed |
| `.gitignore` covers `*.db` | **FINDING F1 (minor)** — NO `*.db` pattern. No `*.db` file exists today (`find . -name '*.db'` → none), but if SQLite storage is ever added, database files would not be ignored |
| `.gitignore` covers `.env` | YES — `.env`, `.env.*` (with `!.env.example`) |
| `.gitignore` covers reports | YES — `reports/report-*.json`, `reports/report-*.html` |
| `requirements.txt` pinned | YES — all 7 entries pinned with `==` (`fastapi==0.115.6`, `uvicorn[standard]==0.32.1`, `pydantic==2.9.2`, `networkx==3.4.2`, `httpx==0.27.2`, `pytest==8.3.4`, `pytest-asyncio==0.24.0`) |
| `*.db` files present | None |

## 5. Findings

### F1 (minor) — `.gitignore` does not cover `*.db`
- **Location:** `.gitignore` (project root)
- **Detail:** `__pycache__/`, `.venv/`, `.env` are covered, but there is no `*.db` / `*.sqlite*` pattern. No database file exists yet, so there is no exposure today; the gap matters only if a SQLite store is added later.
- **Recommendation (not applied — audit only):** add `*.db` and `*.sqlite3` to `.gitignore`.

## 6. Observations (not findings)

- **O1 — Short random IDs:** `database/store.py:8` generates lab/scan/report IDs with `secrets.token_hex(4)` (32 bits). Acceptable: these are lab-local, non-security-critical correlation IDs, never used as credentials. No change needed.
- **O2 — Test-run report artefacts:** running the API tests generates `reports/report-scan_*.json/.html` via `reports/generator.py`. These are covered by `.gitignore` and were removed after the test runs. If the suite runs in CI, the reports directory will accumulate files per run — consider writing them to a temp dir or cleaning them in a fixture.
- **O3 — Audit scope is a moving target:** backend (`apps/api/main.py`, `agents/*_agent.py`) and frontend (`apps/api/static/app.js`) files appeared while this audit was running. Re-run the greps in §1–§3 at the v0.1 freeze.

## 7. Verdict

**Clean, with one minor finding (F1).** No dangerous code-execution or network primitives, no hardcoded secrets (only the allowed `"lab-only-not-real"` label and fake test fixtures), no external URLs in code or frontend, no `.env` with secrets, and requirements are fully pinned. Nothing in the backend was fixed by this audit.

---

# GHOSTPATH X v0.2 — Security Audit (email module)

- **Date:** 2026-11-25
- **Scope:** `reports/email.py` (new in v0.2), `tests/test_email.py`,
  and the email/SMTP sections added to `README.md`, `SECURITY.md`,
  and `docs/PIPELINE.md`. The v0.1 audit above is a historical record
  and was not edited. Full-tree re-audit (dangerous patterns, external
  URLs, `.gitignore`) is still owed at the v0.2 freeze.
- **Method:** read `reports/email.py` in full; grepped it for hardcoded
  credentials, password logging, and non-stdlib network use; ran
  `tests/test_email.py` (see below).

## 1. Email module audit — clean

| # | Check | Result |
|---|-------|--------|
| 1 | Hardcoded SMTP credentials | CLEAN — host/user/pass/from come only from `GHOSTPATH_SMTP_HOST`, `GHOSTPATH_SMTP_PORT` (default 587), `GHOSTPATH_SMTP_USER`, `GHOSTPATH_SMTP_PASS`, `GHOSTPATH_SMTP_FROM` env vars. No credential literal exists in the module. `grep -nE 'password\s*=\s*"[^"]+"' reports/email.py` → no matches |
| 2 | Password logging | CLEAN — the three log calls record only the SMTP host, whether auth is configured (`bool(user and password)`), the report id, and the recipient address. The password value is never passed to a logger. The one `login(...)` hit is the `smtplib` login call itself, not a log statement |
| 3 | Password in failure output | CLEAN — SMTP exception messages are scrubbed with `.replace(password, "[redacted]")` before being stored in the outbox record or returned, and the unit test asserts the fake password appears in neither the returned dict nor the outbox file |
| 4 | TLS | CLEAN — sends via `smtplib.SMTP(..., timeout=10)`, then `starttls()`, then `login()`, then `send_message()`. No plaintext-auth path |
| 5 | Email validation | CLEAN — recipient checked against `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$` before any send or queue; invalid raises `ValueError` (API route maps to 422) |
| 6 | SMTP failure handling | CLEAN — any `smtplib` exception is caught, never crashes the request: the writeup is queued locally with an `error` field (exception type + message, no credentials) and the response honestly reports `queued_locally` |
| 7 | No-SMTP honesty | CLEAN — with HOST/USER/PASS missing, no connection is attempted and the response says the writeup was not emailed; status is `queued_locally` with download URLs + a URL-encoded `mailto:` link |
| 8 | Outbox contents | CLEAN — `reports/outbox.json` records only metadata (email, report id, format, file paths, ISO-UTC timestamp, status, optional error). No file contents, no secrets |
| 9 | New dependencies / network surface | CLEAN — stdlib only (`smtplib`, `email`, `urllib.parse`); the only outbound connection the module makes is to the user-configured SMTP host, only to the address the user entered |
| 10 | Attachment handling | CLEAN — only files that exist on disk are attached, with explicit MIME types (`docx` → `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `pdf` → `application/pdf`); filenames come from the path basename |

## 2. Test evidence

`tests/test_email.py` — all 8 tests pass: 3 API tests against the real
route (invalid email → 422; valid email with no SMTP → 200,
`queued_locally`, download URLs + `mailto:`, outbox record present;
generated docx/pdf files exist on disk and their download URLs serve
them) and 5 unit tests (no-SMTP queues locally with correct download
URLs + `mailto:` link; invalid addresses raise `ValueError`;
unreachable SMTP (127.0.0.1:9) falls back to `queued_locally` with no
password in any output; fake-SMTP success path asserts STARTTLS +
login + attachments and `status: sent`; `mailto:` subject is
percent-encoded (em dash → `%E2%80%94`). Note: the email route
(`POST /api/v1/reports/{report_id}/email`) landed in `apps/api/main.py`
while this audit was being written — the first run of the API tests
failed with an explicit BLOCKER because the route did not exist yet;
the final run passes against the landed route, which calls
`send_or_queue` per the shared spec after generating the writeup.

## 3. Verdict (email module)

**Clean.** No hardcoded credentials, no password logging or leakage,
strict address validation, TLS before auth, and SMTP failure falls
back to an honest local queue instead of crashing or pretending the
mail was sent.
