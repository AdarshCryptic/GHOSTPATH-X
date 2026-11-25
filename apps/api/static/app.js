"use strict";

/* GHOSTPATH X v0.4 — dashboard logic.
   All data comes from the FastAPI backend (same origin, /api/v1/...).
   Nothing here is faked: if the API is unreachable, an error banner is
   shown and panels stay empty instead of inventing numbers. */

var API_BASE = "";

var state = {
  labs: [],
  lab: null,
  scan: null,
  scanId: null,
  graph: null,
  paths: [],
  findings: [],
  challenges: [],
  ctfMachines: [],
  ctfSources: [],
  ctfFilters: { source: "", difficulty: "", type: "", q: "" },
  ctfExpanded: {}
};

var AGENT_NAMES = [
  "Discovery Agent",
  "Identity Agent",
  "Workflow Agent",
  "Graph Intelligence",
  "Attack Reasoner",
  "Validation Agent",
  "Evidence Agent"
];

var SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
var SEVERITY_COLORS = {
  critical: "#FF3B5C",
  high: "#FFB020",
  medium: "#FACC15",
  low: "#00E5A0",
  info: "#8B9BB4"
};

/* Local agent icons (apps/api/static/assets/agent-*.svg). The <img> falls
   back to the coloured status dot if an icon file is missing. */
var AGENT_ICONS = {
  "Discovery Agent": "assets/agent-discovery.svg",
  "Identity Agent": "assets/agent-identity.svg",
  "Workflow Agent": "assets/agent-workflow.svg",
  "Graph Intelligence": "assets/agent-graph.svg",
  "Attack Reasoner": "assets/agent-reasoning.svg",
  "Validation Agent": "assets/agent-validation.svg",
  "Evidence Agent": "assets/agent-evidence.svg"
};

function agentIconHtml(name) {
  var src = AGENT_ICONS[name];
  if (!src) return "";
  return '<img class="agent-icon" src="' + src + '" alt="" aria-hidden="true" ' +
    'onerror="this.style.display=\'none\'">';
}

var NODE_COLORS = {
  identity: "#22d3ee",
  endpoint: "#38bdf8",
  resource: "#00e5a0",
  finding: "#ff3b5c",
  role: "#a855f7",
  state: "#facc15",
  permission: "#8b9bb4",
  authorizationboundary: "#ffb020"
};

/* ---------- small helpers ---------- */

function $(id) { return document.getElementById(id); }

