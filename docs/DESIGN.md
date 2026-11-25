# GHOSTPATH X — Design (v0.2)

> Renamed in v0.2 from "VAPT AUTOPILOT X" (v0.1 name, kept here only as a
> history note). New name: **GHOSTPATH X** — Autonomous Attack-Path
> Discovery & Exploit Validation, by **Adarsh**.
> Tagline: *"Follow the ghost. Prove the path."*

## Purpose

Autonomous web-application pentester that runs only inside an isolated,
explicitly authorised lab. It explores an app, understands users and
workflows, discovers weaknesses, validates attack paths, and produces
reproducible evidence.

## Principles

- **AI reasons, deterministic Python executes.** The LLM (local stub in
  v0.1) only proposes and ranks hypotheses. Approved test primitives are
  executed by deterministic code.
- **No LLM claim is proof.** A finding is `validated` only when the
  validation executor independently reproduces the expected-vs-observed
  mismatch twice.
- **Lab only.** Policy allowlist: `127.0.0.1`, `lab.local`. No external
  network, no DNS lookup to external resolvers, no real credentials.
- **Evidence is hashed.** Every captured request/response is redacted
  and SHA-256 hashed so a report is reproducible.

## Architecture

```
apps/api/main.py        FastAPI, synchronous scan pipeline
core/                   config, policy engine, redaction/hashing
lab/                    simulated target, scope, reset
database/store.py       in-memory store (labs, scans, findings, reports, audit)
agents/                 7 agents, all deterministic (BaseAgent ABC)
discovery/              endpoint inventory + dedupe crawler
identity/               role registry, fake session manager
workflows/              state model + transition analyser
graph/                  NetworkX MultiDiGraph, path scoring
testing/                authorization / workflow / session invariants
validation/             invariant executor + evidence capture
reports/                JSON + HTML report generator
```

## Lab (simulated, in-process)

- Identities: `customer_a` (customer, `order_1001`, `tenant_a`),
  `customer_b` (customer, `order_1002`, `tenant_b`),
  `administrator` (admin).
- Workflow: `created -> paid -> shipped`.
- 8 endpoints, 7 candidate attack paths, 3 validated findings.

## Findings (v0.1, unchanged in v0.2)

- FIND-001 High — Cross-user object authorization
  (`GET /api/orders/1001` as `customer_b`)
- FIND-002 High — Missing function-level authorization
  (`POST /api/admin/promote` as `customer_a`)
- FIND-003 Medium — Invalid workflow transition
  (`POST /api/orders/1001/transition` shipped → created)

## Theme & branding (v0.2) — Ghost Terminal

### Research rationale

The dashboard is a security-operations console, so the theme is built
for long sessions in a dark room: a near-black blue-tinted base keeps
glare down, while a single cool accent (cyan) carries all interactive
meaning and a second, warmer green marks only *verified* things
(validated paths / findings). That two-accent split — cyan = "look here /
clickable", green = "proven" — is the same convention the GHOST project
used (`#0B0F0E` base, `#00E5A0` ghost green, `#FF3B5C` danger), carried
over so the two projects read as one family. Danger red is reserved for
critical severity and destructive actions; amber only for warnings and
"medium/high" severity, so colour never cries wolf. Panels use a subtle
glass effect (translucent `#0B1220` + blur) over the base with hairline
cyan-tinted borders, which gives depth without the heavy solid blocks of
the v0.1 theme. Everything is offline-safe: no CDN, no webfonts, no
external URLs anywhere in the frontend — fonts fall back to system
stacks and all imagery is generated locally (see Assets).

### Palette (exact hexes)

| Token | Hex | Used for |
|---|---|---|
| Base background | `#05080F` | page background |
| Panel | `#0B1220` | cards, sidebar |
| Panel 2 | `#0F172A` | inputs, canvas, nested surfaces |
| Border | `rgba(34,211,238,0.12)` | 1px panel borders |
| Border strong | `rgba(34,211,238,0.28)` | focused / active borders |
| Text | `#E6EDF3` | primary text |
| Muted | `#8B9BB4` | secondary text, labels |
| Accent cyan | `#22D3EE` | links, buttons, active nav, live dots |
| Ghost green | `#00E5A0` | verified paths, validated findings, success |
| Danger | `#FF3B5C` | critical severity, errors, destructive actions |
| Amber | `#FFB020` | warnings, high severity, hints |
| Blue | `#38BDF8` | secondary accent (endpoints, info badges) |
| Purple | `#A855F7` | candidate badges, identity agent |
| Yellow | `#FACC15` | medium severity, graph states |

CSS variables live in `apps/api/static/styles.css` (`--bg`, `--panel`,
`--cyan`, `--green`, `--danger`, `--amber`, …).

### Fonts (system fallbacks only — no webfonts)

- Headings / numbers: `"Space Grotesk", "Inter", -apple-system, "Segoe UI", Roboto, sans-serif`
- Body: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- Mono: `"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace`

### Branding strings

- App name: **GHOSTPATH X** (`core/config.py`: `app_name="GHOSTPATH X"`,
  `version="0.2.0"`; also `pyproject.toml` and the `run.py` banner).
- Tagline: **"Follow the ghost. Prove the path."** (sidebar + Overview
  header).
- Author: **Adarsh** — sidebar profile card (avatar circle "A",
  "Security Researcher"), Overview header "GHOSTPATH X — by Adarsh",
  footer on every screen: "Built by Adarsh • GHOSTPATH X v0.2",
  report HTML title/h1 "GHOSTPATH X — Scan Report" with an
  "Author: Adarsh" line and the same footer.

