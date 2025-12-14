const STORAGE_KEYS = {
  token: "tgz_token",
  apiBase: "tgz_api_base",
  projectTokens: "tgz_project_tokens",
  auditIntervals: "tgz_audit_intervals",
};

const LEGACY_STORAGE_KEYS = {
  token: "df_token",
  apiBase: "df_api_base",
  projectTokens: "df_project_tokens",
};

const state = {
  token: localStorage.getItem(STORAGE_KEYS.token) || localStorage.getItem(LEGACY_STORAGE_KEYS.token) || "",
  apiBase: localStorage.getItem(STORAGE_KEYS.apiBase) || localStorage.getItem(LEGACY_STORAGE_KEYS.apiBase) || "",
  projects: [],
  protocols: [],
  audits: [],
  steps: [],
  runs: [],
  events: [],
  operations: [],
  eventFilter: "all",
  eventSpecFilter: "",
  operationsInvalidOnly: false,
  operationsSpecFilter: "",
  projectSort: "name",
  protocolSort: "updated",
  runStepFilter: null,
  runKindFilter: "all",
  projectTokens: JSON.parse(
    localStorage.getItem(STORAGE_KEYS.projectTokens)
      || localStorage.getItem(LEGACY_STORAGE_KEYS.projectTokens)
      || "{}"
  ),
  auditIntervals: JSON.parse(localStorage.getItem(STORAGE_KEYS.auditIntervals) || "{}"),
  queueStats: null,
  queueJobs: [],
  metrics: { qaVerdicts: {}, tokenUsageByPhase: {}, tokenUsageByModel: {} },
  selectedProject: null,
  selectedProtocol: null,
  onboarding: {},
  clarifications: {},
  policyPacks: [],
  projectPolicy: {},
  effectivePolicy: {},
  policyFindings: {},
  protocolPolicyFindings: {},
  protocolPolicySnapshots: {},
  stepPolicyFindings: {},
  selectedStepForPolicy: null,
  adminSelectedPolicyPackId: null,
  poll: null,
};

// Rough price table (USD per 1k tokens). Extend as needed; unknown models default to 0.
const MODEL_PRICING = {
  "gpt-5.1-high": 0.003,
  "gpt-5.1": 0.002,
  "gpt-5.1-codex-max": 0.02,
  "gpt-5.1-codex-mini": 0.01,
  // Default model for this repo (OpenCode): price depends on your provider.
  "zai-coding-plan/glm-4.6": 0,
  // Legacy aliases kept for older runs.
  "codex-5.1-max-xhigh": 0.02,
  "codex-5.1-max": 0.01,
};

const statusEl = document.getElementById("authStatus");
const apiBaseInput = document.getElementById("apiBase");
const apiTokenInput = document.getElementById("apiToken");
const projectTokenInput = document.getElementById("projectToken");
const saveProjectTokenBtn = document.getElementById("saveProjectToken");
const auditIntervalInput = document.getElementById("auditInterval");

function setStatus(message, level = "info") {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.style.color = level === "error" ? "#f87171" : "#7e8ba1";

  if (level === "toast") {
    statusEl.style.transition = "opacity 0.3s ease";
    statusEl.style.opacity = 1;
    setTimeout(() => {
      statusEl.style.opacity = 0.4;
    }, 1200);
  }
}

function apiPath(path) {
  const base = state.apiBase || "";
  const baseTrimmed = base.endsWith("/") ? base.slice(0, -1) : base;
  return `${baseTrimmed}${path}`;
}

function statusClass(status) {
  return `status-${(status || "").toLowerCase()}`;
}

async function enqueueSpecAudit(projectId = null) {
  try {
    const intervalVal = auditIntervalInput && auditIntervalInput.value ? parseInt(auditIntervalInput.value, 10) : null;
    if (projectId && intervalVal) {
      state.auditIntervals[String(projectId)] = intervalVal;
      persistAuditIntervals();
    }
    const payload = { project_id: projectId, backfill: true, interval_seconds: intervalVal || undefined };
    const resp = await apiFetch("/specs/audit", { method: "POST", body: JSON.stringify(payload), projectId });
    setStatus(`Spec audit enqueued${resp.job?.job_id ? ` (${resp.job.job_id})` : ""}`, "toast");
    loadOperations();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function apiFetch(path, options = {}) {
  const { projectId, ...restOptions } = options;
  const headers = restOptions.headers || {};
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  const targetProjectId = projectId || state.selectedProject;
  if (targetProjectId) {
    const projectToken = state.projectTokens[String(targetProjectId)];
    if (projectToken) {
      headers["X-Project-Token"] = projectToken;
    }
  }
  if (restOptions.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(apiPath(path), { ...restOptions, headers });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status} ${resp.statusText}: ${text}`);
  }
  const contentType = resp.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return resp.json();
  }
  return resp.text();
}

function persistAuth() {
  localStorage.setItem(STORAGE_KEYS.token, state.token);
  localStorage.setItem(STORAGE_KEYS.apiBase, state.apiBase);
  apiBaseInput.value = state.apiBase;
  apiTokenInput.value = state.token;
  setStatus("Auth saved. Loading data...");
  loadProjects();
  loadPolicyPacks();
  loadOperations();
  loadQueue();
  loadMetrics();
}

async function loadPolicyPacks() {
  try {
    const packs = await apiFetch("/policy_packs");
    state.policyPacks = packs || [];
    renderPolicyPanel();
  } catch (err) {
    state.policyPacks = [];
  }
}

async function loadProjectPolicy(projectId = null) {
  const targetId = projectId || state.selectedProject;
  if (!targetId) return;
  try {
    const policy = await apiFetch(`/projects/${targetId}/policy`, { projectId: targetId });
    state.projectPolicy[targetId] = policy;
    renderPolicyPanel();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadEffectivePolicy(projectId = null) {
  const targetId = projectId || state.selectedProject;
  if (!targetId) return;
  try {
    const policy = await apiFetch(`/projects/${targetId}/policy/effective`, { projectId: targetId });
    state.effectivePolicy[targetId] = policy;
    renderPolicyPanel();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadPolicyFindings(projectId = null) {
  const targetId = projectId || state.selectedProject;
  if (!targetId) return;
  try {
    const findings = await apiFetch(`/projects/${targetId}/policy/findings`, { projectId: targetId });
    state.policyFindings = state.policyFindings || {};
    state.policyFindings[targetId] = findings || [];
    renderPolicyPanel();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadProtocolPolicyFindings(protocolRunId = null) {
  const targetId = protocolRunId || state.selectedProtocol;
  if (!targetId) return;
  try {
    const findings = await apiFetch(`/protocols/${targetId}/policy/findings`);
    state.protocolPolicyFindings[targetId] = findings || [];
    renderProtocolDetail();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadProtocolPolicySnapshot(protocolRunId = null) {
  const targetId = protocolRunId || state.selectedProtocol;
  if (!targetId) return;
  try {
    const snap = await apiFetch(`/protocols/${targetId}/policy/snapshot`);
    state.protocolPolicySnapshots[targetId] = snap || null;
    renderProtocolDetail();
  } catch (err) {
    // Snapshot is optional/backfilled; don't break the UI.
    state.protocolPolicySnapshots[targetId] = null;
  }
}

async function loadStepPolicyFindings(stepRunId) {
  if (!stepRunId) return;
  try {
    const findings = await apiFetch(`/steps/${stepRunId}/policy/findings`);
    state.stepPolicyFindings[stepRunId] = findings || [];
    state.selectedStepForPolicy = stepRunId;
    renderProtocolDetail();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function persistProjectTokens() {
  localStorage.setItem(STORAGE_KEYS.projectTokens, JSON.stringify(state.projectTokens));
  if (state.selectedProject && projectTokenInput) {
    projectTokenInput.value = state.projectTokens[String(state.selectedProject)] || "";
  }
}

function persistAuditIntervals() {
  localStorage.setItem(STORAGE_KEYS.auditIntervals, JSON.stringify(state.auditIntervals));
  if (state.selectedProject && auditIntervalInput) {
    const val = state.auditIntervals[String(state.selectedProject)];
    auditIntervalInput.value = val ? String(val) : "";
  }
}

function policyPackById(id) {
  const needle = String(id || "");
  return (state.policyPacks || []).find((p) => String(p.id) === needle) || null;
}

function defaultPolicyPackTemplate(key, version, name) {
  return {
    meta: { key: String(key || ""), version: String(version || ""), name: String(name || "") },
    defaults: {},
    requirements: {},
    clarifications: [],
    enforcement: { mode: "warn", block_codes: [] },
  };
}

function onboardingPill(summary) {
  if (!summary) return "";
  return `<span class="pill ${statusClass(summary.status)}">${summary.status}</span>`;
}

async function loadProjects() {
  try {
    const projects = await apiFetch("/projects");
    state.projects = projects;
    renderProjects();
    setStatus(`Loaded ${projects.length} project(s).`);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadOnboarding(projectId = null) {
  const targetId = projectId || state.selectedProject;
  if (!targetId) return;
  try {
    const summary = await apiFetch(`/projects/${targetId}/onboarding`);
    state.onboarding[targetId] = summary;
    await loadProjectClarifications(targetId);
    renderProjects();
    renderOnboardingDetail();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadProjectClarifications(projectId = null) {
  const targetId = projectId || state.selectedProject;
  if (!targetId) return;
  try {
    const items = await apiFetch(`/projects/${targetId}/clarifications?status=open`, { projectId: targetId });
    state.clarifications[targetId] = items || [];
  } catch (err) {
    state.clarifications[targetId] = [];
  }
}

async function startOnboarding(inline = false) {
  if (!state.selectedProject) {
    setStatus("Select a project first.", "error");
    return;
  }
  try {
    const resp = await apiFetch(`/projects/${state.selectedProject}/onboarding/actions/start`, {
      method: "POST",
      body: JSON.stringify({ inline }),
      projectId: state.selectedProject,
    });
    setStatus(resp.message || (inline ? "Setup ran inline." : "Setup enqueued."), "toast");
    await loadOnboarding();
  } catch (err) {
    setStatus(err.message, "error");
  }
}


async function enqueueSpecAudit(projectId = null) {
  try {
    const payload = { project_id: projectId, backfill: true };
    const resp = await apiFetch('/specs/audit', { method: 'POST', body: JSON.stringify(payload), projectId });
    setStatus(`Spec audit enqueued (job ${resp.job?.job_id || ''})`, 'toast');
    loadOperations();
  } catch (err) {
    setStatus(err.message, 'error');
  }
}

function renderProjects() {
  const container = document.getElementById("projectList");
  container.innerHTML = "";
  const sortBar = document.createElement("div");
  sortBar.className = "sort-toggle";
  sortBar.innerHTML = `
    <span>Sort projects by:</span>
    <button class="${state.projectSort === "name" ? "active" : ""}" data-sort="name">Name</button>
    <button class="${state.projectSort === "spec" ? "active" : ""}" data-sort="spec">Spec status</button>
  `;
  container.appendChild(sortBar);
  const sorted = [...state.projects].sort((a, b) => {
    if (state.projectSort === "name") {
      return a.name.localeCompare(b.name);
    }
    if (state.projectSort === "spec") {
      const aInvalid = (state.protocols || []).some((p) => p.project_id === a.id && p.spec_validation_status === "invalid");
      const bInvalid = (state.protocols || []).some((p) => p.project_id === b.id && p.spec_validation_status === "invalid");
      if (aInvalid !== bInvalid) return aInvalid ? -1 : 1;
      return a.name.localeCompare(b.name);
    }
    return a.id - b.id;
  });
  sorted.forEach((proj) => {
    const anyInvalid = (state.protocols || []).some((p) => p.project_id === proj.id && p.spec_validation_status === "invalid");
    const audits = (state.operations || []).filter((o) => o.project_id === proj.id && o.event_type === "spec_audit");
    const latestAudit = audits.length ? audits[0] : null;
    const auditPill = latestAudit
      ? `<span class="pill">${latestAudit.created_at ? new Date(latestAudit.created_at).toLocaleTimeString() : "audit"}</span>`
      : "";
    const onboarding = state.onboarding[proj.id];
    const policyPill = proj.policy_pack_key ? `<span class="pill">${proj.policy_pack_key}</span>` : "";
    const enforcementPill = (proj.policy_enforcement_mode || "").toLowerCase() === "block"
      ? `<span class="pill warn">policy:block</span>`
      : "";
    const card = document.createElement("div");
    card.className = `card ${state.selectedProject === proj.id ? "active" : ""}`;
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div>${proj.name}</div>
          <div class="muted" style="font-size:12px;">${proj.git_url}</div>
        </div>
        <div style="display:flex; gap:6px; align-items:center;">
          ${anyInvalid ? `<span class="pill spec-invalid">spec invalid</span>` : ""}
          ${auditPill}
          ${onboardingPill(onboarding)}
          ${policyPill}
          ${enforcementPill}
          <span class="pill">${proj.base_branch}</span>
        </div>
      </div>
    `;
    card.onclick = () => {
      if (state.poll) {
        clearInterval(state.poll);
        state.poll = null;
      }
      state.selectedProject = proj.id;
      state.selectedProtocol = null;
      state.steps = [];
      state.events = [];
      loadOnboarding(proj.id);
      loadProjectPolicy(proj.id);
      if (projectTokenInput) {
        projectTokenInput.value = state.projectTokens[String(proj.id)] || "";
      }
      if (auditIntervalInput) {
        const val = state.auditIntervals[String(proj.id)];
        auditIntervalInput.value = val ? String(val) : "";
      }
      renderProjects();
      loadProtocols();
      loadOperations();
      renderPolicyPanel();
    };
      container.appendChild(card);
    });
  container.querySelectorAll(".sort-toggle button[data-sort]").forEach((btn) => {
    btn.onclick = () => {
      state.projectSort = btn.getAttribute("data-sort");
      renderProjects();
    };
  });
}