function esc(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function showError(message) {
  var banner = $("error-banner");
  banner.innerHTML = "<strong>API error:</strong> " + esc(message);
  banner.classList.remove("hidden");
}

function clearError() {
  var banner = $("error-banner");
  banner.innerHTML = "";
  banner.classList.add("hidden");
}

function setLoading(on, text) {
  var el = $("loading");
  if (text) $("loading-text").textContent = text;
  el.classList.toggle("hidden", !on);
}

function capitalize(word) {
  word = String(word || "");
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/* A count field may arrive as a number or as an array — normalise to a number. */
function countVal(v, fallback) {
  if (typeof v === "number") return v;
  if (Array.isArray(v)) return v.length;
  return fallback;
}

/* Canonical status: complete | running | waiting | failed | stopped | unknown */
function canonicalStatus(raw) {
  var s = String(raw || "").toLowerCase().replace(/[\s-]+/g, "_");
  if (s === "complete" || s === "completed" || s === "done" || s === "success" || s === "finished") return "complete";
  if (s === "active" || s === "running" || s === "in_progress" || s === "inprogress") return "running";
  if (s === "waiting" || s === "pending" || s === "queued" || s === "idle") return "waiting";
  if (s === "failed" || s === "error" || s === "crashed") return "failed";
  if (s === "stopped" || s === "cancelled" || s === "canceled") return "stopped";
  return "unknown";
}

function statusBadgeClass(raw) {
  var c = canonicalStatus(raw);
  if (c === "complete") return "badge-green";
  if (c === "running") return "badge-cyan";
  if (c === "waiting") return "badge-grey";
  if (c === "failed") return "badge-red";
  if (c === "stopped") return "badge-amber";
  return "badge-grey";
}

function statusLabel(raw) {
  var c = canonicalStatus(raw);
  if (c === "complete") return "Complete";
  if (c === "running") return String(raw || "").toLowerCase() === "active" ? "Active" : "Running";
  if (c === "waiting") return "Waiting";
  if (c === "failed") return "Failed";
  if (c === "stopped") return "Stopped";
  return raw ? capitalize(String(raw)) : "Unknown";
}

function severityBadgeClass(sev) {
  switch (String(sev || "").toLowerCase()) {
    case "critical": return "badge-red";
    case "high": return "badge-amber";
    case "medium": return "badge-blue";
    case "low": return "badge-green";
    default: return "badge-grey";
  }
}

function findingStatusBadge(f) {
  var s = String(f.status || "").toLowerCase();
  if (s === "validated") return '<span class="badge badge-green">Validated</span>';
  if (s === "candidate") return '<span class="badge badge-purple">Candidate</span>';
  return '<span class="badge badge-grey">' + esc(f.status || "Unknown") + "</span>";
}

/* Redact secrets from HTTP evidence before display. */
function redactEvidence(value) {
  var text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return text
    .replace(/(authorization:\s*)([^\r\n]+)/gi, "$1[REDACTED]")
    .replace(/(bearer\s+)[A-Za-z0-9._\-~+/=]+/gi, "$1[REDACTED]")
    .replace(/((?:api[_-]?key|token|password|secret)\s*[:=]\s*)("[^"]*"|'[^']*'|[^\s,}\]]+)/gi, "$1[REDACTED]")
    .replace(/(token=)([^\s&"]+)/gi, "$1[REDACTED]");
}

function fnv1a(str) {
  var h = 0x811c9dc5;
  for (var i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return ("0000000" + h.toString(16)).slice(-8);
}

function downloadJson(filename, obj) {
  var blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
  var url = URL.createObjectURL(blob);
  var a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
}

/* ---------- API ---------- */

function apiGet(path) {
  return fetch(API_BASE + path).then(function (res) {
    if (!res.ok) throw new Error("GET " + path + " returned HTTP " + res.status);
    return res.json();
  });
}

function apiPost(path, body) {
  return fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(function (res) {
    return res.json().catch(function () { return {}; }).then(function (data) {
      if (!res.ok) {
        var detail = (data && (data.detail || data.message)) || ("HTTP " + res.status);
        var err = new Error("POST " + path + " returned HTTP " + res.status + ": " + detail);
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    });
  });
}

/* Raw POST that resolves with {ok, status, data} instead of throwing, so
   callers (email writeup, challenge solve) can render server responses. */
function apiPostRaw(path, body) {
  return fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  }).then(function (res) {
    return res.json().catch(function () { return {}; }).then(function (data) {
      return { ok: res.ok, status: res.status, data: data };
    });
  });
}

/* ---------- bootstrap ---------- */

function startScan(labId) {
  return apiPost("/api/v1/scans", {
    lab_id: labId,
    profile: "standard",
    identities: ["customer-a", "customer-b", "admin"],
    modules: ["discovery", "identity", "workflow", "graph", "attack_reasoning", "validation", "evidence"]
  }).then(function (res) {
    state.scanId = res.scan_id || res.id || null;
    state.scan = res;
    return res;
  });
}

function loadScanData() {
  if (!state.scanId) return Promise.resolve();
  var scanP = apiGet("/api/v1/scans/" + encodeURIComponent(state.scanId));
  var graphP = apiGet("/api/v1/scans/" + encodeURIComponent(state.scanId) + "/graph");
  var pathsP = apiGet("/api/v1/scans/" + encodeURIComponent(state.scanId) + "/paths");
  var findingsP = apiGet("/api/v1/findings?scan_id=" + encodeURIComponent(state.scanId));
  return Promise.allSettled([scanP, graphP, pathsP, findingsP]).then(function (results) {
    var failed = [];
    if (results[0].status === "fulfilled") state.scan = results[0].value;
    else failed.push("scan status");
    if (results[1].status === "fulfilled") state.graph = results[1].value;
    else failed.push("attack graph");
    if (results[2].status === "fulfilled") {
      var p = results[2].value;
      state.paths = Array.isArray(p) ? p : (p.paths || []);
    } else failed.push("attack paths");
    if (results[3].status === "fulfilled") {
      var f = results[3].value;
      state.findings = Array.isArray(f) ? f : (f.findings || []);
    } else failed.push("findings");
    if (failed.length) {
      showError("Some data could not be loaded from the API: " + failed.join(", ") + ". Showing what was available.");
    }
  });
}

function bootstrap() {
  setLoading(true, "Connecting to lab and starting scan…");
  apiGet("/api/v1/labs")
    .then(function (labs) {
      state.labs = Array.isArray(labs) ? labs : (labs.labs || []);
      if (!state.labs.length) {
        return apiPost("/api/v1/labs", {
          name: "Juice Shop Training Lab",
          base_url: "http://127.0.0.1:8000/lab",
          environment: "isolated_docker"
        }).then(function (lab) {
          state.labs = [lab];
          return lab;
        });
      }
      return state.labs[0];
    })
    .then(function (lab) {
      state.lab = lab;
      renderLabSelector();
      return startScan(lab.id);
    })
    .then(function () { return loadScanData(); })
    .then(function () {
      renderAll();
      clearError();
    })
    .catch(function (err) {
      showError("Could not reach the API (" + err.message + "). Check that the FastAPI backend is running on 127.0.0.1:8000.");
      renderAll();
    })
    .then(function () {
      setLoading(false);
      /* CTF Machines data loads in the background too, so the sidebar
         badge shows the machine count without waiting for a visit.
         Both loaders handle their own errors; a missing endpoint must
         never break the dashboard bootstrap. */
      loadCtfSources();
      loadCtfMachines();
    });
}

/* ---------- navigation ---------- */

var PAGES = ["overview", "about", "owner", "labs", "scans", "graph", "findings", "challenges", "ctf", "evidence", "agents", "settings"];

function showPage(name) {
  PAGES.forEach(function (p) {
    var section = $("page-" + p);
    if (section) section.classList.toggle("hidden", p !== name);
  });
  document.querySelectorAll(".nav-item").forEach(function (btn) {
    btn.classList.toggle("active", btn.getAttribute("data-nav") === name);
  });
  if (name === "challenges") {
    renderChallenges();
  }
  if (name === "owner") {
    refreshOwnerPage();
  }
  if (name === "ctf") {
    loadCtfSources();
    loadCtfMachines();
  }
  if (name === "graph") {
    // Canvas has zero size while hidden; size and redraw once visible.
    requestAnimationFrame(function () {
      resizeGraphCanvas();
      fitGraphView();
      drawGraph();
    });
  }
}

/* ---------- rendering: overview ---------- */

function agentDisplayName(raw) {
  var r = String(raw || "").trim();
  if (!r) return "Unknown Agent";
  var lower = r.toLowerCase();
  for (var i = 0; i < AGENT_NAMES.length; i++) {
    var canon = AGENT_NAMES[i];
    var first = canon.split(" ")[0].toLowerCase();
    if (canon.toLowerCase() === lower || canon.toLowerCase().indexOf(lower) !== -1 || lower.indexOf(first) !== -1) {
      return canon;
    }
  }
  return capitalize(r);
}

/* The API may report agents as objects {name, status} or as plain strings
   such as "Discovery Complete" — accept both. */
function parseAgentEntry(a) {
  if (typeof a === "string") {
    var m = a.match(/^(.*?)[\s\-]+(complete|completed|running|active|waiting|pending|failed|stopped|done)$/i);
    if (m) return { name: agentDisplayName(m[1].trim()), status: m[2].toLowerCase() };
    return { name: agentDisplayName(a), status: "unknown" };
  }
  return { name: agentDisplayName(a.name), status: a.status || "unknown" };
}

function agentStatusList() {
  var raw = state.scan && Array.isArray(state.scan.agent_status) ? state.scan.agent_status : [];
  if (!raw.length) {
    return AGENT_NAMES.map(function (n) { return { name: n, status: "waiting" }; });
  }
  var mapped = raw.map(parseAgentEntry);
  // Keep the canonical 7 first; append any extra agents the API reports.
  var seen = {};
  var out = [];
  AGENT_NAMES.forEach(function (canon) {
    var hit = mapped.find(function (m) { return m.name === canon; });
    if (hit) { out.push(hit); seen[canon] = true; }
  });
  mapped.forEach(function (m) { if (!seen[m.name]) out.push(m); });
  AGENT_NAMES.forEach(function (canon) {
    if (!out.some(function (m) { return m.name === canon; })) out.push({ name: canon, status: "waiting" });
  });
  return out;
}

function renderOverview() {
  var scan = state.scan || {};
  var endpoints = countVal(scan.endpoints_discovered, undefined);
  var identities = countVal(scan.identities_mapped, undefined);
  var paths = countVal(scan.attack_paths, undefined);
  var findings = countVal(scan.validated_findings, undefined);

  if (paths === undefined && state.paths.length) paths = state.paths.length;
  if (findings === undefined && state.findings.length) {
    findings = state.findings.filter(function (f) {
      return String(f.status || "").toLowerCase() === "validated";
    }).length;
  }

  $("stat-endpoints").textContent = endpoints === undefined ? "—" : endpoints;
  $("stat-identities").textContent = identities === undefined ? "—" : identities;
  $("stat-paths").textContent = paths === undefined ? "—" : paths;
  $("stat-findings").textContent = findings === undefined ? "—" : findings;

  var progress = typeof scan.progress === "number" ? scan.progress : (scan.status === "completed" ? 100 : 0);
  progress = Math.max(0, Math.min(100, progress));
  $("scan-progress-fill").style.width = progress + "%";
  $("scan-progress-pct").textContent = progress + "%";
  $("scan-progress-track").setAttribute("aria-valuenow", String(progress));
  $("scan-phase").textContent = scan.phase || scan.status || "—";
  $("scan-id-label").textContent = state.scanId ? "Scan " + state.scanId : "";

  var statusText = scan.status ? capitalize(String(scan.status)) : "Idle";
  $("scan-status-text").textContent = statusText;
  var pill = $("scan-status-pill");
  pill.className = "badge " + (canonicalStatus(scan.status) === "complete" ? "badge-green" : canonicalStatus(scan.status) === "running" ? "badge-cyan" : canonicalStatus(scan.status) === "failed" ? "badge-red" : "badge-grey");
  var dot = pill.querySelector(".dot");
  if (dot) dot.className = "dot " + (canonicalStatus(scan.status) === "complete" ? "dot-green" : canonicalStatus(scan.status) === "running" ? "dot-cyan dot-pulse" : canonicalStatus(scan.status) === "failed" ? "dot-red" : "");

  renderTimeline();
}

var TIMELINE_STEPS = [
  { key: "discovery", match: /discovery/i },
  { key: "identity", match: /identity/i },
  { key: "workflow", match: /workflow/i },
  { key: "paths", match: /attack reasoner|graph intelligence/i },
  { key: "validation", match: /validation/i }
];

function renderTimeline() {
  var agents = agentStatusList();
  var scan = state.scan || {};
  var progress = typeof scan.progress === "number" ? scan.progress : (scan.status === "completed" ? 100 : 0);
  TIMELINE_STEPS.forEach(function (step, idx) {
    var li = document.querySelector('#scan-timeline li[data-step="' + step.key + '"]');
    if (!li) return;
    var stateEl = li.querySelector(".step-state");
    var agent = agents.find(function (a) { return step.match.test(a.name); });
    var cls = "waiting";
    var label = "Waiting";
    if (agent) {
      var c = canonicalStatus(agent.status);
      if (c === "complete") { cls = "done"; label = "Completed"; }
      else if (c === "running") { cls = "active"; label = "Running"; }
      else if (c === "failed") { cls = ""; label = "Failed"; }
    } else if (scan.agent_status === undefined || !scan.agent_status.length) {
      // Fallback when the API reports no per-agent status: derive from progress.
      var doneAt = (idx + 1) * 20;
      if (progress >= doneAt) { cls = "done"; label = "Completed"; }
      else if (progress >= idx * 20) { cls = "active"; label = "Running"; }
    }
    li.classList.remove("done", "active");
    if (cls) li.classList.add(cls);
    stateEl.textContent = label;
  });
}

function renderAgents() {
  var agents = agentStatusList();
  var html = agents.map(function (a) {
    return "<li>" + agentIconHtml(a.name) +
      '<span class="dot ' + (canonicalStatus(a.status) === "complete" ? "dot-green" : canonicalStatus(a.status) === "running" ? "dot-cyan dot-pulse live-dot" : canonicalStatus(a.status) === "failed" ? "dot-red" : "") + '"></span>' +
      '<span class="agent-name">' + esc(a.name) + '</span>' +
      '<span class="badge ' + statusBadgeClass(a.status) + '">' + esc(statusLabel(a.status)) + "</span></li>";
  }).join("");
  $("agent-list").innerHTML = html;
  $("agent-runs-list").innerHTML = html;
  $("agent-runs-updated").textContent = "Last updated " + new Date().toLocaleTimeString();
}

function renderDonut() {
  var counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  state.findings.forEach(function (f) {
    var s = String(f.severity || "info").toLowerCase();
    if (!(s in counts)) s = "info";
    counts[s]++;
  });
  var total = Object.keys(counts).reduce(function (sum, k) { return sum + counts[k]; }, 0);
  $("donut-total").textContent = total;
  $("sev-critical").textContent = counts.critical;
  $("sev-high").textContent = counts.high;
  $("sev-medium").textContent = counts.medium;
  $("sev-low").textContent = counts.low;
  $("sev-info").textContent = counts.info;

  var donut = $("severity-donut");
  if (!total) {
    donut.style.background = "conic-gradient(rgba(34,211,238,0.12) 0 100%)";
    return;
  }
  var parts = [];
  var acc = 0;
  ["critical", "high", "medium", "low", "info"].forEach(function (sev) {
    var frac = (counts[sev] / total) * 100;
    if (frac > 0) {
      parts.push(SEVERITY_COLORS[sev] + " " + acc.toFixed(2) + "% " + (acc + frac).toFixed(2) + "%");
      acc += frac;
    }
  });
  donut.style.background = "conic-gradient(" + parts.join(", ") + ")";
}

function renderRecentFindings() {
  var list = $("recent-findings");
  if (!state.findings.length) {
    list.innerHTML = '<li><span class="finding-title muted">No findings yet for this scan.</span></li>';
    return;
  }
  var sorted = state.findings.slice().sort(function (a, b) {
    var ra = SEVERITY_ORDER[String(a.severity || "info").toLowerCase()];
    var rb = SEVERITY_ORDER[String(b.severity || "info").toLowerCase()];
    return (ra === undefined ? 4 : ra) - (rb === undefined ? 4 : rb);
  });
  list.innerHTML = sorted.slice(0, 5).map(function (f) {
    return '<li data-finding-id="' + esc(f.id || "") + '">' +
      '<span class="finding-title">' + esc(f.title || f.id || "Untitled finding") + "</span>" +
      '<span class="badge ' + severityBadgeClass(f.severity) + '">' + esc(f.severity || "Info") + "</span>" +
      findingStatusBadge(f) + "</li>";
  }).join("");
  list.querySelectorAll("li[data-finding-id]").forEach(function (li) {
    li.addEventListener("click", function () {
      showPage("findings");
      expandFinding(li.getAttribute("data-finding-id"));
    });
  });
}

/* ---------- rendering: findings ---------- */

function reproductionHtml(f) {
  var r = f.reproduction;
  if (!r) return "<p class=\"muted\">No reproduction steps provided.</p>";
  if (Array.isArray(r)) {
    return "<ol>" + r.map(function (s) { return "<li>" + esc(typeof s === "string" ? s : JSON.stringify(s)) + "</li>"; }).join("") + "</ol>";
  }
  return "<pre class=\"evidence\">" + esc(String(r)) + "</pre>";
}

function findingSummary(f) {
  return f.summary || f.description || f.observed || "—";
}

function findingCategory(f) {
  return f.category || f.invariant_id || f.endpoint || "—";
}

/* Prefer the backend's own evidence hash (SHA-256) when present. */
function findingEvidenceHash(f) {
  if (f.evidence && typeof f.evidence === "object" && f.evidence.hash) {
    return { hash: String(f.evidence.hash), label: "Evidence hash (SHA-256)" };
  }
  return { hash: fnv1a(JSON.stringify(f)), label: "Evidence hash (FNV-1a)" };
}

function findingDetailHtml(f) {
  var meta = [];
  if (f.endpoint) meta.push("<dt>Endpoint</dt><dd class=\"mono\">" + esc(f.endpoint) + "</dd>");
  if (f.identity) meta.push("<dt>Identity</dt><dd>" + esc(f.identity) + "</dd>");
  if (f.invariant_id) meta.push("<dt>Invariant</dt><dd class=\"mono\">" + esc(f.invariant_id) + "</dd>");
  if (f.expected) meta.push("<dt>Expected</dt><dd>" + esc(f.expected) + "</dd>");
  if (f.observed) meta.push("<dt>Observed</dt><dd>" + esc(f.observed) + "</dd>");
  var metaHtml = meta.length ? '<div class="detail-block"><h4>Details</h4><dl class="kv">' + meta.join("") + "</dl></div>" : "";
  return '<div class="detail-block"><h4>Summary</h4><p>' + esc(findingSummary(f)) + "</p></div>" +
    metaHtml +
    '<div class="detail-block"><h4>Reproduction steps</h4>' + reproductionHtml(f) + "</div>" +
    '<div class="detail-block"><h4>HTTP evidence (redacted)</h4><pre class="evidence">' + esc(redactEvidence(f.evidence || "No evidence attached.")) + "</pre></div>" +
    '<div class="detail-block"><h4>Remediation</h4><p>' + esc(f.remediation || "—") + "</p></div>" +
    '<button type="button" class="dl-btn" data-finding-id="' + esc(f.id || "") + '">Download evidence JSON</button>';
}

function renderFindingsTable() {
  var tbody = $("findings-tbody");
  $("findings-count").textContent = state.findings.length + (state.findings.length === 1 ? " finding" : " findings");
  if (!state.findings.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted">No findings for this scan.</td></tr>';
    return;
  }
  tbody.innerHTML = state.findings.map(function (f) {
    var id = f.id || "";
    return '<tr class="row-click" data-finding-id="' + esc(id) + '">' +
      "<td class=\"mono\">" + esc(id) + "</td>" +
      "<td>" + esc(f.title || "—") + "</td>" +
      '<td><span class="badge ' + severityBadgeClass(f.severity) + '">' + esc(f.severity || "Info") + "</span></td>" +
      "<td>" + findingStatusBadge(f) + "</td>" +
      "<td>" + esc(findingCategory(f)) + "</td>" +
      "<td>" + esc(findingSummary(f)) + "</td></tr>" +
      '<tr class="detail-row hidden" data-detail-for="' + esc(id) + '"><td colspan="6">' + findingDetailHtml(f) + "</td></tr>";
  }).join("");
}

function expandFinding(id) {
  var row = document.querySelector('#findings-tbody tr[data-detail-for="' + id + '"]');
  if (row) {
    row.classList.remove("hidden");
    row.scrollIntoView({ block: "nearest" });
  }
}

/* ---------- rendering: evidence & reports ---------- */

function renderEvidence() {
  var list = $("evidence-list");
  if (!state.findings.length) {
    list.innerHTML = '<p class="empty">No evidence yet for this scan.</p>';
  } else {
    list.innerHTML = state.findings.map(function (f) {
      var h = findingEvidenceHash(f);
      var preview = redactEvidence(f.evidence || "No evidence attached.");
      if (preview.length > 600) preview = preview.slice(0, 600) + "…";
      return '<div class="evidence-item"><div class="row">' +
        '<span class="grow"><strong>' + esc(f.id || "") + "</strong> — " + esc(f.title || "Untitled finding") + "</span>" +
        '<span class="badge ' + severityBadgeClass(f.severity) + '">' + esc(f.severity || "Info") + "</span>" +
        findingStatusBadge(f) + "</div>" +
        '<pre class="evidence" style="margin-top:10px">' + esc(preview) + "</pre>" +
        '<div class="row" style="margin-top:10px"><span class="hash">' + esc(h.label) + ': <span class="mono">' + esc(h.hash) + '</span></span>' +
        '<span style="flex:1"></span>' +
        '<button type="button" class="dl-btn" data-finding-id="' + esc(f.id || "") + '">Download evidence JSON</button></div></div>';
    }).join("");
  }

  var scanLabel = $("report-scan-label");
  var reportId = (state.scan && state.scan.report_id) || state.scanId;
  if (reportId) {
    scanLabel.textContent = "Report for scan " + (state.scanId || "") + " (lab: " + (state.lab ? state.lab.name : "—") + ", report " + reportId + ").";
    $("report-json-link").href = "/api/v1/reports/" + encodeURIComponent(reportId);
  } else {
    scanLabel.textContent = "No scan loaded yet.";
    $("report-json-link").href = "#";
  }
}

/* ---------- rendering: labs / live scans / settings ---------- */

function renderLabSelector() {
  var sel = $("lab-selector");
  sel.innerHTML = state.labs.map(function (lab) {
    return '<option value="' + esc(lab.id) + '"' + (state.lab && lab.id === state.lab.id ? " selected" : "") + ">" + esc(lab.name || lab.id) + "</option>";
  }).join("");
}

function renderLabs() {
  var list = $("labs-list");
  if (!state.labs.length) {
    list.innerHTML = '<li><span class="agent-name">No labs registered.</span></li>';
    return;
  }
  list.innerHTML = state.labs.map(function (lab) {
    var active = state.lab && lab.id === state.lab.id;
    return "<li>" +
      '<span class="dot ' + (active ? "dot-green" : "") + '"></span>' +
      '<span class="agent-name">' + esc(lab.name || lab.id) + ' <span class="agent-kind">' + esc(lab.base_url || "") + " · " + esc(lab.environment || lab.status || "") + "</span></span>" +
      (active ? '<span class="badge badge-green">Active</span>' : '<button type="button" class="use-lab-btn" data-lab-id="' + esc(lab.id) + '">Use this lab</button>') +
      "</li>";
  }).join("");
  list.querySelectorAll(".use-lab-btn").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var lab = state.labs.find(function (l) { return String(l.id) === btn.getAttribute("data-lab-id"); });
      if (!lab) return;
      state.lab = lab;
      renderLabSelector();
      setLoading(true, "Starting scan on " + lab.name + "…");
      startScan(lab.id)
        .then(loadScanData)
        .then(function () { renderAll(); clearError(); })
        .catch(function (err) { showError("Scan failed: " + err.message); })
        .then(function () { setLoading(false); });
    });
  });
}

function renderLiveScan() {
  var scan = state.scan || {};
  var progress = typeof scan.progress === "number" ? scan.progress : (scan.status === "completed" ? 100 : 0);
  progress = Math.max(0, Math.min(100, progress));
  $("live-scan-progress-fill").style.width = progress + "%";
  $("live-scan-progress-pct").textContent = progress + "%";
  $("live-scan-title").textContent = state.lab ? "Current scan — " + state.lab.name : "Current scan";
  $("live-scan-id").textContent = state.scanId ? "Scan " + state.scanId : "";
  $("live-scan-status").textContent = scan.status ? capitalize(String(scan.status)) : "—";
  $("live-scan-phase").textContent = scan.phase || scan.status || "—";
  $("live-scan-endpoints").textContent = countVal(scan.endpoints_discovered, undefined) === undefined ? "—" : countVal(scan.endpoints_discovered, undefined);
  $("live-scan-identities").textContent = countVal(scan.identities_mapped, undefined) === undefined ? "—" : countVal(scan.identities_mapped, undefined);
  $("live-scan-paths").textContent = countVal(scan.attack_paths, state.paths.length);
  $("live-scan-findings").textContent = countVal(scan.validated_findings, undefined) === undefined ? "—" : countVal(scan.validated_findings, undefined);
  $("stop-scan-btn").disabled = !state.scanId || canonicalStatus(scan.status) === "complete" || canonicalStatus(scan.status) === "stopped";
  /* Radar sweep is visible only while a scan is actually running. */
  var radar = $("radar-wrap");
  if (radar) radar.classList.toggle("hidden", canonicalStatus(scan.status) !== "running");
}

function renderAll() {
  renderOverview();
  renderAgents();
  renderDonut();
  renderRecentFindings();
  renderFindingsTable();
  renderEvidence();
  renderLabs();
  renderLiveScan();
  applyGraphFilters();
  $("settings-api-base").textContent = window.location.origin + " (same origin)";
}

/* ---------- attack graph (canvas) ---------- */

var graphView = {
  nodes: [],
  edges: [],
  pos: new Map(),
  scale: 1,
  ox: 0,
  oy: 0,
  selected: null,
  hover: null,
  dragNode: null,
  panning: false,
  downX: 0,
  downY: 0,
  moved: false,
  maxNodes: 500,
  domain: "juice.bugbase.ai",
  search: "",
  domainNote: ""
};

function nodeColor(type) {
  return NODE_COLORS[String(type || "").toLowerCase()] || "#64748b";
}

function applyGraphFilters() {
  var raw = state.graph;
  graphView.pos.clear();
  graphView.selected = null;
  if (!raw || !Array.isArray(raw.nodes)) {
    graphView.nodes = [];
    graphView.edges = [];
    renderGraphDetails();
    updateGraphCounts();
    drawGraph();
    return;
  }
  var nodes = raw.nodes.slice();
  graphView.domainNote = "";
  if (graphView.domain !== "all") {
    var filtered = nodes.filter(function (n) {
      return ((n.label || "") + " " + (n.id || "")).toLowerCase().indexOf(graphView.domain) !== -1;
    });
    if (filtered.length) nodes = filtered;
    else graphView.domainNote = "No nodes carry the domain label — showing all nodes.";
  }
  nodes = nodes.slice(0, graphView.maxNodes);
  var ids = {};
  nodes.forEach(function (n) { ids[n.id] = true; });
  var edges = (Array.isArray(raw.edges) ? raw.edges : []).filter(function (e) {
    return ids[e.source] && ids[e.target];
  });
  graphView.nodes = nodes;
  graphView.edges = edges;
  nodes.forEach(function (n, i) {
    if (!graphView.pos.has(n.id)) {
      var angle = i * 2.399963;
      var r = 50 + 62 * Math.sqrt(i);
      graphView.pos.set(n.id, { x: r * Math.cos(angle), y: r * Math.sin(angle) });
    }
  });
  renderGraphDetails();
  updateGraphCounts();
  if (!$("page-graph").classList.contains("hidden")) {
    resizeGraphCanvas();
    fitGraphView();
    drawGraph();
  }
}

function updateGraphCounts() {
  var totalNodes = state.graph ? (state.graph.node_count || (state.graph.nodes || []).length) : 0;
  var totalEdges = state.graph ? (state.graph.edge_count || (state.graph.edges || []).length) : 0;
  var text = graphView.nodes.length + " nodes | " + graphView.edges.length + " edges";
  if (totalNodes && (totalNodes !== graphView.nodes.length || totalEdges !== graphView.edges.length)) {
    text += "  (full graph: " + totalNodes + " nodes | " + totalEdges + " edges)";
  }
  if (graphView.domainNote) text += " — " + graphView.domainNote;
  $("graph-counts").textContent = text;
}

function graphCanvas() { return $("graph-canvas"); }

function resizeGraphCanvas() {
  var canvas = graphCanvas();
  var wrap = canvas.parentElement;
  var dpr = window.devicePixelRatio || 1;
  var w = wrap.clientWidth;
  var h = 520;
  if (!w) return;
  canvas.width = Math.round(w * dpr);
  canvas.height = Math.round(h * dpr);
  canvas.style.height = h + "px";
  var ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function canvasSize() {
  var canvas = graphCanvas();
  return { w: canvas.clientWidth || canvas.parentElement.clientWidth, h: 520 };
}

function worldFromEvent(e) {
  var rect = graphCanvas().getBoundingClientRect();
  return {
    x: (e.clientX - rect.left - graphView.ox) / graphView.scale,
    y: (e.clientY - rect.top - graphView.oy) / graphView.scale
  };
}

function hitNode(world) {
  var best = null;
  var bestD = Infinity;
  graphView.nodes.forEach(function (n) {
    var p = graphView.pos.get(n.id);
    if (!p) return;
    var d = Math.hypot(p.x - world.x, p.y - world.y);
    if (d < 16 / graphView.scale + 6 && d < bestD) { best = n; bestD = d; }
  });
  return best;
}

function neighboursOf(id) {
  var out = [];
  graphView.edges.forEach(function (e) {
    if (e.source === id) out.push(e.target);
    else if (e.target === id) out.push(e.source);
  });
  return out;
}

function drawGraph() {
  var canvas = graphCanvas();
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;
  var size = canvasSize();
  var dpr = window.devicePixelRatio || 1;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size.w, size.h);

  if (!graphView.nodes.length) {
    var empty = $("graph-empty");
    if (empty) empty.classList.remove("hidden");
    ctx.fillStyle = "#8B9BB4";
    ctx.font = "14px -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("No graph data yet — run a scan first.", size.w / 2, size.h / 2);
    return;
  }
  var emptyEl = $("graph-empty");
  if (emptyEl) emptyEl.classList.add("hidden");

  var toScreen = function (p) {
    return { x: p.x * graphView.scale + graphView.ox, y: p.y * graphView.scale + graphView.oy };
  };
  var selectedNeighbours = graphView.selected ? neighboursOf(graphView.selected) : [];

  // Edges
  graphView.edges.forEach(function (e) {
    var a = graphView.pos.get(e.source);
    var b = graphView.pos.get(e.target);
    if (!a || !b) return;
    var pa = toScreen(a);
    var pb = toScreen(b);
    var highlighted = graphView.selected &&
      (e.source === graphView.selected || e.target === graphView.selected ||
        selectedNeighbours.indexOf(e.source) !== -1 && selectedNeighbours.indexOf(e.target) !== -1);
    ctx.beginPath();
    ctx.moveTo(pa.x, pa.y);
    ctx.lineTo(pb.x, pb.y);
    ctx.strokeStyle = highlighted ? "#00E5A0" : "rgba(34,211,238,0.25)";
    ctx.lineWidth = highlighted ? 2 : 1;
    ctx.stroke();
  });

  // Nodes
  var showLabels = graphView.nodes.length <= 80;
  graphView.nodes.forEach(function (n) {
    var p = graphView.pos.get(n.id);
    if (!p) return;
    var s = toScreen(p);
    var r = Math.max(5, 9 * graphView.scale);
    var isSelected = graphView.selected === n.id;
    var isMatch = graphView.search && ((n.label || "") + " " + (n.id || "")).toLowerCase().indexOf(graphView.search) !== -1;

    if (isSelected) {
      ctx.beginPath();
      ctx.arc(s.x, s.y, r + 5, 0, Math.PI * 2);
      ctx.strokeStyle = "#22d3ee";
      ctx.lineWidth = 2;
      ctx.stroke();
    } else if (isMatch) {
      ctx.beginPath();
      ctx.arc(s.x, s.y, r + 4, 0, Math.PI * 2);
      ctx.strokeStyle = "#FFB020";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.arc(s.x, s.y, r, 0, Math.PI * 2);
    ctx.fillStyle = nodeColor(n.type);
    ctx.fill();
    ctx.strokeStyle = "#05080F";
    ctx.lineWidth = 1.5;
    ctx.stroke();

    if (showLabels || isSelected || graphView.hover === n.id) {
      ctx.font = "11px -apple-system, sans-serif";
      ctx.fillStyle = "#e2e8f0";
      ctx.textAlign = "left";
      ctx.fillText(n.label || n.id, s.x + r + 5, s.y + 4);
    }
  });
}

function fitGraphView() {
  var size = canvasSize();
  if (!graphView.nodes.length) {
    graphView.scale = 1;
    graphView.ox = size.w / 2;
    graphView.oy = size.h / 2;
    return;
  }
  var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  graphView.nodes.forEach(function (n) {
    var p = graphView.pos.get(n.id);
    if (!p) return;
    minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
    minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
  });
  var bw = Math.max(60, maxX - minX);
  var bh = Math.max(60, maxY - minY);
  var scale = Math.min(size.w / (bw + 100), size.h / (bh + 100), 1.6);
  scale = Math.max(0.2, scale);
  graphView.scale = scale;
  graphView.ox = size.w / 2 - ((minX + maxX) / 2) * scale;
  graphView.oy = size.h / 2 - ((minY + maxY) / 2) * scale;
}

function zoomGraph(factor, cx, cy) {
  var size = canvasSize();
  var mx = cx === undefined ? size.w / 2 : cx;
  var my = cy === undefined ? size.h / 2 : cy;
  var newScale = Math.max(0.2, Math.min(4, graphView.scale * factor));
  var k = newScale / graphView.scale;
  graphView.ox = mx - (mx - graphView.ox) * k;
  graphView.oy = my - (my - graphView.oy) * k;
  graphView.scale = newScale;
  drawGraph();
}

function selectGraphNode(id) {
  graphView.selected = id;
  renderGraphDetails();
  drawGraph();
}

function renderGraphDetails() {
  var panel = $("graph-details");
  var node = graphView.nodes.find(function (n) { return n.id === graphView.selected; });
  if (!node) {
    panel.innerHTML = "<h3>Node details</h3><p class=\"muted\">Click a node in the graph to inspect it. Drag nodes to rearrange, scroll to zoom.</p>";
    return;
  }
  var nb = neighboursOf(node.id);
  var nbHtml = nb.length
    ? '<ul class="neighbour-list">' + nb.map(function (id) {
        var n = graphView.nodes.find(function (x) { return x.id === id; });
        return '<li><button type="button" data-neighbour-id="' + esc(id) + '">' + esc((n && n.label) || id) + "</button></li>";
      }).join("") + "</ul>"
    : '<p class="muted">No neighbours in the current view.</p>';
  panel.innerHTML = "<h3>Node details</h3>" +
    "<dl><dt>Label</dt><dd>" + esc(node.label || node.id) + "</dd>" +
    "<dt>Type</dt><dd>" + esc(node.type || "—") + "</dd>" +
    "<dt>ID</dt><dd class=\"mono\">" + esc(node.id) + "</dd>" +
    "<dt>Connections</dt><dd>" + nb.length + "</dd></dl>" +
    "<h3 style=\"margin-top:16px\">Neighbours</h3>" + nbHtml;
  panel.querySelectorAll("[data-neighbour-id]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      selectGraphNode(btn.getAttribute("data-neighbour-id"));
    });
  });
}