## Assets (all local, `apps/api/static/assets/`)

Generated by `scripts/generate_assets.py` (stdlib + Pillow only;
`pillow==11.0.0` in `requirements.txt`). Re-run the script to regenerate
everything deterministically. All references are relative paths — no
external URLs.

| File | What it is | Where it is used |
|---|---|---|
| `logo.svg` | Hand-written ghost + network-path emblem: ghost silhouette with cyan/green glow on dark, five connected nodes along the bottom, red target node | Sidebar logo, Overview brand header |
| `logo.png` | Same emblem rasterised with PIL, 256×256, dark bg, cyan glow | Favicon-style / offline fallback copy of the logo |
| `graph-empty.svg` | Attack Graph empty/loading illustration: faint cyan nodes + edges on a dark panel | Attack Graph page empty state (`#graph-empty`, shown when the graph has no nodes) |
| `radar.gif` | Animated radar/scan sweep (PIL, 480×240, 24 frames, loop, ~66 KB): rotating cyan sweep + fading green blips | Live Scans page (`#radar-wrap`, shown only while a scan is running) |
| `agent-discovery.svg` | Magnifier mark, cyan | Agent Status list, Discovery Agent |
| `agent-identity.svg` | Person mark, purple | Agent Status list, Identity Agent |
| `agent-workflow.svg` | Flow / stacked-steps mark, amber | Agent Status list, Workflow Agent |
| `agent-graph.svg` | Connected-nodes mark, ghost green | Agent Status list, Graph Intelligence |
| `agent-reasoning.svg` | Spark mark, cyan | Agent Status list, Attack Reasoner |
| `agent-validation.svg` | Shield-check mark, ghost green | Agent Status list, Validation Agent |
| `agent-evidence.svg` | Document mark, danger red | Agent Status list, Evidence Agent |

Agent icons render as `<img class="agent-icon">` with an `onerror`
fallback to the existing coloured status dot, so a missing file never
breaks the list.

## New in v0.2 (dashboard)

- **Challenges screen** (sidebar, after Findings): grid `#challenges-grid`,
  `renderChallenges()` fetches `GET /api/v1/challenges` and renders cards
  (id, title, difficulty badge, category, story, objective, Download
  brief → `GET /api/v1/challenges/{id}/brief`, 3 hint buttons revealing
  hints one at a time, Solve form → `POST /api/v1/challenges/{id}/solve`,
  Learn section with lesson + remediation + graph path, Generate writeup
  → `POST /api/v1/challenges/{id}/writeup`). Written defensively: if the
  challenges backend is not up yet, the screen shows error text and the
  rest of the dashboard is unaffected.
- **Email writeup box** (Findings + Evidence & Reports pages): email
  input + format selector (Word / PDF / Both) + "Send writeup" →
  `POST /api/v1/reports/{report_id}/email` with `{email, format}`;
  client-side regex `^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$`;
  `queued_locally` shows download links + a mailto link, `sent` shows
  success, errors show the server message.
- **Live Scan radar**: `assets/radar.gif` + CSS pulse animation
  (`.live-dot`) on live status dots while a scan is running.

## New in v0.4 — About page

A static explainer page, no API calls and no scan dependency: it
renders from the served `index.html` alone, so it works before any lab
is created or scan is run. Sidebar nav sits right after Overview;
the section id is `page-about`.

### What it explains

- **What GHOSTPATH X is** — an autonomous attack-path discovery and
  exploit validation engine that runs only inside an isolated,
  explicitly authorised lab.
- **The real-life problem** — scanners report hundreds of possible
  issues and most are noise; GHOSTPATH X finds the one verified path
  an attacker can actually walk and proves it with reproducible
  evidence, instead of a list of maybes.
- **The lab example** — Customer B reads Customer A's order
  (`GET /api/orders/1001` as `customer_b`, FIND-001): a cross-user
  authorization failure turned into a proven path, not just a flag.
- **How a path is proven** — Discovery → Identity → Workflow → Graph
  → Reasoning → Validation → Evidence, with validation reproducing
  each failure a second time before it becomes a finding.

### Assets (all local, `apps/api/static/assets/about/`)

| File | What it is | Size |
|---|---|---|
| `about-hero.svg` | Hero: ghost + network path emblem, GHOSTPATH X — by Adarsh | 960×320 |
| `about-noise-vs-path.svg` | Before/after: noisy scanner output vs one verified path | 960×320 |
| `about-path-chain.svg` | Chain diagram: Identity → Endpoint → Resource → Finding | 960×240 |
| `about-isolated-lab.svg` | Shield lab: isolated lab boundary, lab-only scope | 480×320 |
| `about-path-walk.gif` | Animated verified-path walk, looping | 480×240, loop |
| `radar.gif` (reused, `assets/`) | Animated radar/scan sweep, already used on Live Scans | 480×240, 24 frames, loop |

All references are relative paths — no external URLs, same rule as the
rest of the dashboard.

### Palette & fonts (same theme, repeated for reference)

Base background `#05080F`, panel `#0B1220`, accent cyan `#22D3EE`,
ghost green `#00E5A0`, danger `#FF3B5C`, amber `#FFB020`, text
`#E6EDF3`, muted `#8B9BB4`. Headings/numbers: `"Space Grotesk"`,
body: `"Inter"`, mono: `"JetBrains Mono"` — system fallbacks only,
no webfonts.