function renderPolicyPanel() {
  const content = document.getElementById("policyContent");
  const form = document.getElementById("policyForm");
  const select = document.getElementById("policyPackKey");
  const versionModeEl = document.getElementById("policyPackVersionMode");
  const versionSelectEl = document.getElementById("policyPackVersionSelect");
  const versionInput = document.getElementById("policyPackVersion");
  const packInfoEl = document.getElementById("policyPackInfo");
  const overridesEl = document.getElementById("policyOverrides");
  const repoLocalEl = document.getElementById("policyRepoLocalEnabled");
  const enforcementEl = document.getElementById("policyEnforcementMode");
  const hashEl = document.getElementById("policyHash");
  const previewEl = document.getElementById("policyPreview");
  const findingsEl = document.getElementById("policyFindings");
  const checksEl = document.getElementById("policyRequiredChecks");
  const blockCodesEl = document.getElementById("policyBlockCodes");
  const adminSelectEl = document.getElementById("adminPolicyPackSelect");

  if (!state.selectedProject) {
    if (content) content.textContent = "Select a project to configure policy packs.";
    if (form) form.style.display = "none";
    return;
  }
  if (content) content.textContent = "";
  if (form) form.style.display = "block";

  const projectId = state.selectedProject;
  const project = state.projects.find((p) => p.id === projectId);
  const current = state.projectPolicy[projectId] || {};

  const persistedPackKey = current.policy_pack_key || project?.policy_pack_key || "default";
  const persistedPackVersion = current.policy_pack_version ?? project?.policy_pack_version ?? null;

  const draftPackKey = select && select.value ? String(select.value) : null;
  const selectedPackKey = draftPackKey || persistedPackKey;

  const draftVersionMode = versionModeEl && versionModeEl.value ? String(versionModeEl.value) : null;
  const baseVersionMode = draftVersionMode || (persistedPackVersion ? "pin" : "latest");

  const draftVersion = versionInput && versionInput.value ? String(versionInput.value) : null;
  const currentPackVersion = (baseVersionMode === "pin" ? (draftVersion || persistedPackVersion) : null);

  if (select) {
    const byKey = {};
    (state.policyPacks || []).forEach((p) => {
      byKey[p.key] = true;
    });
    const keys = Object.keys(byKey).sort();
    select.innerHTML = keys.length
      ? keys.map((k) => `<option value="${k}">${k}</option>`).join("")
      : `<option value="default">default</option>`;
    select.value = selectedPackKey;
    select.onchange = () => {
      const key = select.value || "default";
      const latest = latestPackForKey(key);
      if (versionSelectEl) {
        const versions = packsForKey(key).map((p) => p.version).filter(Boolean);
        versionSelectEl.innerHTML = `<option value="">(choose)</option>`
          + versions.map((v) => `<option value="${escapeHtml(String(v))}">${escapeHtml(String(v))}</option>`).join("");
      }
      const mode = versionModeEl ? String(versionModeEl.value || baseVersionMode) : baseVersionMode;
      if (versionInput) {
        if (mode === "pin") {
          versionInput.value = (latest && latest.version) ? String(latest.version) : "";
        } else {
          versionInput.value = "";
        }
      }
      renderPolicyPanel();
    };
  }

  if (versionModeEl) {
    versionModeEl.value = baseVersionMode;
    versionModeEl.onchange = () => renderPolicyPanel();
  }

  if (versionSelectEl) {
    const key = (select && select.value) || selectedPackKey;
    const versions = packsForKey(key).map((p) => p.version).filter(Boolean);
    versionSelectEl.innerHTML = `<option value="">(choose)</option>`
      + versions.map((v) => `<option value="${escapeHtml(String(v))}">${escapeHtml(String(v))}</option>`).join("");
    versionSelectEl.value = currentPackVersion ? String(currentPackVersion) : "";
    versionSelectEl.onchange = () => {
      if (versionInput) versionInput.value = versionSelectEl.value || "";
    };
  }

  if (versionInput) {
    versionInput.value = currentPackVersion ? String(currentPackVersion) : "";
    const mode = versionModeEl ? String(versionModeEl.value || baseVersionMode) : baseVersionMode;
    versionInput.disabled = mode !== "pin";
    if (versionSelectEl) versionSelectEl.disabled = mode !== "pin";
  }

  if (packInfoEl) {
    const key = (select && select.value) || selectedPackKey;
    const packs = packsForKey(key);
    const latest = latestPackForKey(key);
    const versions = packs.map((p) => p.version).filter(Boolean);
    const desc = latest && latest.description ? escapeHtml(latest.description) : "";
    const status = latest && latest.status ? escapeHtml(latest.status) : "";
    packInfoEl.innerHTML = `
      <div><strong>${escapeHtml(key)}</strong>${latest && latest.version ? ` @ ${escapeHtml(latest.version)}` : ""} ${status ? `<span class="pill">${status}</span>` : ""}</div>
      ${desc ? `<div class="muted small">${desc}</div>` : ""}
      ${versions.length ? `<div class="muted small">Versions: ${versions.map((v) => `<code>${escapeHtml(v)}</code>`).join(" ")}</div>` : ""}
    `;
  }
  if (repoLocalEl) {
    repoLocalEl.checked = Boolean(current.policy_repo_local_enabled ?? project?.policy_repo_local_enabled ?? false);
  }
  if (enforcementEl) {
    enforcementEl.value = (current.policy_enforcement_mode || project?.policy_enforcement_mode || "warn").toLowerCase();
  }
  if (overridesEl) {
    const overrides = current.policy_overrides ?? project?.policy_overrides ?? null;
    overridesEl.value = overrides ? JSON.stringify(overrides, null, 2) : "";
  }
  if (hashEl) {
    const hash = current.policy_effective_hash || project?.policy_effective_hash || "";
    hashEl.textContent = hash ? `Effective hash: ${hash}` : "Effective hash: (compute via Preview effective)";
  }
  if (previewEl) {
    const eff = state.effectivePolicy[projectId];
    if (eff && eff.policy) {
      previewEl.textContent = JSON.stringify({ sources: eff.sources, policy: eff.policy }, null, 2);
    } else {
      previewEl.textContent = "Click “Preview effective” to compute and display the merged policy.";
    }
  }
  if (findingsEl) {
    const findings = (state.policyFindings && state.policyFindings[projectId]) || [];
    if (!findings.length) {
      findingsEl.innerHTML = `<div class="muted small">No findings loaded. Use Refresh or Preview to load.</div>`;
    } else {
      findingsEl.innerHTML = findings
        .map((f) => {
          const fix = f.suggested_fix ? `<div class="muted small">Fix: ${escapeHtml(f.suggested_fix)}</div>` : "";
          return `<div style="padding:8px; border:1px solid rgba(148,163,184,0.2); border-radius:10px; margin:8px 0;">
            <div><span class="pill">${escapeHtml(f.severity || "warning")}</span> <strong>${escapeHtml(f.code)}</strong></div>
            <div class="small">${escapeHtml(f.message || "")}</div>
            ${fix}
          </div>`;
        })
        .join("");
    }
  }

  const clarEl = document.getElementById("policyClarifications");
  if (clarEl) {
    const clarifications = state.clarifications[projectId] || [];
    if (!clarifications.length) {
      clarEl.innerHTML = `<div class="muted small">No open clarifications. If blocked, answer clarifications in the Onboarding panel above.</div>`;
    } else {
      const blockingCount = clarifications.filter((c) => c.blocking).length;
      const optionalCount = clarifications.length - blockingCount;
      clarEl.innerHTML = `
        <div class="muted small" style="margin-bottom:8px;">
          ${blockingCount} blocking, ${optionalCount} optional clarifications.
          ${blockingCount > 0 ? `<span class="pill status-blocked onboarding">action required</span>` : ""}
        </div>
        ${clarifications.slice(0, 15).map((c) => {
          const blocking = c.blocking ? `<span class="pill status-blocked onboarding">blocking</span>` : `<span class="pill status-running onboarding">optional</span>`;
          const recommended = c.recommended ? `<div class="muted small">Recommended: <code>${escapeHtml(JSON.stringify(c.recommended))}</code></div>` : "";
          const answered = c.status === "answered" ? `<span class="pill status-completed onboarding">answered</span>` : "";
          return `<div style="padding:8px; border:1px solid rgba(148,163,184,0.2); border-radius:10px; margin:8px 0;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
              <strong>${escapeHtml(c.key)}</strong>
              <div>${blocking} ${answered}</div>
            </div>
            <div class="small">${escapeHtml(c.question || "")}</div>
            ${recommended}
          </div>`;
        }).join("")}
        ${clarifications.length > 15 ? `<div class="muted small">...and ${clarifications.length - 15} more. See Onboarding panel to answer.</div>` : ""}
        <div class="muted small" style="margin-top:8px;">
          <a href="#onboardingPanel" style="color:var(--color-primary);">→ Go to Onboarding panel to answer clarifications</a>
        </div>
      `;
    }
  }

  if (checksEl) {
    const eff = state.effectivePolicy[projectId];
    let checks = [];
    if (eff && eff.policy) {
      checks = extractRequiredChecks(eff.policy);
    } else {
      const key = (select && select.value) || current.policy_pack_key || project?.policy_pack_key || "default";
      const pack = (state.policyPacks || []).find((p) => p.key === key);
      checks = pack && pack.pack ? extractRequiredChecks(pack.pack) : [];
    }
    checksEl.innerHTML = checks.length
      ? `<div class="muted small">Required checks</div><ul class="muted small">${checks.map((c) => `<li><code>${escapeHtml(c)}</code></li>`).join("")}</ul>`
      : `<div class="muted small">Required checks: (none)</div>`;
  }

  if (blockCodesEl) {
    const eff = state.effectivePolicy[projectId];
    let blockCodes = [];
    if (eff && eff.policy && eff.policy.enforcement) {
      const enforcement = eff.policy.enforcement;
      if (enforcement && typeof enforcement === "object" && Array.isArray(enforcement.block_codes)) {
        blockCodes = enforcement.block_codes.map((c) => String(c)).filter((c) => c.trim());
      }
    } else {
      const key = (select && select.value) || current.policy_pack_key || project?.policy_pack_key || "default";
      const pack = (state.policyPacks || []).find((p) => p.key === key);
      const enforcement = pack && pack.pack ? pack.pack.enforcement : null;
      if (enforcement && typeof enforcement === "object" && Array.isArray(enforcement.block_codes)) {
        blockCodes = enforcement.block_codes.map((c) => String(c)).filter((c) => c.trim());
      }
    }
    if (!blockCodes.length) {
      blockCodesEl.innerHTML = `<div class="muted small">Strict-mode block codes: (none)</div>`;
    } else {
      const text = blockCodes.join("\n");
      blockCodesEl.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div class="muted small">Strict-mode block codes</div>
          <button class="tiny-btn" type="button" data-copy-text="${encodeURIComponent(text)}">Copy</button>
        </div>
        <div class="muted small">${blockCodes.map((c) => `<code>${escapeHtml(c)}</code>`).join("<br/>")}</div>
      `;
    }
  }

  if (adminSelectEl) {
    const packs = (state.policyPacks || []).slice().sort((a, b) => {
      const ak = String(a.key || "");
      const bk = String(b.key || "");
      if (ak !== bk) return ak.localeCompare(bk);
      return String(a.version || "").localeCompare(String(b.version || ""));
    });
    adminSelectEl.innerHTML = packs.length
      ? packs.map((p) => {
        const label = `${String(p.key)}@${String(p.version)} (${String(p.status || "active")})`;
        return `<option value="${escapeHtml(String(p.id))}">${escapeHtml(label)}</option>`;
      }).join("")
      : `<option value="">(no packs)</option>`;
    const desired = state.adminSelectedPolicyPackId ? String(state.adminSelectedPolicyPackId) : null;
    if (desired && packs.some((p) => String(p.id) === desired)) {
      adminSelectEl.value = desired;
    }
  }
}

async function loadProtocols() {
  if (!state.selectedProject) {
    document.getElementById("protocolList").innerHTML = `<p class="muted">Select a project to view runs.</p>`;
    document.getElementById("protocolDetail").innerHTML = "";
    return;
  }
  try {
    const runs = await apiFetch(`/projects/${state.selectedProject}/protocols`);
    state.protocols = runs;
    renderProtocols();
    renderOnboardingDetail();
    setStatus(`Loaded ${runs.length} protocol run(s).`);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadRuns() {
  if (!state.selectedProtocol) return;
  try {
    const runs = await apiFetch(`/protocols/${state.selectedProtocol}/runs?limit=200`);
    state.runs = runs || [];
    renderProtocolDetail();
  } catch (err) {
    // Runs are optional; don't break the whole console.
    state.runs = [];
  }
}

function renderProtocols() {
  const list = document.getElementById("protocolList");
  list.innerHTML = "";
  if (!state.protocols.length) {
    list.innerHTML = `<p class="muted">No protocol runs yet.</p>`;
  } else {
    const sortBar = document.createElement("div");
    sortBar.className = "sort-toggle";
    sortBar.innerHTML = `
      <span>Sort runs by:</span>
      <button class="${state.protocolSort === "updated" ? "active" : ""}" data-sort="updated">Updated</button>
      <button class="${state.protocolSort === "spec" ? "active" : ""}" data-sort="spec">Spec status</button>
    `;
    list.appendChild(sortBar);

    const sortedRuns = [...state.protocols].sort((a, b) => {
      if (state.protocolSort === "spec") {
        const rank = (run) => {
          const status = (run.spec_validation_status || "unknown").toLowerCase();
          if (status === "invalid") return 0;
          if (status === "unknown") return 1;
          if (status === "valid") return 2;
          return 3;
        };
        const diff = rank(a) - rank(b);
        if (diff !== 0) return diff;
      }
      const aTs = new Date(a.updated_at || 0).getTime() || 0;
      const bTs = new Date(b.updated_at || 0).getTime() || 0;
      if (bTs !== aTs) return bTs - aTs;
      return a.protocol_name.localeCompare(b.protocol_name);
    });

    const table = document.createElement("table");
    table.className = "table";
    table.innerHTML = `
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Spec</th>
          <th>Audit</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const body = table.querySelector("tbody");
    sortedRuns.forEach((run) => {
      const row = document.createElement("tr");
      row.style.cursor = "pointer";
      const specStatus = (run.spec_validation_status || "unknown").toLowerCase();
      const badgeClass = specStatus === "valid" ? "spec-valid" : specStatus === "invalid" ? "spec-invalid" : "spec-unknown";
      const specBadge = run.spec_hash
        ? `<span class="pill ${badgeClass}">${run.spec_hash} · ${specStatus}</span>`
        : `<span class="pill spec-unknown">spec: n/a</span>`;
      const latestAudit = (state.operations || []).find((ev) => ev.protocol_run_id === run.id && ev.event_type === "spec_audit");
      const auditBadge = latestAudit
        ? `<span class="pill">${formatDate(latestAudit.created_at)}</span>`
        : `<span class="pill muted">n/a</span>`;
      row.innerHTML = `
        <td>${run.protocol_name}</td>
        <td><span class="pill ${statusClass(run.status)}">${run.status}</span></td>
        <td>${specBadge}</td>
        <td>${auditBadge}</td>
        <td class="muted">${formatDate(run.updated_at)}</td>
      `;
      row.onclick = () => {
        state.selectedProtocol = run.id;
        state.runs = [];
        state.runStepFilter = null;
        state.runKindFilter = "all";
        state.selectedStepForPolicy = null;
        renderProtocols();
        loadSteps();
        loadEvents();
        loadRuns();
        loadProtocolPolicyFindings(run.id);
        loadProtocolPolicySnapshot(run.id);
        startPolling();
      };
      if (state.selectedProtocol === run.id) {
        row.style.background = "rgba(96,165,250,0.08)";
      }
      body.appendChild(row);
    });
    list.appendChild(table);

    sortBar.querySelectorAll("button[data-sort]").forEach((btn) => {
      btn.onclick = () => {
        state.protocolSort = btn.getAttribute("data-sort");
        renderProtocols();
      };
    });
  }
  renderProtocolDetail();
}

function renderProtocolDetail() {
  const container = document.getElementById("protocolDetail");
  if (!state.selectedProtocol) {
    container.innerHTML = `<p class="muted">Select a protocol run to see steps and events.</p>`;
    return;
  }
  const run = state.protocols.find((r) => r.id === state.selectedProtocol);
  if (!run) {
    container.innerHTML = `<p class="muted">Protocol not found.</p>`;
    return;
  }
  const latestStep = state.steps[state.steps.length - 1];
  const protocolFindings = (state.protocolPolicyFindings && state.protocolPolicyFindings[run.id]) || [];
  const protocolSnapshot = (state.protocolPolicySnapshots && state.protocolPolicySnapshots[run.id]) || null;
  const selectedStep = state.selectedStepForPolicy ? state.steps.find((s) => s.id === state.selectedStepForPolicy) : null;
  const stepFindings = state.selectedStepForPolicy ? (state.stepPolicyFindings[state.selectedStepForPolicy] || []) : [];
  const policyEvents = (state.events || [])
    .filter((e) => e.event_type === "policy_findings" || e.event_type === "policy_autofix" || e.event_type === "policy_blocked")
    .slice(-6)
    .reverse();
  const policyMetaBits = [];
  if (run.policy_pack_key) policyMetaBits.push(`pack:${run.policy_pack_key}${run.policy_pack_version ? `@${run.policy_pack_version}` : ""}`);
  if (run.policy_effective_hash) policyMetaBits.push(`hash:${run.policy_effective_hash}`);
  const isBlocked = (run.status || "").toLowerCase() === "blocked";
  container.innerHTML = `
    <div class="pane">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-weight:700;">${run.protocol_name}</div>
          <div class="muted">${run.description || ""}</div>
          ${policyMetaBits.length ? `<div class="muted small">${policyMetaBits.join(" · ")}</div>` : ""}
          ${renderTemplateMeta(run)}
          ${
            isBlocked
              ? `<div class="event" style="margin-top:10px;">
                   <div style="display:flex; justify-content:space-between; align-items:center;">
                     <strong>Blocked</strong>
                     <button id="openPolicyPanel" type="button" class="tiny-btn">Open Policy</button>
                   </div>
                   <div class="muted small">If blocked by policy, review Policy findings and either fix the repo/step or set enforcement back to warn.</div>
                 </div>`
              : ""
          }
        </div>
        <span class="pill ${statusClass(run.status)}">${run.status}</span>
      </div>
      <div class="actions">
        <button id="startRun" class="primary">Start planning</button>
        <button id="runNext">Run next step</button>
        <button id="retryStep">Retry failed step</button>
        <button id="runQa">Run QA on latest</button>
        <button id="approveStep">Approve latest</button>
        <button id="openPr">Open PR/MR now</button>
        <button id="pauseRun">Pause</button>
        <button id="resumeRun">Resume</button>
        <button id="cancelRun" class="danger">Cancel</button>
        <button id="refreshActive">Refresh</button>
      </div>
    </div>
    <div class="pane">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h3>Policy (run)</h3>
        <div class="panel-actions">
          <button id="refreshProtocolPolicy" type="button">Refresh</button>
          <button id="refreshProtocolPolicySnapshot" type="button" class="tiny-btn">Snapshot</button>
        </div>
      </div>
      ${
        protocolSnapshot && protocolSnapshot.policy_effective_json
          ? `<details open>
              <summary>Policy snapshot</summary>
              <div class="muted small" style="margin-top:6px;">
                ${
                  protocolSnapshot.policy_pack_key
                    ? `pack:${escapeHtml(protocolSnapshot.policy_pack_key)}${protocolSnapshot.policy_pack_version ? `@${escapeHtml(protocolSnapshot.policy_pack_version)}` : ""}`
                    : "pack:(unknown)"
                }
                ${protocolSnapshot.policy_effective_hash ? ` · hash:${escapeHtml(protocolSnapshot.policy_effective_hash)}` : ""}
              </div>
              <div style="margin-top:8px; display:flex; justify-content:flex-end;">
                <button class="tiny-btn" type="button" data-copy-text="${encodeURIComponent(JSON.stringify(protocolSnapshot.policy_effective_json, null, 2))}">Copy JSON</button>
              </div>
              <pre class="code-block" style="margin-top:8px;">${escapeHtml(JSON.stringify(protocolSnapshot.policy_effective_json, null, 2))}</pre>
            </details>`
          : `<div class="muted small">Policy snapshot not loaded. Click Snapshot.</div>`
      }
      ${
        policyEvents.length
          ? `<div class="muted small">Recent policy events</div>
             ${policyEvents
               .map((e) => {
                 const meta = e.metadata || {};
                 let details = "";
                 if (e.event_type === "policy_autofix" && Array.isArray(meta.files) && meta.files.length) {
                   details = `<div class="muted small">Files: ${meta.files.map((f) => `<code>${escapeHtml(f)}</code>`).join(" ")}</div>`;
                 }
                 if (e.event_type === "policy_findings" && Array.isArray(meta.findings)) {
                   const truncated = meta.truncated ? " (truncated)" : "";
                   details = `<div class="muted small">Findings: ${meta.findings.length}${truncated}</div>`;
                 }
                 if (e.event_type === "policy_blocked" && Array.isArray(meta.blocking_findings)) {
                   details = `<div class="muted small">Blocking findings: ${meta.blocking_findings.length}</div>`;
                 }
                 return `<div class="event">
                   <div style="display:flex; justify-content:space-between;">
                     <span class="pill">${escapeHtml(e.event_type)}</span>
                     <span class="muted small">${escapeHtml(formatDate(e.created_at))}</span>
                   </div>
                   <div class="muted small">${escapeHtml(e.message || "")}</div>
                   ${details}
                 </div>`;
               })
               .join("")}`
          : `<div class="muted small">No policy events yet.</div>`
      }
      ${
        protocolFindings.length
          ? protocolFindings
              .map((f) => {
                const fix = f.suggested_fix ? `<div class="muted small">Fix: ${escapeHtml(f.suggested_fix)}</div>` : "";
                return `<div class="event">
                  <div style="display:flex; justify-content:space-between;">
                    <span class="pill">${escapeHtml(f.severity || "warning")}</span>
                    <span class="muted small">${escapeHtml(f.code || "")}</span>
                  </div>
                  <div>${escapeHtml(f.message || "")}</div>
                  ${fix}
                </div>`;
              })
              .join("")
          : `<div class="muted small">No findings loaded. Click Refresh.</div>`
      }
      ${
        selectedStep
          ? `<div style="margin-top:10px;">
              <div class="muted small">Step findings: ${escapeHtml(selectedStep.step_name)}</div>
              ${renderStepPolicyQuickFixes(stepFindings)}
              ${
                stepFindings.length
                  ? stepFindings
                      .map((f) => {
                        const fix = f.suggested_fix ? `<div class="muted small">Fix: ${escapeHtml(f.suggested_fix)}</div>` : "";
                        return `<div class="event">
                          <div style="display:flex; justify-content:space-between;">
                            <span class="pill">${escapeHtml(f.severity || "warning")}</span>
                            <span class="muted small">${escapeHtml(f.code || "")}</span>
                          </div>
                          <div>${escapeHtml(f.message || "")}</div>
                          ${fix}
                        </div>`;
                      })
                      .join("")
                  : `<div class="muted small">No step findings loaded. Click “Policy” on a step row.</div>`
              }
            </div>`
          : ""
      }
    </div>
    ${renderCiHints(run)}
    ${renderRunsPane()}
    <div class="split">
      <div class="pane">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <h3>Steps</h3>
          <span class="muted">${state.steps.length} step(s)</span>
        </div>
        ${renderStepsTable()}
      </div>
      <div class="pane">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <h3>Events</h3>
            <div class="muted small">${eventSummaryLabel()}</div>
          </div>
          <div class="button-group">
            ${["all", "loop", "trigger", "policy"].map((f) => `<button class="${state.eventFilter === f ? "primary" : ""}" data-filter="${f}">${f}</button>`).join(" ")}
            <input id="specFilterInput" class="input-inline" placeholder="spec hash" value="${state.eventSpecFilter || ""}" />
          </div>
        </div>
        ${renderEventsList()}
      </div>
    </div>
  `;

  document.getElementById("startRun").onclick = () => startProtocol(run.id);
  document.getElementById("pauseRun").onclick = () => pauseProtocol(run.id);
  document.getElementById("resumeRun").onclick = () => resumeProtocol(run.id);
  document.getElementById("cancelRun").onclick = () => cancelProtocol(run.id);
  document.getElementById("runNext").onclick = () => runNextStep(run.id);
  document.getElementById("retryStep").onclick = () => retryLatest(run.id);
  document.getElementById("runQa").onclick = () => runQaLatest();
  document.getElementById("approveStep").onclick = () => approveLatest();
  document.getElementById("openPr").onclick = () => openPr(run.id);
  document.getElementById("refreshActive").onclick = () => {
    loadSteps();
    loadEvents();
    loadRuns();
    loadProtocolPolicySnapshot(run.id);
  };
  const refreshProtocolPolicyBtn = document.getElementById("refreshProtocolPolicy");
  if (refreshProtocolPolicyBtn) {
    refreshProtocolPolicyBtn.onclick = () => loadProtocolPolicyFindings(run.id);
  }
  const refreshProtocolPolicySnapshotBtn = document.getElementById("refreshProtocolPolicySnapshot");
  if (refreshProtocolPolicySnapshotBtn) {
    refreshProtocolPolicySnapshotBtn.onclick = () => loadProtocolPolicySnapshot(run.id);
  }
  const openPolicyPanelBtn = document.getElementById("openPolicyPanel");
  if (openPolicyPanelBtn) {
    openPolicyPanelBtn.onclick = () => {
      const el = document.getElementById("policyPanel");
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      setStatus("Opened Policy panel.", "toast");
    };
  }
  bindEventFilters();
  bindRunsFilters();
  bindStepRunButtons();
  bindStepPolicyButtons();
  bindCopyTextButtons();

  document.querySelectorAll("button[data-copy-spec]").forEach((btn) => {
    btn.onclick = async (e) => {
      const hash = e.currentTarget.getAttribute("data-copy-spec");
      try {
        await navigator.clipboard.writeText(hash);
        setStatus(`Copied spec hash ${hash}`, "toast");
        const existing = e.currentTarget.parentElement.querySelector(".tiny-toast");
        if (existing) {
          existing.remove();
        }
        const toast = document.createElement("span");
        toast.className = "tiny-toast";
        toast.textContent = "Copied!";
        e.currentTarget.insertAdjacentElement("afterend", toast);
        setTimeout(() => {
          toast.remove();
        }, 1500);
      } catch (err) {
        setStatus("Copy failed", "error");
      }
    };
  });

  const startBtn = document.getElementById("startRun");
  const pauseBtn = document.getElementById("pauseRun");
  const resumeBtn = document.getElementById("resumeRun");
  const cancelBtn = document.getElementById("cancelRun");
  const runNextBtn = document.getElementById("runNext");
  const retryBtn = document.getElementById("retryStep");
  const qaBtn = document.getElementById("runQa");
  const approveBtn = document.getElementById("approveStep");

  const terminal = ["completed", "cancelled", "failed"].includes(run.status);
  startBtn.disabled = !["pending", "planned"].includes(run.status);
  pauseBtn.disabled = !["running", "planning"].includes(run.status);
  resumeBtn.disabled = run.status !== "paused";
  cancelBtn.disabled = terminal;

  runNextBtn.disabled = terminal || run.status === "paused";
  retryBtn.disabled = terminal || run.status === "paused";
  qaBtn.disabled = terminal || run.status === "paused" || !latestStep;
  approveBtn.disabled = terminal || run.status === "paused" || !latestStep;
}

function renderStepPolicyQuickFixes(stepFindings) {
  const findings = Array.isArray(stepFindings) ? stepFindings : [];
  if (!findings.length) return "";
  const chmodCmds = new Set();
  const missingChecks = new Set();

  findings.forEach((f) => {
    if (!f || !f.code) return;
    if (f.code === "policy.ci.required_check_not_executable") {
      const check = f.metadata && f.metadata.check ? String(f.metadata.check) : null;
      if (check) chmodCmds.add(`chmod +x ${check}`);
    }
    if (f.code === "policy.ci.required_check_missing") {
      const check = f.metadata && f.metadata.check ? String(f.metadata.check) : null;
      if (check) missingChecks.add(check);
    }
  });

  const cmds = Array.from(chmodCmds);
  const missing = Array.from(missingChecks);
  if (!cmds.length && !missing.length) return "";

  let stubScript = "";
  if (missing.length) {
    const lines = [];
    lines.push("# Create placeholder CI scripts required by policy");
    missing.forEach((check) => {
      lines.push(`mkdir -p \"$(dirname \\\"${check}\\\")\"`);
      lines.push(`cat > \"${check}\" <<'EOF'`);
      lines.push("#!/usr/bin/env bash");
      lines.push("set -euo pipefail");
      lines.push(`echo \"TODO: implement ${check}\"`);
      lines.push("EOF");
      lines.push(`chmod +x \"${check}\"`);
      lines.push("");
    });
    stubScript = lines.join("\n").trim();
  }

  const cmdBlock = cmds.length
    ? `<div class="event">
         <div style="display:flex; justify-content:space-between; align-items:center;">
           <strong>Quick fixes</strong>
           <button class="tiny-btn" type="button" data-copy-text="${encodeURIComponent(cmds.join("\\n"))}">Copy chmod</button>
         </div>
         <pre class="code-block">${escapeHtml(cmds.join("\\n"))}</pre>
       </div>`
    : "";
  const missingBlock = missing.length
    ? `<div class="event">
         <strong>Missing required checks</strong>
         <div class="muted small">${missing.map((c) => `<code>${escapeHtml(c)}</code>`).join("<br/>")}</div>
         <div style="margin-top:8px; display:flex; justify-content:flex-end;">
           <button class="tiny-btn" type="button" data-copy-text="${encodeURIComponent(stubScript)}">Copy create-stubs</button>
         </div>
         <pre class="code-block" style="margin-top:8px;">${escapeHtml(stubScript)}</pre>
       </div>`
    : "";
  return `${cmdBlock}${missingBlock}`;
}

function bindStepPolicyButtons() {
  document.querySelectorAll("button[data-step-policy]").forEach((btn) => {
    btn.onclick = (e) => {
      const stepId = parseInt(e.currentTarget.getAttribute("data-step-policy"), 10);
      if (!Number.isFinite(stepId)) return;
      loadStepPolicyFindings(stepId);
    };
  });
}

function bindCopyTextButtons() {
  document.querySelectorAll("button[data-copy-text]").forEach((btn) => {
    btn.onclick = (e) => {
      const encoded = e.currentTarget.getAttribute("data-copy-text") || "";
      const text = decodeURIComponent(encoded);
      copyText(text);
    };
  });
}

function renderRunsPane() {
  const runCount = (state.runs || []).length;
  const filtered = filteredRuns();
  const label = state.runStepFilter ? `step ${state.runStepFilter}` : "all";
  const kinds = Array.from(new Set((state.runs || []).map((r) => String(r.run_kind || r.job_type || "")))).filter(Boolean);
  const hasKind = (k) => kinds.includes(k);
  return `
    <div class="pane">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
        <div>
          <h3>Runs</h3>
          <div class="muted small">${filtered.length} shown · ${runCount} total · ${label}</div>
        </div>
        <div class="button-group">
          <button id="runsFilterAll" class="${state.runKindFilter === "all" ? "primary" : ""}">All</button>
          <button id="runsFilterExec" class="${state.runKindFilter === "exec" ? "primary" : ""}">Exec</button>
          <button id="runsFilterQa" class="${state.runKindFilter === "qa" ? "primary" : ""}">QA</button>
          <button id="runsFilterPlan" class="${state.runKindFilter === "plan" ? "primary" : ""}">Plan</button>
          ${hasKind("setup") ? `<button id="runsFilterSetup" class="${state.runKindFilter === "setup" ? "primary" : ""}">Setup</button>` : ""}
          ${hasKind("open_pr") ? `<button id="runsFilterOpenPr" class="${state.runKindFilter === "open_pr" ? "primary" : ""}">PR</button>` : ""}
          ${hasKind("spec_audit") ? `<button id="runsFilterAudit" class="${state.runKindFilter === "spec_audit" ? "primary" : ""}">Audit</button>` : ""}
          <button id="runsClearStep" class="${state.runStepFilter ? "primary" : ""}">Clear step</button>
          <button id="refreshRuns" type="button">Refresh</button>
        </div>
      </div>
      ${renderRunsTable(filtered)}
    </div>
  `;
}

function filteredRuns() {
  const all = state.runs || [];
  return all.filter((r) => {
    if (state.runStepFilter && String(r.step_run_id) !== String(state.runStepFilter)) return false;
    if (state.runKindFilter && state.runKindFilter !== "all" && String(r.run_kind) !== String(state.runKindFilter)) return false;
    return true;
  });
}

function renderRunsTable(runs) {
  if (!runs.length) {
    return `<p class="muted small">No runs to display yet.</p>`;
  }
  const rows = runs
    .map((r) => {
      const logUrl = r.log_path ? apiPath(`/codex/runs/${encodeURIComponent(r.run_id)}/logs`) : null;
      const detailUrl = apiPath(`/codex/runs/${encodeURIComponent(r.run_id)}`);
      const artifactsUrl = apiPath(`/codex/runs/${encodeURIComponent(r.run_id)}/artifacts`);
      const kind = r.run_kind || r.job_type || "-";
      const attempt = r.attempt != null ? r.attempt : "-";
      const stepId = r.step_run_id != null ? r.step_run_id : "-";
      const status = r.status || "-";
      const execModel = r.result && r.result.exec ? r.result.exec.model : null;
      const qaModel = r.result && r.result.qa ? r.result.qa.model : (r.result && r.result.qa_inline ? r.result.qa_inline.qa_model : null);
      const model = execModel || qaModel || "-";
      const verdict = (r.result && r.result.qa && r.result.qa.verdict) || (r.result && r.result.qa_inline && r.result.qa_inline.verdict) || "-";
      return `
        <tr>
          <td class="muted"><a href="${detailUrl}" target="_blank" rel="noreferrer">${r.run_id}</a></td>
          <td>${kind}</td>
          <td><span class="pill ${statusClass(status)}">${status}</span></td>
          <td class="muted">${model}</td>
          <td class="muted">${verdict}</td>
          <td class="muted">${attempt}</td>
          <td class="muted">${stepId}</td>
          <td class="muted">${formatDate(r.created_at)}</td>
          <td class="muted">${formatDate(r.started_at)}</td>
          <td class="muted">${formatDate(r.finished_at)}</td>
          <td>${logUrl ? `<a href="${logUrl}" target="_blank" rel="noreferrer">logs</a>` : `<span class="muted">-</span>`}</td>
          <td><a href="${artifactsUrl}" target="_blank" rel="noreferrer">artifacts</a></td>
        </tr>
      `;
    })
    .join("");
  return `
    <table class="table">
      <thead>
        <tr><th>Run ID</th><th>Kind</th><th>Status</th><th>Model</th><th>Verdict</th><th>Attempt</th><th>Step</th><th>Created</th><th>Started</th><th>Finished</th><th>Logs</th><th>Artifacts</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function bindRunsFilters() {
  const refreshBtn = document.getElementById("refreshRuns");
  if (refreshBtn) refreshBtn.onclick = () => loadRuns();
  const clearStep = document.getElementById("runsClearStep");
  if (clearStep) {
    clearStep.onclick = () => {
      state.runStepFilter = null;
      renderProtocolDetail();
    };
  }
  const setKind = (kind) => {
    state.runKindFilter = kind;
    renderProtocolDetail();
  };
  const allBtn = document.getElementById("runsFilterAll");
  if (allBtn) allBtn.onclick = () => setKind("all");
  const execBtn = document.getElementById("runsFilterExec");
  if (execBtn) execBtn.onclick = () => setKind("exec");
  const qaBtn = document.getElementById("runsFilterQa");
  if (qaBtn) qaBtn.onclick = () => setKind("qa");
  const planBtn = document.getElementById("runsFilterPlan");
  if (planBtn) planBtn.onclick = () => setKind("plan");
  const setupBtn = document.getElementById("runsFilterSetup");
  if (setupBtn) setupBtn.onclick = () => setKind("setup");
  const prBtn = document.getElementById("runsFilterOpenPr");
  if (prBtn) prBtn.onclick = () => setKind("open_pr");
  const auditBtn = document.getElementById("runsFilterAudit");
  if (auditBtn) auditBtn.onclick = () => setKind("spec_audit");
}

function bindStepRunButtons() {
  document.querySelectorAll("button[data-step-runs]").forEach((btn) => {
    btn.onclick = (e) => {
      const stepId = e.currentTarget.getAttribute("data-step-runs");
      if (!stepId) return;
      state.runStepFilter = stepId;
      renderProtocolDetail();
      // Ensure we have data; if not loaded yet, fetch it.
      if (!state.runs || !state.runs.length) {
        loadRuns();
      }
    };
  });
}

function renderTemplateMeta(run) {
  const cfg = run.template_config || {};
  const template = cfg.template || run.template_source || null;
  const parts = [];
  if (template) {
    const name = template.template || template.name || "template";
    const version = template.version ? `v${template.version}` : "";
    parts.push(`Template: ${name} ${version}`.trim());
  }
  if (run.spec_hash) {
    const status = (run.spec_validation_status || "unknown").toLowerCase();
    const ts = run.spec_validated_at ? formatDate(run.spec_validated_at) : "-";
    const badgeClass = status === "valid" ? "spec-valid" : status === "invalid" ? "spec-invalid" : "spec-unknown";
    parts.push(
      `<span class="pill ${badgeClass}">spec ${run.spec_hash} · ${status} · ${ts}</span>
       <button class="tiny-btn" data-copy-spec="${run.spec_hash}" title="Copy spec hash">⧉</button>`
    );
  }
  if (!parts.length) return "";
  return `<div class="muted" style="font-size:12px;">${parts.join(" · ")}</div>`;
}

function renderOnboardingDetail() {
  const container = document.getElementById("onboardingContent");
  if (!container) return;
  if (!state.selectedProject) {
    container.innerHTML = `<p class="muted small">Select a project to view onboarding progress.</p>`;
    return;
  }
  const summary = state.onboarding[state.selectedProject];
  if (!summary) {
    container.innerHTML = `<p class="muted small">Loading onboarding status...</p>`;
    return;
  }
  const clarifications = state.clarifications[state.selectedProject] || [];
  const stages = (summary.stages || [])
    .map((st) => {
      const when = st.created_at ? formatDate(st.created_at) : "";
      const msg = st.message || "";
      return `<div class="stage">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <h4>${st.name}</h4>
          <span class="pill ${statusClass(st.status)} onboarding">${st.status}</span>
        </div>
        <div class="muted">${msg}</div>
        <div class="muted small">${when}</div>
      </div>`;
    })
    .join("");
  const events = (summary.events || [])
    .slice(-8)
    .reverse()
    .map((ev) => {
      return `<tr>
        <td class="muted small">${formatDate(ev.created_at)}</td>
        <td>${ev.event_type}</td>
        <td class="muted small">${ev.message || ""}</td>
      </tr>`;
    })
    .join("");
  const lastMsg = summary.last_event ? summary.last_event.message : "";
  const lastTime = summary.last_event ? formatDate(summary.last_event.created_at) : "";
  const hint = summary.hint ? `<div class="muted small" style="margin-top:6px;">Hint: ${summary.hint}</div>` : "";
  const clarHtml = (() => {
    if (!clarifications.length) return `<div class="muted small">No open clarifications.</div>`;
    const cards = clarifications
      .slice(0, 25)
      .map((c) => {
        const recommended = c.recommended ? JSON.stringify(c.recommended, null, 2) : "";
        const blocking = c.blocking ? `<span class="pill status-blocked onboarding">blocking</span>` : `<span class="pill status-running onboarding">optional</span>`;
        return `
          <div class="stage">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
              <div><strong>${escapeHtml(c.key)}</strong></div>
              ${blocking}
            </div>
            <div class="muted small" style="margin-top:6px;">${escapeHtml(c.question || "")}</div>
            ${recommended ? `<pre class="muted small" style="margin-top:6px; white-space:pre-wrap;">Recommended: ${escapeHtml(recommended)}</pre>` : ""}
            <textarea class="clar-answer" data-clar-key="${escapeHtml(c.key)}" placeholder='{"value": "..."} (JSON or plain text)'></textarea>
            <div style="display:flex; justify-content:flex-end; gap:6px; margin-top:6px;">
              <button class="tiny-btn" type="button" data-clar-save="${escapeHtml(c.key)}">Save answer</button>
            </div>
          </div>
        `;
      })
      .join("");
    return `<div class="stage-list">${cards}</div>`;
  })();
  container.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
      <div>
        <div class="muted small">Workspace</div>
        <div>${summary.workspace_path || "-"}</div>
        <div class="muted small">Last: ${lastMsg || "-"} ${lastTime ? `(${lastTime})` : ""}</div>
        ${hint}
      </div>
      <span class="pill ${statusClass(summary.status)} onboarding">${summary.status}</span>
    </div>
    <div style="margin-top:10px;">
      <h4 style="margin:0 0 6px 0;">Clarifications</h4>
      ${clarHtml}
    </div>
    <div class="stage-list">${stages || `<div class="muted small">No stages yet.</div>`}</div>
    <div class="timeline">
      <table>
        <thead><tr><th>Time</th><th>Event</th><th>Message</th></tr></thead>
        <tbody>${events || `<tr><td colspan="3" class="muted small">No events yet.</td></tr>`}</tbody>
      </table>
    </div>
  `;

  container.querySelectorAll("button[data-clar-save]").forEach((btn) => {
    btn.onclick = async (e) => {
      const key = e.currentTarget.getAttribute("data-clar-save");
      if (!key || !state.selectedProject) return;
      const textarea = container.querySelector(`textarea[data-clar-key=\"${CSS.escape(key)}\"]`);
      const raw = textarea ? textarea.value.trim() : "";
      let answer = null;
      if (raw) {
        const parsed = parseJsonField(raw);
        answer = parsed || raw;
      }
      try {
        await apiFetch(`/projects/${state.selectedProject}/clarifications/${encodeURIComponent(key)}`, {
          method: "POST",
          body: JSON.stringify({ answer }),
          projectId: state.selectedProject,
        });
        setStatus(`Saved answer for ${key}.`, "toast");
        await loadProjectClarifications(state.selectedProject);
        renderOnboardingDetail();
      } catch (err) {
        setStatus(err.message, "error");
      }
    };
  });
}

function renderStepsTable() {
  if (!state.steps.length) {
    return `<p class="muted">No steps recorded for this run.</p>`;
  }
  const rows = state.steps
    .map(
      (s) => `
        <tr>
          <td>${s.step_index}</td>
          <td>${s.step_name}</td>
          <td><span class="pill ${statusClass(s.status)}">${s.status}</span></td>
          <td class="muted">${s.model || "-"}</td>
          <td class="muted">${s.engine_id || "-"}</td>
          <td class="muted">${policyLabel(s.policy)}</td>
          <td class="muted">${runtimeStateLabel(s.runtime_state)}</td>
          <td class="muted">${s.summary || "-"}</td>
          <td><button class="tiny-btn" type="button" data-step-runs="${s.id}">Runs</button></td>
          <td><button class="tiny-btn" type="button" data-step-policy="${s.id}">Policy</button></td>
        </tr>
      `
    )
    .join("");
  return `
    <table class="table">
      <thead>
        <tr><th>#</th><th>Name</th><th>Status</th><th>Model</th><th>Engine</th><th>Policy</th><th>State</th><th>Summary</th><th>Runs</th><th>Policy</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function policyLabel(policy) {
  if (!policy) return "-";
  if (Array.isArray(policy) && policy.length) {
    return policy.map((p) => policyLabel(p)).join(" / ");
  }
  const parts = [];
  if (policy.behavior) parts.push(policy.behavior);
  if (policy.action) parts.push(policy.action);
  if (policy.trigger_agent_id) parts.push(`→${policy.trigger_agent_id}`);
  if (policy.max_iterations) parts.push(`max:${policy.max_iterations}`);
  return parts.join(" ");
}

function runtimeStateLabel(state) {
  if (!state) return "-";
  const parts = [];
  const loops = state.loop_counts || state.loopCounts;
  if (loops && typeof loops === "object") {
    const loopBits = Object.entries(loops).map(([k, v]) => `${k}:${v}`);
    if (loopBits.length) parts.push(`loops(${loopBits.join(",")})`);
  }
  if (state.last_triggered_by) parts.push(`triggered_by:${state.last_triggered_by}`);
  if (state.last_target_step_index !== undefined) parts.push(`target:${state.last_target_step_index}`);
  return parts.join(" ") || "-";
}

function eventTypeClass(eventType) {
  const important = [
    "loop_decision",
    "loop_limit_reached",
    "loop_condition_skipped",
    "trigger_decision",
    "trigger_enqueued",
    "trigger_executed_inline",
    "trigger_inline_depth_exceeded",
    "trigger_enqueue_failed",
    "trigger_condition_skipped",
    "trigger_missing_target",
  ];
  if (important.includes(eventType)) return "warn";
  return "";
}

function filteredEvents() {
  const filter = state.eventFilter || "all";
  if (filter === "loop") {
    return state.events.filter((e) => e.event_type && e.event_type.startsWith("loop_"));
  }
  if (filter === "trigger") {
    return state.events.filter((e) => e.event_type && e.event_type.startsWith("trigger_"));
  }
  if (filter === "policy") {
    return state.events.filter(
      (e) => e.event_type === "policy_findings" || e.event_type === "policy_autofix" || e.event_type === "policy_blocked"
    );
  }
  const specFilter = (state.eventSpecFilter || "").trim().toLowerCase();
  const events = state.events;
  if (!specFilter) return events;
  return events.filter((e) => {
    const meta = e.metadata || {};
    const specHash = (meta.spec_hash || meta.specHash || "").toLowerCase();
    return specHash.includes(specFilter);
  });
}

function eventSummaryLabel() {
  const total = state.events.length;
  const loops = state.events.filter((e) => e.event_type && e.event_type.startsWith("loop_")).length;
  const triggers = state.events.filter((e) => e.event_type && e.event_type.startsWith("trigger_")).length;
  const policy = state.events.filter(
    (e) => e.event_type === "policy_findings" || e.event_type === "policy_autofix" || e.event_type === "policy_blocked"
  ).length;
  const parts = [`${total} total`, `loop:${loops}`, `trigger:${triggers}`, `policy:${policy}`];
  return parts.join(" · ");
}

function eventMetaSnippet(event) {
  const meta = event.metadata || {};
  const parts = [];
  if (event.event_type === "loop_decision" || event.event_type === "loop_limit_reached") {
    if (meta.target_step_index !== undefined) parts.push(`target:${meta.target_step_index}`);
    if (meta.iterations !== undefined) {
      const max = meta.max_iterations !== undefined ? `/${meta.max_iterations}` : "";
      parts.push(`iter:${meta.iterations}${max}`);
    }
    if (Array.isArray(meta.steps_reset)) parts.push(`reset:${meta.steps_reset.length}`);
  }
  if (event.event_type.startsWith("trigger_")) {
    if (meta.target_step_index !== undefined) parts.push(`target:${meta.target_step_index}`);
    if (meta.target_step_id !== undefined) parts.push(`id:${meta.target_step_id}`);
    if (meta.source) parts.push(`source:${meta.source}`);
    if (meta.reason) parts.push(`reason:${meta.reason}`);
    if (meta.policy && meta.policy.module_id) parts.push(`policy:${meta.policy.module_id}`);
  }
  return parts.join(" · ");
}

function renderEventsList() {
  const events = filteredEvents();
  if (!events.length) {
    return `<p class="muted">Events will appear as jobs run.</p>`;
  }
  return events
    .map(
      (e) => {
        const meta = e.metadata || {};
        const promptVersions = meta.prompt_versions || meta.promptVersions;
        const promptLine = promptVersions
          ? Object.entries(promptVersions)
              .map(([k, v]) => `${k}:${v}`)
              .join(" · ")
          : null;
        const modelLine = meta.model ? `model:${meta.model}` : null;
        const specLine = meta.spec_hash ? `spec:${meta.spec_hash}` : null;
        const extraLine = [promptLine, modelLine, specLine].filter(Boolean).join(" | ");
        const metaSnippet = eventMetaSnippet(e);
        return `
        <div class="event">
          <div style="display:flex; justify-content:space-between;">
            <span class="pill ${eventTypeClass(e.event_type)}">${e.event_type}</span>
            <span class="muted">${formatDate(e.created_at)}</span>
          </div>
          <div>${e.message}</div>
          ${extraLine ? `<div class="muted" style="font-size:12px;">${extraLine}</div>` : ""}
          ${metaSnippet ? `<div class="muted" style="font-size:12px;">${metaSnippet}</div>` : ""}
          ${e.metadata ? `<div class="muted" style="font-size:12px;">${JSON.stringify(e.metadata)}</div>` : ""}
        </div>
      `;
      }
    )
    .join("");
}

function renderCiHints(run) {
  const base = (state.apiBase || window.location.origin || "").replace(/\/$/, "");
  const githubUrl = `${base}/webhooks/github`;
  const gitlabUrl = `${base}/webhooks/gitlab`;
  return `
    <div class="pane">
      <div class="pane-heading">
        <h3>CI & Webhooks</h3>
        <span class="pill">${run.protocol_name}</span>
      </div>
      <p class="muted small">Report CI status from your pipeline or post a webhook manually.</p>
      <div class="code-block">TASKSGODZILLA_API_BASE=${base || "http://localhost:8011"}
scripts/ci/report.sh success
# on failure
scripts/ci/report.sh failure</div>
      <div class="muted small">GitHub: POST ${githubUrl} (X-GitHub-Event: status) · GitLab: POST ${gitlabUrl} (X-Gitlab-Event: Pipeline Hook)</div>
    </div>
  `;
}

async function loadSteps() {
  if (!state.selectedProtocol) return;
  try {
    const steps = await apiFetch(`/protocols/${state.selectedProtocol}/steps`);
    state.steps = steps;
    renderProtocolDetail();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadEvents() {
  if (!state.selectedProtocol) return;
  try {
    const events = await apiFetch(`/protocols/${state.selectedProtocol}/events`);
    state.events = events;
    renderProtocolDetail();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function loadQueue() {
  try {
    const stats = await apiFetch("/queues");
    const jobs = await apiFetch("/queues/jobs");
    state.queueStats = stats;
    state.queueJobs = jobs;
    renderQueue();
  } catch (err) {
    state.queueStats = null;
    state.queueJobs = [];
    renderQueue();
    setStatus(err.message, "error");
  }
}

async function loadMetrics() {
  try {
    const text = await apiFetch("/metrics");
    const qaVerdicts = {};
    const tokenUsageByPhase = {};
    const tokenUsageByModel = {};
    text
      .split("\n")
      .forEach((line) => {
        if (line.startsWith("qa_verdict_total")) {
          const match = line.match(/verdict="([^"]+)".*\s(\d+(?:\.\d+)?)/);
          if (match) {
            qaVerdicts[match[1]] = parseFloat(match[2]);
          }
        }
        if (line.startsWith("codex_token_estimated_total")) {
          const match = line.match(/phase="([^"]+)",model="([^"]+)".*\s(\d+(?:\.\d+)?)/);
          if (match) {
            const phase = match[1];
            const value = parseFloat(match[3]);
            tokenUsageByPhase[phase] = (tokenUsageByPhase[phase] || 0) + value;
            if (!tokenUsageByModel[phase]) tokenUsageByModel[phase] = {};
            tokenUsageByModel[phase][match[2]] = (tokenUsageByModel[phase][match[2]] || 0) + value;
          }
        }
      });
    state.metrics = { qaVerdicts, tokenUsageByPhase, tokenUsageByModel };
    renderMetrics();
  } catch (err) {
    state.metrics = { qaVerdicts: {}, tokenUsageByPhase: {}, tokenUsageByModel: {} };
    renderMetrics();
    setStatus(err.message, "error");
  }
}

function renderQueue() {
  const statsEl = document.getElementById("queueStats");
  const jobsEl = document.getElementById("queueJobs");
  if (!statsEl || !jobsEl) return;
  if (!state.queueStats) {
    statsEl.innerHTML = `<p class="muted">Queue stats will appear after loading.</p>`;
    jobsEl.innerHTML = `<p class="muted">No jobs loaded.</p>`;
    return;
  }
  const { backend, ...queues } = state.queueStats;
  const queueRows = Object.entries(queues)
    .map(
      ([name, data]) => `
        <div class="event">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="pill">${name}</span>
            <span class="muted" style="font-size:12px;">${backend || ""}</span>
          </div>
          <div class="muted" style="font-size:12px;">queued ${data.queued} · started ${data.started} · finished ${data.finished} · failed ${data.failed}</div>
        </div>
      `
    )
    .join("");
  statsEl.innerHTML = queueRows || `<p class="muted">No queues reported.</p>`;

  const jobs = (state.queueJobs || []).slice(0, 6);
  jobsEl.innerHTML = jobs.length
    ? jobs
        .map(
          (job) => `
            <div class="event">
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <span class="pill">${job.job_type}</span>
                <span class="pill ${statusClass(job.status)}">${job.status}</span>
              </div>
              <div class="muted" style="font-size:12px;">${job.job_id}</div>
              <div class="muted" style="font-size:12px;">attempt ${job.meta && job.meta.tgz_attempt ? job.meta.tgz_attempt : "-"}</div>
            </div>
          `
        )
        .join("")
    : `<p class="muted">No jobs yet.</p>`;
}

function renderSparkline(values, dataset) {
  const series = Array.isArray(values) ? values : Object.values(values || {});
  const scale = dataset ? Object.values(dataset) : series;
  if (!series.length || !scale.length) return "";
  const max = Math.max(...scale);
  if (max <= 0) return "";
  const blocks = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"];
  const bars = series
    .map((v) => {
      const idx = Math.min(blocks.length - 1, Math.floor((v / max) * (blocks.length - 1)));
      return blocks[idx];
    })
    .join("");
  return `<div class="muted small" aria-label="sparkline">${bars}</div>`;
}

function renderBar(value, max, label) {
  if (!max || max <= 0) return "";
  const pct = Math.min(100, Math.round((value / max) * 100));
  return `
    <div class="bar-track" aria-label="${label} ${pct}%">
      <div class="bar-fill" style="width:${pct}%;"></div>
      <span class="bar-label">${pct}%</span>
    </div>
  `;
}

function estimateCost(modelTokens) {
  const perModel = modelTokens || {};
  let total = 0;
  const unknown = [];
  Object.entries(perModel).forEach(([model, tokens]) => {
    const price = MODEL_PRICING[model];
    if (price === undefined) {
      unknown.push(model);
      return;
    }
    total += (tokens / 1000) * price;
  });
  return { total, unknown };
}

function renderMetrics() {
  const target = document.getElementById("metricsSummary");
  if (!target) return;
  const qaVerdicts = state.metrics.qaVerdicts || {};
  const verdictKeys = Object.keys(qaVerdicts);
  const passCount = qaVerdicts.pass || qaVerdicts.PASS || 0;
  const failCount = qaVerdicts.fail || qaVerdicts.FAIL || 0;
  const totalQa = passCount + failCount;
  const passRate = totalQa ? Math.round((passCount / totalQa) * 100) : null;

  const qaRows = verdictKeys.length
    ? verdictKeys
        .map(
          (key) => `
        <div class="event">
          <div style="display:flex; justify-content:space-between;">
            <span class="pill">${key}</span>
            <span class="muted">${qaVerdicts[key]}</span>
          </div>
          ${renderBar(qaVerdicts[key], totalQa, "qa")}
        </div>
      `
        )
        .join("")
    : `<p class="muted">QA metrics not yet available. Trigger QA to see verdict counts.</p>`;

  const tokenUsage = state.metrics.tokenUsageByPhase || {};
  const tokenModels = state.metrics.tokenUsageByModel || {};
  const tokenRows = Object.keys(tokenUsage).length
    ? Object.entries(tokenUsage)
        .map(([phase, value]) => {
          const costInfo = estimateCost(tokenModels[phase] || {});
          return `
        <div class="event">
          <div style="display:flex; justify-content:space-between;">
            <span class="pill">${phase}</span>
            <span class="muted">${Math.round(value)} tok${costInfo.total > 0 ? ` · ~$${costInfo.total.toFixed(2)}` : ""}</span>
          </div>
          ${renderBar(value, Math.max(...Object.values(tokenUsage)), "tokens")}
          ${costInfo.unknown.length ? `<div class="muted small">Unknown pricing for: ${costInfo.unknown.join(", ")}</div>` : ""}
        </div>
      `;
        })
        .join("")
    : `<p class="muted">Token usage metrics not yet available.</p>`;

  target.innerHTML = `
    <div>
      <div class="pane-heading" style="display:flex; justify-content:space-between; align-items:center;">
        <h4>QA verdicts</h4>
        <span class="muted small">/metrics</span>
      </div>
      ${passRate !== null ? `<div class="muted small">Pass rate: ${passRate}% (${passCount}/${totalQa})</div>` : ""}
      ${qaRows}
      <div class="pane-heading" style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
        <h4>Token usage (estimated)</h4>
      </div>
      ${tokenRows}
    </div>
  `;
}

async function loadOperations() {
  const target = document.getElementById("operationsList");
  if (!target) return;
  try {
    const params = [];
    if (state.selectedProject) {
      params.push(`project_id=${state.selectedProject}`);
    }
    params.push("limit=50");
    const qs = params.length ? `?${params.join("&")}` : "";
    const events = await apiFetch(`/events${qs}`);
    state.operations = events;
    renderOperations();
    renderAuditHistory();
  } catch (err) {
    state.operations = [];
    renderOperations();
    renderAuditHistory();
    setStatus(err.message, "error");
  }
}

function renderOperations() {
  const target = document.getElementById("operationsList");
  if (!target) return;
  if (!state.operations.length) {
    target.innerHTML = `<p class="muted">Recent events will appear here.</p>`;
    return;
  }
  const toggle = `
    <div style="display:flex; justify-content:flex-end; align-items:center; gap:8px; margin-bottom:6px;">
      <label class="muted small" style="display:flex; align-items:center; gap:6px;">
        <input type="checkbox" id="opsInvalidOnly" ${state.operationsInvalidOnly ? "checked" : ""} />
        invalid specs only
      </label>
      <input id="opsSpecFilter" class="input-inline" placeholder="spec hash" value="${state.operationsSpecFilter || ""}" />
    </div>
  `;
  const filteredOps = state.operations.filter((e) => {
    if (!state.operationsInvalidOnly) return true;
    const meta = e.metadata || {};
    const status = meta.spec_status || meta.specStatus || null;
    if (status) return status === "invalid";
    const hash = meta.spec_hash || null;
    return Boolean(hash);
  });
  const specFilter = (state.operationsSpecFilter || "").trim().toLowerCase();
  const filteredBySpec = specFilter
    ? filteredOps.filter((e) => {
        const meta = e.metadata || {};
        const specHash = (meta.spec_hash || meta.specHash || "").toLowerCase();
        return specHash.includes(specFilter);
      })
    : filteredOps;
  target.innerHTML =
    toggle +
    filteredBySpec
      .slice(0, 40)
      .map((e) => {
        const meta = e.metadata || {};
        const specHash = meta.spec_hash || (meta.outputs && meta.outputs.spec_hash);
        const specStatus = meta.spec_status || meta.specStatus || "unknown";
        const contextBits = [
          e.project_name || e.project_id || "",
          e.protocol_name || "",
          e.step_run_id ? `step ${e.step_run_id}` : "",
        ]
          .filter(Boolean)
          .join(" · ");
        const specClass = specStatus === "valid" ? "spec-valid" : specStatus === "invalid" ? "spec-invalid" : "spec-unknown";
        const specPill = specHash ? `<span class="pill ${specClass}" style="margin-right:6px;">spec ${specHash}</span>` : "";
        return `
          <div class="event">
            <div style="display:flex; justify-content:space-between;">
              <span class="pill">${e.event_type}</span>
              <span class="muted">${formatDate(e.created_at)}</span>
            </div>
            <div>${specPill}${e.message}</div>
            ${contextBits ? `<div class="muted small">${contextBits}</div>` : ""}
            ${e.metadata ? `<div class="muted" style="font-size:12px;">${JSON.stringify(e.metadata)}</div>` : ""}
          </div>
        `;
      })
      .join("");
  const toggleEl = document.getElementById("opsInvalidOnly");
  if (toggleEl) {
    toggleEl.onchange = (e) => {
      state.operationsInvalidOnly = e.target.checked;
      renderOperations();
    };
  }
  const specInput = document.getElementById("opsSpecFilter");
  if (specInput) {
    specInput.oninput = (e) => {
      state.operationsSpecFilter = e.target.value;
      renderOperations();
    };
  }
}

function renderAuditHistory() {
  const target = document.getElementById("auditHistory");
  if (!target) return;
  const audits = (state.operations || []).filter((e) => e.event_type === "spec_audit").filter((e) => {
    if (state.selectedProject) {
      return e.project_id === state.selectedProject;
    }
    return true;
  });
  if (!audits.length) {
    target.innerHTML = `<p class="muted">No spec audit events yet.</p>`;
    return;
  }
  target.innerHTML = audits
    .slice(0, 20)
    .map((ev) => {
      const meta = ev.metadata || {};
      const errors = meta.errors || [];
      const proj = ev.project_name || meta.project_name || "";
      const proto = ev.protocol_name || meta.protocol_name || "";
      const status = errors.length ? "spec-invalid" : "spec-valid";
      const backfilled = meta.backfilled ? "backfilled" : "checked";
      return `
        <div class="event">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <strong>${proto || ev.protocol_run_id || ""}</strong>
              <span class="muted small">${proj}</span>
            </div>
            <span class="pill ${status}">${backfilled}</span>
          </div>
          <div class="muted small">${formatDate(ev.created_at)}</div>
          ${errors.length ? `<div class="muted small">errors: ${errors.join(", ")}</div>` : ""}
        </div>
      `;
    })
    .join("");
}

function startPolling() {
  if (state.poll) {
    clearInterval(state.poll);
  }
  state.poll = setInterval(() => {
    loadSteps();
    loadEvents();
    loadRuns();
    loadOperations();
    loadMetrics();
    loadOnboarding();
  }, 4000);
}

function bindEventFilters() {
  document.querySelectorAll(".button-group button[data-filter]").forEach((btn) => {
    btn.onclick = () => {
      state.eventFilter = btn.getAttribute("data-filter");
      renderProtocolDetail();
    };
  });
  const specInput = document.getElementById("specFilterInput");
  if (specInput) {
    specInput.oninput = (e) => {
      state.eventSpecFilter = e.target.value;
      renderProtocolDetail();
    };
  }
}

async function startProtocol(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/start`, { method: "POST" });
    setStatus("Planning enqueued.");
    loadEvents();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function pauseProtocol(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/pause`, { method: "POST" });
    setStatus("Protocol paused.");
    loadProtocols();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function resumeProtocol(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/resume`, { method: "POST" });
    setStatus("Protocol resumed.");
    loadProtocols();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function cancelProtocol(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/cancel`, { method: "POST" });
    setStatus("Protocol cancelled.");
    loadProtocols();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function runNextStep(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/run_next_step`, { method: "POST" });
    setStatus("Next step enqueued.");
    loadEvents();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function retryLatest(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/retry_latest`, { method: "POST" });
    setStatus("Retry enqueued.");
    loadEvents();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function runQaLatest() {
  if (!state.steps.length) {
    setStatus("No steps to QA.", "error");
    return;
  }
  const latest = state.steps[state.steps.length - 1];
  try {
    await apiFetch(`/steps/${latest.id}/actions/run_qa`, { method: "POST" });
    setStatus(`QA enqueued for ${latest.step_name}.`);
    loadEvents();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function approveLatest() {
  if (!state.steps.length) {
    setStatus("No steps to approve.", "error");
    return;
  }
  const latest = state.steps[state.steps.length - 1];
  try {
    await apiFetch(`/steps/${latest.id}/actions/approve`, { method: "POST" });
    setStatus(`Step ${latest.step_name} approved.`);
    loadSteps();
    loadEvents();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

async function openPr(runId) {
  try {
    await apiFetch(`/protocols/${runId}/actions/open_pr`, { method: "POST" });
    setStatus("PR/MR job enqueued.");
    loadEvents();
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function wireForms() {
  document.getElementById("saveAuth").onclick = () => {
    state.apiBase = apiBaseInput.value.trim();
    state.token = apiTokenInput.value.trim();
    persistAuth();
  };

  document.getElementById("refreshProjects").onclick = loadProjects;
  document.getElementById("refreshProtocols").onclick = loadProtocols;
  const refreshQueueBtn = document.getElementById("refreshQueue");
  if (refreshQueueBtn) {
    refreshQueueBtn.onclick = loadQueue;
  }
  const refreshOpsBtn = document.getElementById("refreshOperations");
  if (refreshOpsBtn) {
    refreshOpsBtn.onclick = loadOperations;
  }
  const specAuditBtn = document.getElementById("runSpecAudit");
  if (specAuditBtn) {
    specAuditBtn.onclick = () => enqueueSpecAudit(state.selectedProject);
  }
  const refreshAuditsBtn = document.getElementById("refreshAudits");
  if (refreshAuditsBtn) {
    refreshAuditsBtn.onclick = loadOperations;
  }
  const refreshMetricsBtn = document.getElementById("refreshMetrics");
  if (refreshMetricsBtn) {
    refreshMetricsBtn.onclick = loadMetrics;
  }
  const refreshOnboardingBtn = document.getElementById("refreshOnboarding");
  if (refreshOnboardingBtn) {
    refreshOnboardingBtn.onclick = () => loadOnboarding();
  }
  const refreshPolicyBtn = document.getElementById("refreshPolicy");
  if (refreshPolicyBtn) {
    refreshPolicyBtn.onclick = async () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      await loadPolicyPacks();
      await loadProjectPolicy();
      await loadPolicyFindings();
      renderPolicyPanel();
    };
  }
  const previewPolicyBtn = document.getElementById("previewPolicy");
  if (previewPolicyBtn) {
    previewPolicyBtn.onclick = async () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      await loadEffectivePolicy();
      await loadPolicyFindings();
      setStatus("Effective policy loaded.", "toast");
    };
  }
  const savePolicyBtn = document.getElementById("savePolicy");
  if (savePolicyBtn) {
    savePolicyBtn.onclick = async () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      const select = document.getElementById("policyPackKey");
      const versionModeEl = document.getElementById("policyPackVersionMode");
      const versionSelectEl = document.getElementById("policyPackVersionSelect");
      const versionInput = document.getElementById("policyPackVersion");
      const overridesEl = document.getElementById("policyOverrides");
      const repoLocalEl = document.getElementById("policyRepoLocalEnabled");
      const enforcementEl = document.getElementById("policyEnforcementMode");
      const overrides = parseJsonField(overridesEl?.value || "");
      if ((overridesEl?.value || "").trim() && !overrides) {
        setStatus("Overrides must be valid JSON (or empty).", "error");
        return;
      }
      const versionMode = (versionModeEl?.value || "latest").toLowerCase();
      let pinnedVersion = (versionInput?.value || "").trim();
      if (!pinnedVersion && versionSelectEl && versionSelectEl.value) {
        pinnedVersion = String(versionSelectEl.value).trim();
      }
      if (versionMode === "pin" && !pinnedVersion) {
        setStatus("Select or enter a version to pin (or choose latest).", "error");
        return;
      }
      const payload = {
        policy_pack_key: select?.value || null,
        policy_pack_version: versionMode === "pin" ? pinnedVersion : null,
        clear_policy_pack_version: versionMode !== "pin",
        policy_overrides: overrides,
        policy_repo_local_enabled: Boolean(repoLocalEl?.checked),
        policy_enforcement_mode: (enforcementEl?.value || "warn").toLowerCase(),
      };
      try {
        await apiFetch(`/projects/${state.selectedProject}/policy`, {
          method: "PUT",
          body: JSON.stringify(payload),
          projectId: state.selectedProject,
        });
        // Refresh local state and project list pill/hash.
        await loadProjects();
        await loadProjectPolicy();
        state.effectivePolicy[state.selectedProject] = null;
        renderPolicyPanel();
        setStatus("Policy saved.", "toast");
      } catch (err) {
        setStatus(err.message, "error");
      }
    };
  }
  const useBeginnerBtn = document.getElementById("useBeginnerPolicy");
  if (useBeginnerBtn) {
    useBeginnerBtn.onclick = () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      const select = document.getElementById("policyPackKey");
      const versionModeEl = document.getElementById("policyPackVersionMode");
      const versionSelectEl = document.getElementById("policyPackVersionSelect");
      const versionInput = document.getElementById("policyPackVersion");
      if (select) select.value = "beginner-guided";
      if (versionModeEl) versionModeEl.value = "pin";
      if (versionSelectEl) versionSelectEl.value = "1.0";
      if (versionInput) versionInput.value = "1.0";
      renderPolicyPanel();
      setStatus("Selected beginner-guided@1.0 (not saved).", "toast");
    };
  }
  const enableRepoLocalBtn = document.getElementById("enableRepoLocalPolicy");
  if (enableRepoLocalBtn) {
    enableRepoLocalBtn.onclick = () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      const repoLocalEl = document.getElementById("policyRepoLocalEnabled");
      if (repoLocalEl) {
        repoLocalEl.checked = true;
      }
      renderPolicyPanel();
      setStatus("Repo-local override enabled (not saved).", "toast");
    };
  }
  const suggestOverridesBtn = document.getElementById("suggestPolicyOverrides");
  if (suggestOverridesBtn) {
    suggestOverridesBtn.onclick = () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      const select = document.getElementById("policyPackKey");
      const overridesEl = document.getElementById("policyOverrides");
      const packKey = (select && select.value) || "default";
      const suggested = buildSuggestedPolicyOverrides(packKey);
      if (overridesEl) {
        overridesEl.value = JSON.stringify(suggested, null, 2);
      }
      renderPolicyPanel();
      setStatus("Suggested overrides inserted (not saved).", "toast");
    };
  }
  const setWarnBtn = document.getElementById("setPolicyWarn");
  if (setWarnBtn) {
    setWarnBtn.onclick = () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      const enforcementEl = document.getElementById("policyEnforcementMode");
      if (enforcementEl) enforcementEl.value = "warn";
      renderPolicyPanel();
      setStatus("Enforcement set to warn (not saved).", "toast");
    };
  }
  const saveWarnNowBtn = document.getElementById("savePolicyWarnNow");
  if (saveWarnNowBtn) {
    saveWarnNowBtn.onclick = async () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      try {
        await apiFetch(`/projects/${state.selectedProject}/policy`, {
          method: "PUT",
          body: JSON.stringify({ policy_enforcement_mode: "warn" }),
          projectId: state.selectedProject,
        });
        await loadProjects();
        await loadProjectPolicy();
        await loadPolicyFindings();
        setStatus("Enforcement saved as warn.", "toast");
      } catch (err) {
        setStatus(err.message, "error");
      }
    };
  }

  const adminSelectEl = document.getElementById("adminPolicyPackSelect");
  const adminLoadBtn = document.getElementById("adminPolicyPackLoad");
  const adminCloneBtn = document.getElementById("adminPolicyPackClone");
  const adminNewBtn = document.getElementById("adminPolicyPackNew");
  const adminSaveBtn = document.getElementById("adminPolicyPackSave");
  const adminKeyEl = document.getElementById("adminPolicyPackKey");
  const adminVerEl = document.getElementById("adminPolicyPackVersion");
  const adminNameEl = document.getElementById("adminPolicyPackName");
  const adminDescEl = document.getElementById("adminPolicyPackDescription");
  const adminStatusEl = document.getElementById("adminPolicyPackStatus");
  const adminJsonEl = document.getElementById("adminPolicyPackJson");
  const adminResultEl = document.getElementById("adminPolicyPackResult");

  function adminSetResult(message, level = "info") {
    if (!adminResultEl) return;
    adminResultEl.textContent = message || "";
    adminResultEl.style.color = level === "error" ? "#f87171" : "#7e8ba1";
  }

  function adminLoadPack(pack) {
    if (!pack) return;
    state.adminSelectedPolicyPackId = String(pack.id);
    if (adminKeyEl) adminKeyEl.value = String(pack.key || "");
    if (adminVerEl) adminVerEl.value = String(pack.version || "");
    if (adminNameEl) adminNameEl.value = String(pack.name || "");
    if (adminDescEl) adminDescEl.value = String(pack.description || "");
    if (adminStatusEl) adminStatusEl.value = String(pack.status || "active");
    if (adminJsonEl) adminJsonEl.value = JSON.stringify(pack.pack || {}, null, 2);
    adminSetResult("");
    renderPolicyPanel();
  }

  if (adminSelectEl) {
    adminSelectEl.onchange = () => {
      state.adminSelectedPolicyPackId = adminSelectEl.value || null;
    };
  }

  if (adminLoadBtn) {
    adminLoadBtn.onclick = () => {
      if (!adminSelectEl || !adminSelectEl.value) {
        setStatus("No pack selected.", "error");
        return;
      }
      const pack = policyPackById(adminSelectEl.value);
      if (!pack) {
        setStatus("Selected pack not found.", "error");
        return;
      }
      adminLoadPack(pack);
      setStatus("Policy pack loaded into editor.", "toast");
    };
  }

  if (adminNewBtn) {
    adminNewBtn.onclick = () => {
      const key = adminKeyEl?.value?.trim() || "custom";
      const version = adminVerEl?.value?.trim() || "1.0";
      if (adminKeyEl) adminKeyEl.value = key;
      if (adminVerEl) adminVerEl.value = version;
      if (adminNameEl && !adminNameEl.value.trim()) adminNameEl.value = "Custom";
      if (adminStatusEl) adminStatusEl.value = "active";
      if (adminJsonEl) adminJsonEl.value = JSON.stringify(defaultPolicyPackTemplate(key, version, adminNameEl?.value || "Custom"), null, 2);
      adminSetResult("New template inserted (not saved).");
    };
  }

  if (adminCloneBtn) {
    adminCloneBtn.onclick = () => {
      const sourceId = adminSelectEl?.value;
      const source = sourceId ? policyPackById(sourceId) : null;
      if (!source) {
        setStatus("Select a pack to clone first.", "error");
        return;
      }
      const newKey = window.prompt("New pack key", String(source.key || "")) || "";
      const newVersion = window.prompt("New pack version", "1.0") || "";
      if (!newKey.trim() || !newVersion.trim()) {
        setStatus("Clone cancelled (missing key/version).", "error");
        return;
      }
      const packObj = (source.pack && typeof source.pack === "object") ? JSON.parse(JSON.stringify(source.pack)) : {};
      if (!packObj.meta || typeof packObj.meta !== "object") packObj.meta = {};
      packObj.meta.key = newKey.trim();
      packObj.meta.version = newVersion.trim();
      if (!packObj.meta.name) packObj.meta.name = source.name || "Custom";
      if (adminKeyEl) adminKeyEl.value = newKey.trim();
      if (adminVerEl) adminVerEl.value = newVersion.trim();
      if (adminNameEl) adminNameEl.value = String(source.name || "Custom");
      if (adminDescEl) adminDescEl.value = String(source.description || "");
      if (adminStatusEl) adminStatusEl.value = String(source.status || "active");
      if (adminJsonEl) adminJsonEl.value = JSON.stringify(packObj, null, 2);
      adminSetResult(`Cloned from ${String(source.key)}@${String(source.version)} (not saved).`);
    };
  }

  if (adminSaveBtn) {
    adminSaveBtn.onclick = async () => {
      const key = adminKeyEl?.value?.trim() || "";
      const version = adminVerEl?.value?.trim() || "";
      const name = adminNameEl?.value?.trim() || "";
      const description = adminDescEl?.value?.trim() || null;
      const status = adminStatusEl?.value || "active";
      const packObj = parseJsonField(adminJsonEl?.value || "");
      if (!key || !version || !name) {
        adminSetResult("Key, version, and name are required.", "error");
        return;
      }
      if (!packObj) {
        adminSetResult("Pack JSON must be valid JSON (non-empty).", "error");
        return;
      }
      try {
        const saved = await apiFetch("/policy_packs", {
          method: "POST",
          body: JSON.stringify({ key, version, name, description, status, pack: packObj }),
        });
        state.adminSelectedPolicyPackId = String(saved.id);
        await loadPolicyPacks();
        renderPolicyPanel();
        adminSetResult(`Saved ${saved.key}@${saved.version} (id ${saved.id}).`, "info");
        setStatus("Policy pack saved.", "toast");
      } catch (err) {
        const msg = String(err && err.message ? err.message : err);
        adminSetResult(msg, "error");
        setStatus("Policy pack save failed.", "error");
      }
    };
  }

  const startOnboardingBtn = document.getElementById("startOnboarding");
  if (startOnboardingBtn) {
    startOnboardingBtn.onclick = () => startOnboarding(false);
  }
  const runOnboardingInlineBtn = document.getElementById("runOnboardingInline");
  if (runOnboardingInlineBtn) {
    runOnboardingInlineBtn.onclick = () => startOnboarding(true);
  }
  if (saveProjectTokenBtn) {
    saveProjectTokenBtn.onclick = () => {
      if (!state.selectedProject) {
        setStatus("Select a project first.", "error");
        return;
      }
      const token = projectTokenInput.value.trim();
      const key = String(state.selectedProject);
      if (token) {
        state.projectTokens[key] = token;
      } else {
        delete state.projectTokens[key];
      }
      persistProjectTokens();
      setStatus(token ? "Project token saved." : "Project token cleared.");
    };
  }

  document.getElementById("projectForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
      name: form.name.value,
      git_url: form.git_url.value,
      base_branch: form.base_branch.value || "main",
      ci_provider: form.ci_provider.value || null,
      project_classification: form.project_classification?.value || null,
      default_models: parseJsonField(form.default_models.value),
    };
    try {
      await apiFetch("/projects", { method: "POST", body: JSON.stringify(payload) });
      setStatus("Project created and setup enqueued.");
      form.reset();
      loadProjects();
    } catch (err) {
      setStatus(err.message, "error");
    }
  });

  document.getElementById("protocolForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!state.selectedProject) {
      setStatus("Select a project first.", "error");
      return;
    }
    const form = e.target;
    const payload = {
      protocol_name: form.protocol_name.value,
      status: "planning",
      base_branch: form.base_branch.value || "main",
      worktree_path: null,
      protocol_root: null,
      description: form.description.value,
    };
    try {
      const run = await apiFetch(`/projects/${state.selectedProject}/protocols`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await apiFetch(`/protocols/${run.id}/actions/start`, { method: "POST" });
      setStatus("Protocol created; planning enqueued.");
      form.reset();
      loadProtocols();
    } catch (err) {
      setStatus(err.message, "error");
    }
  });
}

function parseJsonField(value) {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function formatDate(dateString) {
  if (!dateString) return "";
  const d = new Date(dateString);
  if (Number.isNaN(d.getTime())) return dateString;
  return d.toLocaleString();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function extractRequiredChecks(policyObj) {
  if (!policyObj || typeof policyObj !== "object") return [];
  const defaults = policyObj.defaults && typeof policyObj.defaults === "object" ? policyObj.defaults : {};
  const ci = defaults.ci && typeof defaults.ci === "object" ? defaults.ci : {};
  const checks = Array.isArray(ci.required_checks) ? ci.required_checks : [];
  return checks.map((c) => String(c)).filter((c) => c.trim());
}

function packsForKey(key) {
  const k = String(key || "").trim();
  return (state.policyPacks || [])
    .filter((p) => p && p.key === k)
    .sort((a, b) => {
      const aTs = a.created_at ? new Date(a.created_at).getTime() : 0;
      const bTs = b.created_at ? new Date(b.created_at).getTime() : 0;
      return bTs - aTs;
    });
}

function latestPackForKey(key) {
  const packs = packsForKey(key);
  return packs.length ? packs[0] : null;
}

function buildSuggestedPolicyOverrides(packKey) {
  // Keep these suggestions minimal and project-focused.
  const base = {
    defaults: {
      models: {
        planning: "zai-coding-plan/glm-4.6",
        exec: "zai-coding-plan/glm-4.6",
        qa: "zai-coding-plan/glm-4.6",
      },
    },
  };
  if (packKey === "startup-fast") {
    return {
      ...base,
      defaults: {
        ...base.defaults,
        qa: { policy: "full" },
      },
    };
  }
  if (packKey === "beginner-guided") {
    return {
      ...base,
      defaults: {
        ...base.defaults,
        qa: { policy: "light" },
      },
    };
  }
  return base;
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    setStatus("Copied to clipboard.", "toast");
  } catch (err) {
    setStatus("Copy failed", "error");
  }
}

function init() {
  apiBaseInput.value = state.apiBase;
  apiTokenInput.value = state.token;
  renderQueue();
  renderOperations();
   renderAuditHistory();
  renderMetrics();
  renderPolicyPanel();
  wireForms();
  if (state.token) {
    setStatus("Using saved token.");
    loadProjects();
    loadPolicyPacks();
    loadOperations();
    loadQueue();
    loadMetrics();
  } else {
    setStatus("Add a bearer token to start.");
  }
}

document.addEventListener("DOMContentLoaded", init);