function wireGraphEvents() {
  var canvas = graphCanvas();

  canvas.addEventListener("mousedown", function (e) {
    if (e.button !== 0) return;
    var world = worldFromEvent(e);
    var node = hitNode(world);
    graphView.downX = e.clientX;
    graphView.downY = e.clientY;
    graphView.moved = false;
    if (node) {
      graphView.dragNode = node.id;
    } else {
      graphView.panning = true;
      graphView.lastPanX = e.clientX;
      graphView.lastPanY = e.clientY;
    }
  });

  canvas.addEventListener("mousemove", function (e) {
    if (Math.abs(e.clientX - graphView.downX) > 4 || Math.abs(e.clientY - graphView.downY) > 4) {
      graphView.moved = true;
    }
    if (graphView.dragNode) {
      var world = worldFromEvent(e);
      graphView.pos.set(graphView.dragNode, { x: world.x, y: world.y });
      drawGraph();
    } else if (graphView.panning) {
      graphView.ox += e.clientX - graphView.lastPanX;
      graphView.oy += e.clientY - graphView.lastPanY;
      graphView.lastPanX = e.clientX;
      graphView.lastPanY = e.clientY;
      drawGraph();
    } else {
      var node = hitNode(worldFromEvent(e));
      var id = node ? node.id : null;
      if (id !== graphView.hover) {
        graphView.hover = id;
        canvas.style.cursor = id ? "pointer" : "grab";
        drawGraph();
      }
    }
  });

  canvas.addEventListener("mouseup", function (e) {
    if (graphView.dragNode && !graphView.moved) {
      selectGraphNode(graphView.dragNode);
    } else if (graphView.panning && !graphView.moved) {
      selectGraphNode(null);
    }
    graphView.dragNode = null;
    graphView.panning = false;
  });

  canvas.addEventListener("mouseleave", function () {
    graphView.dragNode = null;
    graphView.panning = false;
    graphView.hover = null;
    drawGraph();
  });

  canvas.addEventListener("contextmenu", function (e) {
    e.preventDefault();
    var node = hitNode(worldFromEvent(e));
    if (node) selectGraphNode(node.id);
  });

  canvas.addEventListener("wheel", function (e) {
    e.preventDefault();
    var rect = canvas.getBoundingClientRect();
    zoomGraph(e.deltaY < 0 ? 1.12 : 0.89, e.clientX - rect.left, e.clientY - rect.top);
  }, { passive: false });

  $("graph-max-nodes").addEventListener("input", function (e) {
    graphView.maxNodes = parseInt(e.target.value, 10);
    $("graph-max-nodes-value").textContent = e.target.value;
    applyGraphFilters();
  });

  $("graph-domain").addEventListener("change", function (e) {
    graphView.domain = e.target.value;
    applyGraphFilters();
  });

  $("graph-search").addEventListener("input", function (e) {
    graphView.search = e.target.value.trim().toLowerCase();
    drawGraph();
  });

  $("graph-search").addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    var match = graphView.nodes.find(function (n) {
      return ((n.label || "") + " " + (n.id || "")).toLowerCase().indexOf(graphView.search) !== -1;
    });
    if (match) selectGraphNode(match.id);
  });

  $("graph-zoom-in").addEventListener("click", function () { zoomGraph(1.25); });
  $("graph-zoom-out").addEventListener("click", function () { zoomGraph(0.8); });
  $("graph-reset-view").addEventListener("click", function () { fitGraphView(); drawGraph(); });

  window.addEventListener("resize", function () {
    if ($("page-graph").classList.contains("hidden")) return;
    resizeGraphCanvas();
    drawGraph();
  });
}

