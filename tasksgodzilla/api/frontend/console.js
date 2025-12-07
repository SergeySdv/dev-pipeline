const STORAGE_KEYS = {
  token: "tgz_token",
  apiBase: "tgz_api_base",
  projectTokens: "tgz_project_tokens",
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
  events: [],
  operations: [],
  eventFilter: "all",
  eventSpecFilter: "",
  operationsInvalidOnly: false,
  operationsSpecFilter: "",
  projectSort: "name",
  protocolSort: "updated",
  projectTokens: JSON.parse(
    localStorage.getItem(STORAGE_KEYS.projectTokens)
      || localStorage.getItem(LEGACY_STORAGE_KEYS.projectTokens)
      || "{}"
  ),
  queueStats: null,
  queueJobs: [],
  metrics: { qaVerdicts: {}, tokenUsageByPhase: {}, tokenUsageByModel: {} },
  selectedProject: null,
  selectedProtocol: null,
  poll: null,
};

// Rough price table (USD per 1k tokens). Extend as needed; unknown models default to 0.
const MODEL_PRICING = {
  "gpt-5.1-high": 0.003,
  "gpt-5.1": 0.002,
  "codex-5.1-max-xhigh": 0.02,
  "codex-5.1-max": 0.01,
};

const statusEl = document.getElementById("authStatus");
const apiBaseInput = document.getElementById("apiBase");
const apiTokenInput = document.getElementById("apiToken");
const projectTokenInput = document.getElementById("projectToken");
const saveProjectTokenBtn = document.getElementById("saveProjectToken");

function apiPath(path) {
  const base = state.apiBase || "";
  const baseTrimmed = base.endsWith("/") ? base.slice(0, -1) : base;
  return `${baseTrimmed}${path}`;
}

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

async function loadAudits() {
  try {
    const ops = await apiFetch("/events");
    state.operations = ops;
    renderAuditHistory();
  } catch (err) {
    setStatus(err.message, "error");
  }
}
