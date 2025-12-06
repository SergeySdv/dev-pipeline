const state = {
  token: localStorage.getItem("df_token") || "",
  apiBase: localStorage.getItem("df_api_base") || "",
  projects: [],
  protocols: [],
  steps: [],
  events: [],
  selectedProject: null,
  selectedProtocol: null,
  poll: null,
};

const statusEl = document.getElementById("authStatus");
const apiBaseInput = document.getElementById("apiBase");
const apiTokenInput = document.getElementById("apiToken");

function setStatus(message, level = "info") {
  if (!statusEl) return;
  statusEl.textContent = message;
  statusEl.style.color = level === "error" ? "#f87171" : "#7e8ba1";
}

function apiPath(path) {
  const base = state.apiBase || "";
  const baseTrimmed = base.endsWith("/") ? base.slice(0, -1) : base;
  return `${baseTrimmed}${path}`;
}

function statusClass(status) {
  return `status-${(status || "").toLowerCase()}`;
}

async function apiFetch(path, options = {}) {
  const headers = options.headers || {};
  if (state.token) {
    headers["Authorization"] = `Bearer ${state.token}`;
  }
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const resp = await fetch(apiPath(path), { ...options, headers });
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
  localStorage.setItem("df_token", state.token);
  localStorage.setItem("df_api_base", state.apiBase);
  apiBaseInput.value = state.apiBase;
  apiTokenInput.value = state.token;
  setStatus("Auth saved. Loading data...");
  loadProjects();
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

function renderProjects() {
  const container = document.getElementById("projectList");
  container.innerHTML = "";
  state.projects.forEach((proj) => {
    const card = document.createElement("div");
    card.className = `card ${state.selectedProject === proj.id ? "active" : ""}`;
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div>${proj.name}</div>
          <div class="muted" style="font-size:12px;">${proj.git_url}</div>
        </div>
        <span class="pill">${proj.base_branch}</span>
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
      renderProjects();
      loadProtocols();
    };
    container.appendChild(card);
  });
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
    setStatus(`Loaded ${runs.length} protocol run(s).`);
  } catch (err) {
    setStatus(err.message, "error");
  }
}

function renderProtocols() {
  const list = document.getElementById("protocolList");
  list.innerHTML = "";
  if (!state.protocols.length) {
    list.innerHTML = `<p class="muted">No protocol runs yet.</p>`;
  } else {
    const table = document.createElement("table");
    table.className = "table";
    table.innerHTML = `
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody></tbody>
    `;
    const body = table.querySelector("tbody");
    state.protocols.forEach((run) => {
      const row = document.createElement("tr");
      row.style.cursor = "pointer";
      row.innerHTML = `
        <td>${run.protocol_name}</td>
        <td><span class="pill ${statusClass(run.status)}">${run.status}</span></td>
        <td class="muted">${formatDate(run.updated_at)}</td>
      `;
      row.onclick = () => {
        state.selectedProtocol = run.id;
        renderProtocols();
        loadSteps();
        loadEvents();
        startPolling();
      };
      if (state.selectedProtocol === run.id) {
        row.style.background = "rgba(96,165,250,0.08)";
      }
      body.appendChild(row);
    });
    list.appendChild(table);
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
  container.innerHTML = `
    <div class="pane">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <div style="font-weight:700;">${run.protocol_name}</div>
          <div class="muted">${run.description || ""}</div>
        </div>
        <span class="pill ${statusClass(run.status)}">${run.status}</span>
      </div>
      <div class="actions">
        <button id="startRun" class="primary">Start planning</button>
        <button id="runNext">Run next step</button>
        <button id="retryStep">Retry failed step</button>
        <button id="runQa">Run QA on latest</button>
        <button id="openPr">Open PR/MR now</button>
        <button id="pauseRun">Pause</button>
        <button id="resumeRun">Resume</button>
        <button id="cancelRun" class="danger">Cancel</button>
        <button id="refreshActive">Refresh</button>
      </div>
    </div>
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
          <h3>Events</h3>
          <span class="muted">${state.events.length} event(s)</span>
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
  document.getElementById("openPr").onclick = () => openPr(run.id);
  document.getElementById("refreshActive").onclick = () => {
    loadSteps();
    loadEvents();
  };

  const startBtn = document.getElementById("startRun");
  const pauseBtn = document.getElementById("pauseRun");
  const resumeBtn = document.getElementById("resumeRun");
  const cancelBtn = document.getElementById("cancelRun");
  const runNextBtn = document.getElementById("runNext");
  const retryBtn = document.getElementById("retryStep");
  const qaBtn = document.getElementById("runQa");

  const terminal = ["completed", "cancelled", "failed"].includes(run.status);
  startBtn.disabled = !["pending", "planned"].includes(run.status);
  pauseBtn.disabled = !["running", "planning"].includes(run.status);
  resumeBtn.disabled = run.status !== "paused";
  cancelBtn.disabled = terminal;

  runNextBtn.disabled = terminal || run.status === "paused";
  retryBtn.disabled = terminal || run.status === "paused";
  qaBtn.disabled = terminal || run.status === "paused" || !latestStep;
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
          <td class="muted">${s.summary || "-"}</td>
        </tr>
      `
    )
    .join("");
  return `
    <table class="table">
      <thead>
        <tr><th>#</th><th>Name</th><th>Status</th><th>Model</th><th>Summary</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderEventsList() {
  if (!state.events.length) {
    return `<p class="muted">Events will appear as jobs run.</p>`;
  }
  return state.events
    .map(
      (e) => `
        <div class="event">
          <div style="display:flex; justify-content:space-between;">
            <span class="pill">${e.event_type}</span>
            <span class="muted">${formatDate(e.created_at)}</span>
          </div>
          <div>${e.message}</div>
          ${e.metadata ? `<div class="muted" style="font-size:12px;">${JSON.stringify(e.metadata)}</div>` : ""}
        </div>
      `
    )
    .join("");
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

function startPolling() {
  if (state.poll) {
    clearInterval(state.poll);
  }
  state.poll = setInterval(() => {
    loadSteps();
    loadEvents();
  }, 4000);
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

  document.getElementById("projectForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
      name: form.name.value,
      git_url: form.git_url.value,
      base_branch: form.base_branch.value || "main",
      ci_provider: form.ci_provider.value || null,
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

function init() {
  apiBaseInput.value = state.apiBase;
  apiTokenInput.value = state.token;
  wireForms();
  if (state.token) {
    setStatus("Using saved token.");
    loadProjects();
  } else {
    setStatus("Add a bearer token to start.");
  }
}

document.addEventListener("DOMContentLoaded", init);