/* ---------- challenges ---------- */

/* Challenges backend (GET /api/v1/challenges, …/brief, …/solve, …/writeup)
   is built by another agent. Everything here is defensive: a 404 or any
   other failure shows plain error text instead of breaking the dashboard. */

function difficultyBadgeClass(difficulty) {
  switch (String(difficulty || "").toLowerCase()) {
    case "easy": return "badge-green";
    case "medium": return "badge-amber";
    case "hard": return "badge-red";
    default: return "badge-grey";
  }
}

function challengeList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.challenges)) return data.challenges;
  return [];
}

function loadChallenges() {
  var grid = $("challenges-grid");
  var status = $("challenges-status");
  if (grid && !state.challenges.length) {
    grid.innerHTML = '<p class="muted">Loading challenges…</p>';
  }
  if (status) status.textContent = "";
  return apiGet("/api/v1/challenges").then(function (data) {
    state.challenges = challengeList(data);
    renderChallenges();
  }).catch(function (err) {
    state.challenges = [];
    if (grid) {
      grid.innerHTML = '<p class="muted">Challenges are not available yet — the challenges API returned an error (' +
        esc(err.message) + '). The backend for this screen is still being built; the rest of the dashboard is unaffected.</p>';
    }
    if (status) status.textContent = "Could not load challenges: " + err.message;
  });
}

