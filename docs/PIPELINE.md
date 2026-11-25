# GHOSTPATH X — Pipeline (v0.2.0)

A scan runs the full pipeline **synchronously** on `POST /api/v1/scans`.

## Order

1. **Discovery** — crawler returns the 8 endpoints (deduplicated by
   method + path template). `agent_status`: Discovery Complete.
2. **Identity** — 3 identities mapped with roles and tenants.
   `agent_status`: Identity Complete.
3. **Workflow** — states (`created`, `paid`, `shipped`) and valid /
   invalid transitions. `agent_status`: Workflow Complete.
4. **Graph Intelligence** — NetworkX security graph built; 7 candidate
   Identity → Endpoint → Resource paths enumerated and scored.
   `agent_status`: Graph Intelligence Complete.
5. **Attack Reasoner** — rule-based ranker (`LocalReasoner`) orders the
   7 hypotheses by weighted score. `agent_status`: Attack Reasoner
   Active → Complete.
6. **Validation** — 5 invariants run against the simulated target;
   each failure is reproduced a second time. Only reproduced failures
   become findings (exactly 3 in v0.1). `agent_status`: Validation
   Running → Complete.
7. **Evidence / Reporting** — redacted, hashed evidence attached;
   JSON + HTML report written to `reports/`.
   `agent_status`: Evidence Waiting → Complete.

## Final scan state

- `status`: `completed`
- `progress`: `100`
- `phase`: `Validation complete`
- `endpoints_discovered`: `8`
- `identities_mapped`: `3`
- `attack_paths`: `7`
- `validated_findings`: `3`

## Validation statuses

`hypothesis` → `candidate` → `validated` / `rejected` /
`inconclusive` / `needs_review`. A `pass` invariant maps to `rejected`
(no finding); a reproduced `fail` maps to `validated`.

## v0.2 — Challenges, writeup, email (after the scan)

The v0.1 pipeline above is unchanged. v0.2 adds a post-scan flow:

8. **Challenges** — 6 downloadable challenges built from the same lab
   the scanner explored. Flow: challenge brief download
   (`GET /api/v1/challenges/{challenge_id}/brief`) → solve it
   against the isolated lab (`POST /api/v1/challenges/{challenge_id}/solve`)
   → learn from the worked solution and the auto-generated writeup.
9. **Auto writeup** — after a scan completes, an attack writeup is
   generated automatically in Word (`.docx`) and PDF (`.pdf`) from the
   validated findings, the attack paths, and the evidence
   (`POST /api/v1/scans/{scan_id}/writeup`; challenge writeups:
   `POST /api/v1/challenges/{challenge_id}/writeup`), downloadable from
   `GET /api/v1/reports/{report_id}/download?format=docx|pdf`.
10. **Email** — the dashboard email box posts to
    `POST /api/v1/reports/{report_id}/email`, which calls
    `reports/email.py::send_or_queue` with the generated writeup
    file(s). Two honest outcomes, both reported as-is:
    - **SMTP configured** (`GHOSTPATH_SMTP_*` env vars) → the writeup
      is sent with STARTTLS + login, status `sent`.
    - **No SMTP configured, or sending failed** → nothing is pretended
      sent. The writeup is queued locally in `reports/outbox.json`
      (metadata only: email, report id, format, file paths, timestamp,
      status `queued_locally`), and the response carries download URLs
      + a `mailto:` link, status `queued_locally`.

Full flow: challenge download → solve → learn → auto writeup
(docx/pdf) → email `queued_locally` / `sent`.

## v0.3 — CTF Machines (catalogue, no scan involved)

The CTF Machines page is a catalogue, not part of the scan pipeline.
Data flows one way, with no live scraping and no external calls at
runtime:

1. **Static curated data** — `ctf_machines/machines.py` holds the
   machine list and the platform list (name, cost label, type,
   homepage, description). Cost labels are written honestly at the
   source: only 100% free platforms say "Free"; partly-free ones say
   "Free tier" or "Free + paid".
2. **API filters** — `GET /api/v1/ctf-machines` filters the static list
   in-process (`?source=`, `?difficulty=`, `?type=`, `?q=`); single
   machine at `GET /api/v1/ctf-machines/{id}`, platform list at
   `GET /api/v1/ctf-machines/sources`.
3. **Dashboard page** — the CTF Machines page renders source cards and
   the filtered machine list from those endpoints.
4. **Solved state** — `POST /api/v1/ctf-machines/{id}/solved`
   (`{"solved": true|false}`) flips a flag held in-memory, same as the
   rest of v0.2: it survives while the server runs and resets on
   restart. No database, no persistence, no network.

## v0.4 — About page (static, no scan involved)

The About page is static: it makes no API calls and needs no scan, lab,
or backend state — it renders from the served `index.html` alone. It
sits in the sidebar navigation right after Overview (section id
`page-about`), so it is the first thing a new user sees after the
overview, before any scan-dependent page.
