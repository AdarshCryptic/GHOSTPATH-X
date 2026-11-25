# GHOSTPATH X

**Autonomous Attack-Path Discovery & Exploit Validation Engine — by Adarsh**

> *Follow the ghost. Prove the path.*

Version 0.4.0.

GHOSTPATH X is an AI-powered web application attack-path discovery and
exploit validation engine — **autonomous only inside an isolated,
explicitly authorised lab**.

Formerly VAPT AUTOPILOT X.

v0.2 adds hands-on challenges, automatic attack writeups (Word + PDF),
and an email box for sending the writeup. The core engine is unchanged
from v0.1: the LLM only reasons and proposes; deterministic Python
executes approved test primitives. No LLM claim is treated as proof —
validation independently checks expected vs observed.

## About

The dashboard has an **About** page (sidebar, right after Overview)
that explains what GHOSTPATH X is and what real-life problem it solves:
security scanners report hundreds of possible issues, but most are noise
— GHOSTPATH X finds the one verified path an attacker can actually walk
and proves it with reproducible evidence, using the lab example where
Customer B reads Customer A's order. It is a static page with custom
diagrams and an animated verified-path walkthrough — no scan needed,
no API calls.

## Lab

Target: OWASP Juice Shop Training Lab (simulated in-process).

- 3 identities: `customer_a` (customer, owns `order_1001`, tenant
  `tenant_a`), `customer_b` (customer, owns `order_1002`, tenant
  `tenant_b`), `administrator` (admin).
- Orders: `order_1001` (owner `customer_a`, shipped), `order_1002`
  (owner `customer_b`, paid).
- Workflow: `created -> paid -> shipped`. Valid: `created->paid`,
  `paid->shipped`. Invalid: `shipped->created`, `paid->created`,
  `created->shipped`.
- v0.1 numbers: 8 endpoints, 3 identities, 7 candidate attack paths,
  3 validated findings.

## Quick start (3 steps)

```bash
pip install -r requirements.txt
python run.py
# Open http://127.0.0.1:8000 in your browser
```

The dashboard auto-creates the Juice Shop Training Lab and runs a scan on
first load. (Using a virtualenv first is fine too, but not required.)

Create a lab, then a scan (the scan runs the full pipeline synchronously):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/labs \
  -H 'Content-Type: application/json' \
  -d '{"name":"Juice Shop Training Lab","base_url":"http://127.0.0.1:8000","environment":"lab"}'

curl -s -X POST http://127.0.0.1:8000/api/v1/scans \
  -H 'Content-Type: application/json' \
  -d '{"lab_id":"<lab_id>"}'