function challengeCardHtml(c) {
  var id = c.id || "";
  var hints = Array.isArray(c.hints) ? c.hints : [];
  var learn = "";
  if (c.lesson || c.remediation || c.graph_path) {
    learn = '<div class="challenge-learn"><strong>Learn</strong><br>' +
      (c.lesson ? "Lesson: " + esc(c.lesson) + "<br>" : "") +
      (c.remediation ? "Remediation: " + esc(c.remediation) + "<br>" : "") +
      (c.graph_path ? "Graph path: <span class=\"mono\">" + esc(typeof c.graph_path === "string" ? c.graph_path : JSON.stringify(c.graph_path)) + "</span>" : "") +
      "</div>";
  }
  return '<article class="challenge-card" data-challenge-id="' + esc(id) + '">' +
    '<div class="challenge-head"><div><h3>' + esc(c.title || id || "Untitled challenge") + '</h3>' +
    '<span class="challenge-id">' + esc(id) + '</span></div>' +
    '<span class="badge ' + difficultyBadgeClass(c.difficulty) + '">' + esc(c.difficulty || "—") + "</span></div>" +
    (c.category ? '<span class="badge badge-cyan">' + esc(c.category) + "</span>" : "") +
    (c.story ? '<p class="challenge-story">' + esc(c.story) + "</p>" : "") +
    (c.objective ? '<p class="challenge-objective"><strong>Objective:</strong> ' + esc(c.objective) + "</p>" : "") +
    '<div class="challenge-links"><a class="button-link" href="/api/v1/challenges/' + encodeURIComponent(id) + '/brief" download>Download brief</a></div>' +
    (hints.length ?
      '<div class="challenge-hints">' +
      hints.map(function (_h, i) {
        return '<button type="button" data-hint-index="' + i + '">Hint ' + (i + 1) + "</button>";
      }).join("") + "</div>" +
      '<div class="challenge-hint-area" data-hint-area></div>' : "") +
    '<form class="challenge-solve" data-solve-form>' +
    '<label>Identity<select data-solve-identity>' +
    '<option value="customer_a">customer_a</option>' +
    '<option value="customer_b">customer_b</option>' +
    '<option value="administrator">administrator</option>' +
    "</select></label>" +
    '<label>Method<input type="text" data-solve-method placeholder="GET" autocomplete="off"></label>' +
    '<label>Path<input type="text" data-solve-path placeholder="/api/orders/1001" autocomplete="off"></label>' +
    '<button type="submit" class="primary">Solve</button></form>' +
    '<p class="challenge-result" data-solve-result role="status"></p>' +
    learn +
    '<div class="challenge-links"><label>Writeup format <select data-writeup-format>' +
    '<option value="docx">Word (.docx)</option><option value="pdf">PDF</option><option value="both">Both</option>' +
    "</select></label>" +
    '<button type="button" class="primary" data-writeup-btn>Generate writeup</button></div>' +
    '<p class="challenge-result" data-writeup-result role="status"></p>' +
    "</article>";
}

function renderChallenges() {
  var grid = $("challenges-grid");
  if (!grid) return;
  if (!state.challenges.length) {
    grid.innerHTML = '<p class="muted">No challenges available for this lab yet.</p>';
    return;
  }
  grid.innerHTML = state.challenges.map(challengeCardHtml).join("");
  wireChallengeCards(grid);
}

function wireChallengeCards(grid) {
  grid.querySelectorAll(".challenge-card").forEach(function (card) {
    var id = card.getAttribute("data-challenge-id");
    var challenge = state.challenges.find(function (c) { return String(c.id) === id; }) || {};
    var hints = Array.isArray(challenge.hints) ? challenge.hints : [];
    var revealed = 0;

    card.querySelectorAll("[data-hint-index]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var idx = parseInt(btn.getAttribute("data-hint-index"), 10);
        var area = card.querySelector("[data-hint-area]");
        if (!area || idx >= hints.length) return;
        /* Hints reveal one at a time, in order. */
        if (idx !== revealed) return;
        var p = document.createElement("p");
        p.className = "hint-text";
        p.textContent = "Hint " + (idx + 1) + ": " + hints[idx];
        area.appendChild(p);
        revealed++;
        btn.disabled = true;
      });
    });

    var form = card.querySelector("[data-solve-form]");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var result = card.querySelector("[data-solve-result]");
        result.className = "challenge-result";
        result.textContent = "Checking your solution…";
        apiPostRaw("/api/v1/challenges/" + encodeURIComponent(id) + "/solve", {
          identity: form.querySelector("[data-solve-identity]").value,
          method: form.querySelector("[data-solve-method]").value.trim(),
          path: form.querySelector("[data-solve-path]").value.trim()
        }).then(function (res) {
          var d = res.data || {};
          var solved = d.solved === true || d.status === "solved" || d.result === "solved";
          result.classList.add(solved ? "solved" : "failed");
          var text = solved ? "Solved — " : "Not solved — ";
          text += d.message || d.detail || (solved ? "correct attack path." : "that identity/method/path did not validate.");
          if (d.evidence) text += " Evidence: " + (typeof d.evidence === "string" ? d.evidence : JSON.stringify(d.evidence));
          if (!res.ok && !d.message && !d.detail) text = "Solve failed (HTTP " + res.status + ").";
          result.textContent = text;
          /* Learn section from the solve response, when the backend sends it. */
          if ((d.lesson || d.remediation || d.graph_path) && !card.querySelector(".challenge-learn")) {
            var div = document.createElement("div");
            div.className = "challenge-learn";
            div.innerHTML = "<strong>Learn</strong><br>" +
              (d.lesson ? "Lesson: " + esc(d.lesson) + "<br>" : "") +
              (d.remediation ? "Remediation: " + esc(d.remediation) + "<br>" : "") +
              (d.graph_path ? "Graph path: <span class=\"mono\">" + esc(typeof d.graph_path === "string" ? d.graph_path : JSON.stringify(d.graph_path)) + "</span>" : "");
            card.appendChild(div);
          }
        }).catch(function (err) {
          result.classList.add("failed");
          result.textContent = "Solve request failed: " + err.message;
        });
      });
    }

    var writeupBtn = card.querySelector("[data-writeup-btn]");
    if (writeupBtn) {
      writeupBtn.addEventListener("click", function () {
        var out = card.querySelector("[data-writeup-result]");
        var format = card.querySelector("[data-writeup-format]").value;
        out.className = "challenge-result";
        out.textContent = "Generating writeup…";
        apiPostRaw("/api/v1/challenges/" + encodeURIComponent(id) + "/writeup", { format: format })
          .then(function (res) {
            var d = res.data || {};
            if (!res.ok) {
              out.classList.add("failed");
              out.textContent = "Writeup failed (HTTP " + res.status + "): " + (d.detail || d.message || "unknown error");
              return;
            }
            out.classList.add("solved");
            out.textContent = "Writeup ready: ";
            var links = writeupLinks(d);
            if (links.length) {
              links.forEach(function (l) {
                var a = document.createElement("a");
                a.href = l.href;
                a.textContent = l.label;
                a.setAttribute("download", "");
                out.appendChild(a);
                out.appendChild(document.createTextNode(" "));
              });
            } else {
              out.textContent += "generated (no download links returned by the server).";
            }
          })
          .catch(function (err) {
            out.classList.add("failed");
            out.textContent = "Writeup request failed: " + err.message;
          });
      });
    }
  });
}

