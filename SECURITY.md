# Security Policy

## Scope

GHOSTPATH X v0.2.0 is an autonomous web-application pentest system that
runs **only inside an isolated, explicitly authorised lab**. It must never
be pointed at a production system, a system without written authorisation,
or any host outside the lab allowlist (`127.0.0.1`, `lab.local`).

## Lab-only credentials

All lab identities (`customer_a`, `customer_b`, `administrator`) are fake,
simulated, in-process test accounts. They are not real credentials. The
string `lab-only-not-real` is used only as a label marking a value as a
lab-only placeholder — never as a real password, token, or secret.

## Rules

- No external network access: `allow_external_network` is `False`.
- No state-changing tests against real systems:
  `allow_state_changing_tests` is `False` for the lab policy default;
  state-changing primitives run only against the simulated in-process lab.
- No hardcoded secrets anywhere in the codebase. Secrets are redacted
  from evidence and audit logs by `core/security.py::redact_secrets`
  (keys: `password`, `token`, `secret`, `authorization`).
- An LLM claim is never proof. A finding is only `validated` when the
  deterministic validation executor independently reproduces the
  expected-vs-observed mismatch twice.
- Evidence is hashed (SHA-256) so reports are reproducible.

## Email / SMTP handling (v0.2)

The email box (`reports/email.py`, stdlib `smtplib` / `email` only)
sends the generated attack writeup (Word / PDF) to an address the user
types in:

- **Credentials come only from environment variables**
  (`GHOSTPATH_SMTP_HOST`, `GHOSTPATH_SMTP_PORT`, `GHOSTPATH_SMTP_USER`,
  `GHOSTPATH_SMTP_PASS`, `GHOSTPATH_SMTP_FROM`). They are never
  hardcoded, never written to a file, and never stored in the repo.
- **TLS is mandatory for sending**: the module connects with
  `smtplib.SMTP`, upgrades with `STARTTLS`, and only then logs in.
- **The password is never logged.** Logs record at most the SMTP host
  and whether auth is configured — never the secret. SMTP failure
  messages are scrubbed of the password before they are recorded.
- **The local outbox (`reports/outbox.json`) contains only metadata**:
  recipient email address, report id, format, file paths, timestamp,
  and queue status. It contains no file contents and no secrets.
- **No SMTP, no pretence.** When no SMTP server is configured (or
  sending fails), the writeup is generated and queued locally with
  download + `mailto:` links. The API reports `queued_locally`, never
  `sent`.
- **Address validation.** Recipient addresses are checked against a
  strict regex before anything is sent; an invalid address is rejected
  with HTTP 422.
- Outbound mail goes only to the address the user entered, only from
  the configured SMTP account, and only with the writeup files for the
  report they asked about. The module makes no other network
  connection.

## Owner lock (v0.4)

The dashboard has a locked "Owner" section (`POST /api/v1/owner/unlock`,
`GET /api/v1/owner/details`):

- **PIN stored only as a SHA-256 hash** (`core/config.py`). The PIN
  itself is never stored in the code, in a file, or in a log, and is
  verified server-side with a constant-time comparison
  (`hmac.compare_digest`).
- **Rate-limited:** after 5 failed attempts from one client, that
  client is locked out for 60 seconds. During a lockout every attempt
  returns 429 with a generic message that does not reveal whether the
  PIN was right. A successful unlock resets the failure count.
- **Short-lived token:** a successful unlock returns a random session
  token (`secrets.token_urlsafe`), kept only in memory on the server
  with a 30-minute expiry. The owner details are served only by
  `GET /api/v1/owner/details` and only with a valid, unexpired token.
- **Frontend never stores the PIN:** it is sent once in the unlock
  request and then cleared. Only the session token is kept, in
  `sessionStorage`, and it is dropped when it expires or when the
  owner locks the section again.
- **Showcase lock, NOT real authentication.** A 6-digit PIN is not
  secure and must never guard real secrets. The owner details contain
  no contact details, credentials, or other personal data — only the
  owner's name, role, and the projects he built. This lock exists to
  show the pattern, not to protect anything sensitive.

## Reporting a vulnerability

If you find a security issue in this project itself, report it privately
to the maintainer. Do not open a public issue with exploit details.