curl -s http://127.0.0.1:8000/api/v1/findings
```

Expected scan counts: `endpoints_discovered=8`, `identities_mapped=3`,
`attack_paths=7`, `validated_findings=3`.

## Challenges

GHOSTPATH X ships 6 hands-on challenges built from the same lab the
scanner explores. Each challenge is a small, self-contained attack-path
exercise:

1. **Download** the challenge brief from the dashboard
   (`GET /api/v1/challenges/{challenge_id}/brief`).
2. **Solve** it against the isolated lab — find the path, prove it with
   the same invariants the validator checks.
3. **Learn** from the worked solution and the auto-generated writeup,
   which explains the path, the evidence, and the fix.

Challenges are lab-only training material. Nothing leaves the lab, and
no challenge touches a real system.

## CTF Machines

GHOSTPATH X ships a curated catalogue of free places to practise —
downloadable vulnerable VMs and free online labs — so you can keep
solving after the built-in challenges. Open the **CTF Machines** page
on the dashboard: source cards at the top, filters for source,
difficulty, type and search, and a solve tracker (mark a machine
solved once you have rooted it and got the flag).

The catalogue is static curated data, not a live scrape: no external
calls at runtime, and the cost labels are honest — a platform is only
called "Free" when it really is 100% free.

| Source | Cost | What you get |
|---|---|---|
| VulnHub | 100% free | Downloadable VMs (Mr-Robot:1, DC-1..9, Kioptrix 1-5, Basic Pentesting, SickOs, Funbox) |
| HackTheBox | Free tier | Online VPN lab, Starting Point free; retired machines need VIP — not a download |
| TryHackMe | Free tier | Online guided rooms; many free rooms, paid for the rest |
| PortSwigger Web Security Academy | 100% free | Free web labs in the browser |
| OverTheWire | 100% free | Free wargames (SSH) |
| PicoCTF | 100% free | Free CTF challenges, beginner-friendly |
| Root-Me | Free tier | Free tier with premium challenges |
| Metasploitable 2/3 | Free | Downloadable vulnerable VM |
| OWASP apps (Juice Shop, DVWA, WebGoat, bWAPP) | Free | Free open-source vulnerable web apps, run in Docker |

Note: CyberSecLabs was checked on 2026-11-25 and is **not listed** — both
`cyberseclabs.co.uk` and `www.cyberseclabs.co.uk` did not resolve, so no
working homepage could be linked. It is left out rather than shipping a
dead link; if the site comes back, it can be added as a "Free + paid"
online lab.

API: `GET /api/v1/ctf-machines` (filters `?source=`, `?difficulty=`,
`?type=`, `?q=`), `GET /api/v1/ctf-machines/{id}`,
`GET /api/v1/ctf-machines/sources`, and
`POST /api/v1/ctf-machines/{id}/solved` with `{"solved": true}` to
track a solve (in-memory, same as the rest of v0.2).

Only attack systems you own or have explicit permission to test. Run downloaded VMs on Host-Only networking, never bridged to your home LAN.

## Auto writeup generation

After a scan completes, GHOSTPATH X generates an attack writeup
automatically — no manual report writing:

- **Word** (`.docx`) and **PDF** (`.pdf`) versions of the same writeup,
  from `POST /api/v1/scans/{scan_id}/writeup` (or the dashboard
  button; challenge writeups come from
  `POST /api/v1/challenges/{challenge_id}/writeup`).
- Each writeup covers the validated findings with the attack path, the
  observed evidence, and remediation, so the result is reproducible
  from the scan alone.
- Download either format from
  `GET /api/v1/reports/{report_id}/download?format=docx|pdf`.

## Email box

The dashboard has an email box: enter an email address and GHOSTPATH X
sends the attack writeup (Word or PDF) to it.

**Honest note — read this before expecting an email to arrive:** real
sending needs the user's own SMTP server, configured with the
`GHOSTPATH_SMTP_*` environment variables (`GHOSTPATH_SMTP_HOST`,
`GHOSTPATH_SMTP_PORT` — default 587, `GHOSTPATH_SMTP_USER`,
`GHOSTPATH_SMTP_PASS`, `GHOSTPATH_SMTP_FROM` — default the user).
Without SMTP configured, the writeup is **not** actually emailed.
Instead it is generated and queued locally (`reports/outbox.json`),
and the response gives you download links plus a `mailto:` link so you
can send it yourself. The dashboard always says which of the two
happened — `sent` or `queued_locally` — and never pretends an email
went out when it did not.

```bash
export GHOSTPATH_SMTP_HOST=smtp.example.com
export GHOSTPATH_SMTP_USER=you@example.com
export GHOSTPATH_SMTP_PASS='your-smtp-password'   # never commit this
```

## Layout

- `core/` — config, policy engine, security (redaction, evidence hashing)
- `lab/` — simulated target, scope validation, reset
- `agents/` — Discovery, Identity, Workflow, Graph, Reasoning,
  Validation, Reporting (deterministic; LLM is a local stub only)
- `discovery/`, `identity/`, `workflows/` — inventory, sessions, roles,
  state model
- `graph/` — NetworkX security graph, path scoring
- `testing/` — authorization / workflow / session invariants
- `validation/` — invariant executor, evidence capture
- `reports/` — report generator (JSON + HTML, no external assets),
  writeup generator (Word + PDF), email delivery (`reports/email.py`,
  stdlib only) with local outbox (`reports/outbox.json`)
- `challenges/` — the 6 downloadable challenges
- `ctf_machines/` — the curated free CTF machine / lab catalogue (v0.3)
- `database/` — in-memory store
- `apps/api/` — FastAPI app
- `docs/` — `DESIGN.md`, `PIPELINE.md`, `SECURITY_AUDIT.md`

## Deferred to v0.3

Not in v0.2 (still simulated / in-memory / stubbed):

- Real Playwright browser automation
- PostgreSQL persistent storage
- Neo4j graph database
- Real Ollama / LLM reasoning (local LLM still a stub)
- Docker isolation for the lab
- Redis / Celery background jobs
- MinIO object storage
- React frontend
- JWT / RBAC authentication
- Destructive tests
- Persistent storage beyond the in-memory store

## Safety

See `SECURITY.md`. Lab-only, fake test accounts only. No external
network, no real credentials, no hardcoded secrets.