/* Collect download links from a writeup/email response, whatever shape it uses. */
function writeupLinks(d) {
  var links = [];
  var push = function (href, label) {
    if (href) links.push({ href: String(href), label: label });
  };
  push(d.download_url, "Download");
  push(d.docx_url, "Download Word");
  push(d.pdf_url, "Download PDF");
  push(d.docx_path, "Download Word");
  push(d.pdf_path, "Download PDF");
  if (Array.isArray(d.files)) {
    d.files.forEach(function (f) {
      if (typeof f === "string") push(f, "Download");
      else if (f && (f.url || f.path)) push(f.url || f.path, f.label || f.format || "Download");
    });
  }
  if (Array.isArray(d.downloads)) {
    d.downloads.forEach(function (f) {
      if (typeof f === "string") push(f, "Download");
      else if (f && (f.url || f.path)) push(f.url || f.path, f.label || f.format || "Download");
    });
  }
  if (Array.isArray(d.links)) {
    d.links.forEach(function (f) {
      if (f && (f.url || f.href)) push(f.url || f.href, f.label || "Download");
    });
  }
  return links;
}

/* ---------- CTF machines ---------- */

/* CTF machines backend (GET /api/v1/ctf-machines, …/sources,
   POST …/{id}/solved) is built by another agent. Everything here is
   defensive, like challenges: a 404 or any other failure shows plain
   error text instead of breaking the dashboard. All machine/source
   data comes from the API — nothing is hardcoded in the UI. */

function ctfDifficultyBadge(difficulty) {
  var cls;
  switch (String(difficulty || "").toLowerCase()) {
    case "beginner": cls = "badge-green"; break;
    case "intermediate": cls = "badge-amber"; break;
    case "advanced": cls = "badge-red"; break;
    default: cls = "badge-grey";
  }
  return '<span class="badge ' + cls + '">' + esc(difficulty || "—") + "</span>";
}

function ctfMachineList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.machines)) return data.machines;
  return [];
}

function ctfSourcesList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.sources)) return data.sources;
  return [];
}

function ctfQueryString() {
  var f = state.ctfFilters;
  var params = [];
  if (f.source) params.push("source=" + encodeURIComponent(f.source));
  if (f.difficulty) params.push("difficulty=" + encodeURIComponent(f.difficulty));
  if (f.type) params.push("type=" + encodeURIComponent(f.type));
  if (f.q) params.push("q=" + encodeURIComponent(f.q));
  return params.length ? "?" + params.join("&") : "";
}

function ctfFiltersActive() {
  var f = state.ctfFilters;
  return !!(f.source || f.difficulty || f.type || f.q);
}

/* Sidebar badge shows the total machine count (only meaningful when no
   filter is active, so a filtered list never overwrites the total). */
function updateCtfNavBadge() {
  var badge = $("ctf-nav-count");
  if (!badge || ctfFiltersActive()) return;
  badge.textContent = String(state.ctfMachines.length);
  badge.classList.remove("hidden");
}

function loadCtfSources() {
  var grid = $("ctf-sources-grid");
  return apiGet("/api/v1/ctf-machines/sources").then(function (data) {
    state.ctfSources = ctfSourcesList(data);
    renderCtfSources();
    renderCtfSourceFilter();
  }).catch(function (err) {
    if (grid) {
      grid.innerHTML = '<p class="muted">Sources could not be loaded (' +
        esc(err.message) + '). The backend for this screen is still being built; the rest of the dashboard is unaffected.</p>';
    }
    var status = $("ctf-status");
    if (status) status.textContent = "Could not load CTF sources: " + err.message;
  });
}

function renderCtfSources() {
  var grid = $("ctf-sources-grid");
  if (!grid) return;
  if (!state.ctfSources.length) {
    grid.innerHTML = '<p class="muted">No sources available yet.</p>';
    return;
  }
  grid.innerHTML = state.ctfSources.map(function (s) {
    var selected = state.ctfFilters.source && String(s.name) === state.ctfFilters.source;
    return '<article class="ctf-source-card' + (selected ? " selected" : "") + '" data-source-name="' + esc(s.name || "") + '" tabindex="0" role="button" aria-pressed="' + (selected ? "true" : "false") + '">' +
      '<div class="ctf-source-head"><h3>' + esc(s.name || "Unnamed source") + "</h3>" +
      (s.cost_label ? '<span class="badge badge-cyan">' + esc(s.cost_label) + "</span>" : "") + "</div>" +
      (s.description ? '<p class="ctf-source-desc">' + esc(s.description) + "</p>" : "") +
      '<div class="ctf-source-meta">' + (s.type ? "<span>" + esc(s.type) + "</span>" : "") + "</div>" +
      (s.homepage_url ? '<a class="ctf-source-visit" href="' + esc(s.homepage_url) + '" target="_blank" rel="noopener">Visit ↗</a>' : "") +
      "</article>";
  }).join("");
  grid.querySelectorAll(".ctf-source-card").forEach(function (card) {
    var activate = function () {
      var name = card.getAttribute("data-source-name");
      state.ctfFilters.source = name;
      var sel = $("ctf-filter-source");
      if (sel) sel.value = name;
      renderCtfSources();
      loadCtfMachines();
      var list = $("ctf-machines-list");
      if (list) list.scrollIntoView({ block: "start" });
    };
    card.addEventListener("click", function (e) {
      if (e.target.closest("a")) return; /* let the Visit link open */
      activate();
    });
    card.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); activate(); }
    });
  });
}

function renderCtfSourceFilter() {
  var sel = $("ctf-filter-source");
  if (!sel) return;
  var current = state.ctfFilters.source;
  sel.innerHTML = '<option value="">All sources</option>' + state.ctfSources.map(function (s) {
    return '<option value="' + esc(s.name || "") + '"' + (String(s.name) === current ? " selected" : "") + ">" + esc(s.name || "") + "</option>";
  }).join("");
  /* Keep the dropdown in sync when the active filter is not (yet) in the
     source list, e.g. a machine source the sources endpoint omits. */
  if (current && !state.ctfSources.some(function (s) { return String(s.name) === current; })) {
    var opt = document.createElement("option");
    opt.value = current;
    opt.textContent = current;
    opt.selected = true;
    sel.appendChild(opt);
  }
}

function loadCtfMachines() {
  var list = $("ctf-machines-list");
  var status = $("ctf-status");
  if (list && !state.ctfMachines.length) {
    list.innerHTML = '<p class="muted">Loading machines…</p>';
  }
  if (status) { status.className = "form-status"; status.textContent = ""; }
  return apiGet("/api/v1/ctf-machines" + ctfQueryString()).then(function (data) {
    state.ctfMachines = ctfMachineList(data);
    renderCtfMachines();
    updateCtfNavBadge();
  }).catch(function (err) {
    state.ctfMachines = [];
    if (list) {
      list.innerHTML = '<p class="muted">Machines could not be loaded — the CTF machines API returned an error (' +
        esc(err.message) + '). The backend for this screen is still being built; the rest of the dashboard is unaffected.</p>';
    }
    if (status) status.textContent = "Could not load CTF machines: " + err.message;
  });
}

function ctfMachineCardHtml(m) {
  var id = m.id || "";
  var topics = Array.isArray(m.topics) ? m.topics : [];
  var steps = Array.isArray(m.setup_steps) ? m.setup_steps : [];
  var solved = m.solved === true;
  var expanded = !!state.ctfExpanded[id];
  var meta = [];
  if (m.os) meta.push("OS: " + m.os);
  if (m.format) meta.push("Format: " + m.format);
  return '<article class="ctf-machine-card' + (solved ? " solved" : "") + '" data-machine-id="' + esc(id) + '">' +
    '<div class="ctf-machine-head"><h3>' + esc(m.name || id || "Untitled machine") + "</h3>" +
    '<span class="ctf-machine-badges">' + ctfDifficultyBadge(m.difficulty) +
    (solved ? '<span class="badge badge-green">✓ Solved</span>' : "") + "</span></div>" +
    '<div class="ctf-machine-meta">' + esc(m.source || "") +
    (m.type ? " · " + esc(m.type) : "") +
    (m.cost_label ? " · " + esc(m.cost_label) : "") + "</div>" +
    (m.description ? '<p class="ctf-machine-desc">' + esc(m.description) + "</p>" : "") +
    (topics.length ? '<div class="ctf-topics">' + topics.map(function (t) {
      return '<span class="topic-chip">' + esc(t) + "</span>";
    }).join("") + "</div>" : "") +
    (meta.length ? '<div class="ctf-machine-meta">' + esc(meta.join(" · ")) + "</div>" : "") +
    (m.learnings ? '<p class="ctf-machine-learn"><strong>You will learn:</strong> ' + esc(m.learnings) + "</p>" : "") +
    '<div class="ctf-actions">' +
    (m.homepage_url ? '<a class="button-link" href="' + esc(m.homepage_url) + '" target="_blank" rel="noopener">Download / Visit ↗</a>' : "") +
    (steps.length ? '<button type="button" data-ctf-setup-btn>' + (expanded ? "Hide setup steps" : "How to set up") + "</button>" : "") +
    '<button type="button" class="' + (solved ? "" : "primary") + '" data-ctf-solve-btn>' + (solved ? "Mark unsolved" : "Mark as solved") + "</button>" +
    "</div>" +
    (steps.length ? '<div class="ctf-setup' + (expanded ? "" : " hidden") + '" data-ctf-setup><ol>' +
      steps.map(function (s) { return "<li>" + esc(s) + "</li>"; }).join("") + "</ol></div>" : "") +
    "</article>";
}

function renderCtfMachines() {
  var list = $("ctf-machines-list");
  if (!list) return;
  var machines = state.ctfMachines;
  var solved = machines.filter(function (m) { return m.solved === true; }).length;
  $("ctf-count").textContent = machines.length + (machines.length === 1 ? " machine" : " machines");
  $("ctf-progress").textContent = solved + " / " + machines.length + " machines solved";
  if (!machines.length) {
    list.innerHTML = '<p class="muted">No machines match these filters.</p>';
    return;
  }
  list.innerHTML = machines.map(ctfMachineCardHtml).join("");
  wireCtfMachineCards(list);
}

function wireCtfMachineCards(list) {
  list.querySelectorAll(".ctf-machine-card").forEach(function (card) {
    var id = card.getAttribute("data-machine-id");
    var setupBtn = card.querySelector("[data-ctf-setup-btn]");
    if (setupBtn) {
      setupBtn.addEventListener("click", function () {
        state.ctfExpanded[id] = !state.ctfExpanded[id];
        var setup = card.querySelector("[data-ctf-setup]");
        if (setup) setup.classList.toggle("hidden", !state.ctfExpanded[id]);
        setupBtn.textContent = state.ctfExpanded[id] ? "Hide setup steps" : "How to set up";
      });
    }
    var solveBtn = card.querySelector("[data-ctf-solve-btn]");
    if (solveBtn) {
      solveBtn.addEventListener("click", function () {
        var machine = state.ctfMachines.find(function (x) { return String(x.id) === id; });
        var target = !(machine && machine.solved === true);
        solveBtn.disabled = true;
        solveBtn.textContent = target ? "Marking solved…" : "Marking unsolved…";
        apiPost("/api/v1/ctf-machines/" + encodeURIComponent(id) + "/solved", { solved: target })
          .then(function (updated) {
            var m2 = state.ctfMachines.find(function (x) { return String(x.id) === id; });
            if (m2) m2.solved = (updated && typeof updated.solved === "boolean") ? updated.solved : target;
            renderCtfMachines();
            updateCtfNavBadge();
            var status = $("ctf-status");
            if (status) {
              status.className = "form-status ok";
              status.textContent = "Marked \"" + (m2 ? (m2.name || id) : id) + "\" as " + (target ? "solved." : "unsolved.");
            }
          })
          .catch(function (err) {
            renderCtfMachines();
            var status = $("ctf-status");
            if (status) {
              status.className = "form-status err";
              status.textContent = "Could not update solved state: " + err.message;
            }
          });
      });
    }
  });
}

/* ---------- email writeup ---------- */

var EMAIL_RE = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

function currentReportId() {
  return (state.scan && state.scan.report_id) || state.scanId || null;
}

function sendWriteup(emailInputId, formatSelectId, statusId) {
  var email = $(emailInputId).value.trim();
  var format = $(formatSelectId).value;
  var status = $(statusId);
  status.className = "email-status";
  status.textContent = "";
  if (!EMAIL_RE.test(email)) {
    status.classList.add("err");
    status.textContent = "Enter a valid email address (e.g. you@example.com).";
    return;
  }
  var reportId = currentReportId();
  if (!reportId) {
    status.classList.add("err");
    status.textContent = "No scan report available yet — run a scan first.";
    return;
  }
  status.textContent = "Sending writeup to " + email + "…";
  apiPostRaw("/api/v1/reports/" + encodeURIComponent(reportId) + "/email", {
    email: email,
    format: format
  }).then(function (res) {
    var d = res.data || {};
    status.textContent = "";
    if (!res.ok) {
      status.classList.add("err");
      status.textContent = "Could not send the writeup (HTTP " + res.status + "): " + (d.detail || d.message || "unknown error");
      return;
    }
    var serverStatus = String(d.status || "").toLowerCase();
    if (serverStatus === "queued_locally") {
      status.classList.add("ok");
      status.textContent = "Email queued locally (no SMTP in the lab). Download the writeup below, or open your mail app: ";
      writeupLinks(d).forEach(function (l) {
        var a = document.createElement("a");
        a.href = l.href;
        a.textContent = l.label;
        a.setAttribute("download", "");
        status.appendChild(a);
        status.appendChild(document.createTextNode(" "));
      });
      var mailto = document.createElement("a");
      mailto.href = "mailto:" + encodeURIComponent(email) +
        "?subject=" + encodeURIComponent("GHOSTPATH X attack writeup — scan " + reportId) +
        "&body=" + encodeURIComponent("Hi,\n\nThe GHOSTPATH X attack writeup for scan " + reportId + " is attached / linked here.\n\nBuilt by Adarsh — GHOSTPATH X v0.4");
      mailto.textContent = "Open mail app";
      status.appendChild(mailto);
    } else if (serverStatus === "sent") {
      status.classList.add("ok");
      status.textContent = "Writeup sent to " + email + ".";
      writeupLinks(d).forEach(function (l) {
        var a = document.createElement("a");
        a.href = l.href;
        a.textContent = l.label;
        a.setAttribute("download", "");
        status.appendChild(document.createTextNode(" "));
        status.appendChild(a);
      });
    } else {
      status.classList.add("ok");
      status.textContent = d.message || ("Writeup request accepted for " + email + ".");
      writeupLinks(d).forEach(function (l) {
        var a = document.createElement("a");
        a.href = l.href;
        a.textContent = l.label;
        a.setAttribute("download", "");
        status.appendChild(document.createTextNode(" "));
        status.appendChild(a);
      });
    }
  }).catch(function (err) {
    status.classList.add("err");
    status.textContent = "Could not send the writeup: " + err.message;
  });
}

/* ---------- owner lock ---------- */

/* Showcase PIN lock, NOT real authentication. The PIN is sent once to
   POST /api/v1/owner/unlock and is never stored anywhere on the client:
   only the short-lived session token is kept, in sessionStorage. The
   owner details come only from GET /api/v1/owner/details with that
   token — they are never in the static frontend. */
var OWNER_TOKEN_KEY = "ghostpath_owner_token";

function ownerToken() {
  try { return sessionStorage.getItem(OWNER_TOKEN_KEY); } catch (e) { return null; }
}

function ownerClearToken() {
  try { sessionStorage.removeItem(OWNER_TOKEN_KEY); } catch (e) { /* storage unavailable */ }
}

function showOwnerLock() {
  var lock = $("owner-lock");
  var details = $("owner-details");
  if (lock) lock.classList.remove("hidden");
  if (details) details.classList.add("hidden");
  var pin = $("owner-pin");
  if (pin) pin.value = "";
}

function showOwnerDetails(data) {
  var lock = $("owner-lock");
  var details = $("owner-details");
  if (lock) lock.classList.add("hidden");
  if (details) details.classList.remove("hidden");
  if ($("owner-name")) $("owner-name").textContent = data.name || "Adarsh";
  if ($("owner-role")) $("owner-role").textContent = data.role || "";
  if ($("owner-title")) $("owner-title").textContent = data.title || "";
  if ($("owner-projects")) {
    $("owner-projects").textContent = Array.isArray(data.projects) ? "Built: " + data.projects.join(", ") : "";
  }
  var err = $("owner-error");
  if (err) err.textContent = "";
}

function refreshOwnerPage() {
  var token = ownerToken();
  if (!token) { showOwnerLock(); return; }
  fetch(API_BASE + "/api/v1/owner/details", {
    headers: { "Authorization": "Bearer " + token }
  }).then(function (res) {
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }).then(function (data) {
    showOwnerDetails(data);
  }).catch(function () {
    /* Missing or expired token: back to the lock screen. */
    ownerClearToken();
    showOwnerLock();
  });
}

function wireOwnerEvents() {
  var form = $("owner-unlock-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var pinInput = $("owner-pin");
      var err = $("owner-error");
      var btn = $("owner-unlock-btn");
      var pin = pinInput.value.trim();
      err.textContent = "";
      if (!/^\d{6}$/.test(pin)) {
        err.textContent = "Enter the 6-digit PIN.";
        return;
      }
      btn.disabled = true;
      btn.textContent = "Unlocking…";
      /* The PIN is sent once, in this request only. It is not stored
         in any variable, localStorage, or sessionStorage afterwards. */
      fetch(API_BASE + "/api/v1/owner/unlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin: pin })
      }).then(function (res) {
        return res.json().catch(function () { return {}; }).then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      }).then(function (res) {
        pinInput.value = "";
        pin = "";
        if (!res.ok) {
          if (res.status === 429) err.textContent = "Too many tries — try again in a minute";
          else err.textContent = "Incorrect PIN";
          return;
        }
        try { sessionStorage.setItem(OWNER_TOKEN_KEY, res.data.token); } catch (e) { /* storage unavailable */ }
        refreshOwnerPage();
      }).catch(function () {
        pinInput.value = "";
        pin = "";
        err.textContent = "Could not reach the server — try again.";
      }).then(function () {
        btn.disabled = false;
        btn.textContent = "Unlock";
      });
    });
  }
  var lockBtn = $("owner-lock-btn");
  if (lockBtn) {
    lockBtn.addEventListener("click", function () {
      ownerClearToken();
      showOwnerLock();
    });
  }
}

/* ---------- wiring ---------- */

function wireEvents() {
  document.querySelectorAll(".nav-item").forEach(function (btn) {
    btn.addEventListener("click", function () {
      showPage(btn.getAttribute("data-nav"));
    });
  });

  $("view-all-findings-btn").addEventListener("click", function () { showPage("findings"); });

  $("refresh-overview-btn").addEventListener("click", function () {
    setLoading(true, "Refreshing scan data…");
    loadScanData().then(renderAll).catch(function (err) { showError(err.message); })
      .then(function () { setLoading(false); });
  });

  $("lab-selector").addEventListener("change", function (e) {
    var lab = state.labs.find(function (l) { return String(l.id) === e.target.value; });
    if (!lab) return;
    state.lab = lab;
    setLoading(true, "Starting scan on " + (lab.name || lab.id) + "…");
    startScan(lab.id)
      .then(loadScanData)
      .then(function () { renderAll(); clearError(); })
      .catch(function (err) { showError("Scan failed: " + err.message); })
      .then(function () { setLoading(false); });
  });

  $("refresh-labs-btn").addEventListener("click", function () {
    apiGet("/api/v1/labs")
      .then(function (labs) {
        state.labs = Array.isArray(labs) ? labs : (labs.labs || []);
        renderLabSelector();
        renderLabs();
      })
      .catch(function (err) { showError(err.message); });
  });

  $("new-lab-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var status = $("lab-form-status");
    status.className = "form-status";
    status.textContent = "Creating lab…";
    apiPost("/api/v1/labs", {
      name: $("new-lab-name").value.trim(),
      base_url: $("new-lab-url").value.trim(),
      environment: $("new-lab-env").value
    }).then(function (lab) {
      state.labs.push(lab);
      renderLabSelector();
      renderLabs();
      status.className = "form-status ok";
      status.textContent = "Lab created: " + (lab.name || lab.id);
      $("new-lab-form").reset();
    }).catch(function (err) {
      status.className = "form-status err";
      status.textContent = "Could not create lab: " + err.message;
    });
  });

  $("refresh-scan-btn").addEventListener("click", function () {
    loadScanData().then(renderAll).catch(function (err) { showError(err.message); });
  });

  $("new-scan-btn").addEventListener("click", function () {
    if (!state.lab) { showError("No lab selected — create or select a lab first."); return; }
    var status = $("scan-action-status");
    status.textContent = "Starting new scan…";
    startScan(state.lab.id)
      .then(loadScanData)
      .then(function () { renderAll(); clearError(); status.textContent = "New scan finished."; })
      .catch(function (err) { status.textContent = "Scan failed: " + err.message; });
  });

  $("stop-scan-btn").addEventListener("click", function () {
    if (!state.scanId) return;
    var status = $("scan-action-status");
    status.textContent = "Sending stop request…";
    fetch(API_BASE + "/api/v1/scans/" + encodeURIComponent(state.scanId) + "/stop", { method: "POST" })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json().catch(function () { return {}; });
      })
      .then(function () {
        status.textContent = "Stop requested.";
        return loadScanData();
      })
      .then(renderAll)
      .catch(function (err) {
        status.textContent = "Stop request failed (" + err.message + ") — the backend may not implement a stop endpoint yet.";
      });
  });

  $("refresh-challenges-btn").addEventListener("click", function () {
    loadChallenges();
  });

  /* ---------- CTF machines filters ---------- */

  $("ctf-filter-source").addEventListener("change", function (e) {
    state.ctfFilters.source = e.target.value;
    renderCtfSources();
    loadCtfMachines();
  });

  $("ctf-filter-difficulty").addEventListener("change", function (e) {
    state.ctfFilters.difficulty = e.target.value;
    loadCtfMachines();
  });

  $("ctf-filter-type").addEventListener("change", function (e) {
    state.ctfFilters.type = e.target.value;
    loadCtfMachines();
  });

  var ctfSearchTimer = null;
  $("ctf-filter-q").addEventListener("input", function (e) {
    clearTimeout(ctfSearchTimer);
    ctfSearchTimer = setTimeout(function () {
      state.ctfFilters.q = e.target.value.trim();
      loadCtfMachines();
    }, 300);
  });

  $("ctf-clear-filters-btn").addEventListener("click", function () {
    state.ctfFilters = { source: "", difficulty: "", type: "", q: "" };
    $("ctf-filter-source").value = "";
    $("ctf-filter-difficulty").value = "";
    $("ctf-filter-type").value = "";
    $("ctf-filter-q").value = "";
    renderCtfSources();
    loadCtfMachines();
  });

  $("refresh-ctf-btn").addEventListener("click", function () {
    loadCtfSources();
    loadCtfMachines();
  });

  $("send-writeup-findings").addEventListener("click", function () {
    sendWriteup("email-findings", "email-format-findings", "email-status-findings");
  });

  $("send-writeup-evidence").addEventListener("click", function () {
    sendWriteup("email-evidence", "email-format-evidence", "email-status-evidence");
  });

  $("refresh-findings-btn").addEventListener("click", function () {
    if (!state.scanId) return;
    apiGet("/api/v1/findings?scan_id=" + encodeURIComponent(state.scanId))
      .then(function (f) {
        state.findings = Array.isArray(f) ? f : (f.findings || []);
        renderFindingsTable();
        renderDonut();
        renderRecentFindings();
        renderEvidence();
      })
      .catch(function (err) { showError(err.message); });
  });

  $("findings-tbody").addEventListener("click", function (e) {
    var dl = e.target.closest(".dl-btn");
    if (dl) {
      var f = state.findings.find(function (x) { return String(x.id) === dl.getAttribute("data-finding-id"); });
      if (f) downloadJson("evidence-" + (f.id || "finding") + ".json", f);
      return;
    }
    var row = e.target.closest("tr.row-click");
    if (!row) return;
    var detail = document.querySelector('#findings-tbody tr[data-detail-for="' + row.getAttribute("data-finding-id") + '"]');
    if (detail) detail.classList.toggle("hidden");
  });

  document.addEventListener("click", function (e) {
    var dl = e.target.closest("#evidence-list .dl-btn, #page-evidence .dl-btn");
    if (!dl) return;
    var f = state.findings.find(function (x) { return String(x.id) === dl.getAttribute("data-finding-id"); });
    if (f) downloadJson("evidence-" + (f.id || "finding") + ".json", f);
  });

  $("report-local-json-btn").addEventListener("click", function () {
    downloadJson("scan-" + (state.scanId || "report") + ".json", {
      scan: state.scan,
      paths: state.paths,
      findings: state.findings,
      graph: state.graph
    });
  });

  $("report-html-btn").addEventListener("click", function () {
    if (!state.scan) return;
    var rows = state.findings.map(function (f) {
      var h = findingEvidenceHash(f);
      return "<tr><td>" + esc(f.id || "") + "</td><td>" + esc(f.title || "") + "</td><td>" +
        esc(f.severity || "") + "</td><td>" + esc(f.status || "") + "</td><td>" +
        esc(findingSummary(f)) + "</td><td>" + esc(f.remediation || "") + "</td><td class=\"mono\">" +
        esc(h.hash) + "</td></tr>";
    }).join("");
    var scan = state.scan;
    var html = "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\">" +
      "<title>GHOSTPATH X — Scan report " + esc(state.scanId || "") + "</title>" +
      "<style>body{font-family:sans-serif;background:#05080F;color:#E6EDF3;margin:24px}" +
      "table{border-collapse:collapse;width:100%}th,td{border:1px solid rgba(34,211,238,0.12);padding:8px;text-align:left;vertical-align:top}" +
      "th{color:#8B9BB4;text-transform:uppercase;font-size:11px}.mono{font-family:monospace}</style></head><body>" +
      "<h1>GHOSTPATH X — Scan report</h1>" +
      "<p>Author: Adarsh</p>" +
      "<p>Scan: " + esc(state.scanId || "—") + " &middot; Lab: " + esc(state.lab ? state.lab.name : "—") +
      " &middot; Status: " + esc(scan.status || "—") + " &middot; Phase: " + esc(scan.phase || "—") + "</p>" +
      "<p>Endpoints: " + esc(scan.endpoints_discovered) + " &middot; Identities: " + esc(scan.identities_mapped) +
      " &middot; Attack paths: " + esc(scan.attack_paths) + " &middot; Validated findings: " + esc(scan.validated_findings) + "</p>" +
      "<table><thead><tr><th>ID</th><th>Title</th><th>Severity</th><th>Status</th><th>Summary</th><th>Remediation</th><th>Evidence hash</th></tr></thead>" +
      "<tbody>" + rows + "</tbody></table><footer><p>Built by Adarsh &bull; GHOSTPATH X v0.4</p></footer></body></html>";
    var blob = new Blob([html], { type: "text/html" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "report-" + (state.scanId || "scan") + ".html";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  });

  $("refresh-agents-btn").addEventListener("click", function () {
    loadScanData().then(function () { renderAgents(); renderTimeline(); renderOverview(); })
      .catch(function (err) { showError(err.message); });
  });

  $("test-connection-btn").addEventListener("click", function () {
    var el = $("settings-conn-status");
    el.textContent = "Testing…";
    apiGet("/api/v1/labs")
      .then(function (labs) {
        var n = Array.isArray(labs) ? labs.length : ((labs.labs || []).length);
        el.textContent = "Connected — " + n + (n === 1 ? " lab" : " labs") + " registered.";
        el.style.color = "#00E5A0";
      })
      .catch(function (err) {
        el.textContent = "Connection failed: " + err.message;
        el.style.color = "#FF3B5C";
      });
  });

  wireGraphEvents();
  wireOwnerEvents();
}

document.addEventListener("DOMContentLoaded", function () {
  wireEvents();
  bootstrap();
});
