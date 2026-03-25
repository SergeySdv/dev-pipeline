function parseTemplateSourceObject(source: string): Record<string, unknown> | null {
  const trimmed = source.trim();
  if (!trimmed.startsWith("{")) {
    return null;
  }

  try {
    const parsed = JSON.parse(trimmed);
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, unknown>;
    }
  } catch {
    return null;
  }

  return null;
}

export function formatProtocolTemplateSource(source: string | null): string {
  if (!source) {
    return "None";
  }

  const parsed = parseTemplateSourceObject(source);
  if (!parsed) {
    return source;
  }

  const kind = typeof parsed.kind === "string" ? parsed.kind : null;
  const name = typeof parsed.name === "string" ? parsed.name : null;
  const path = typeof parsed.path === "string" ? parsed.path : null;

  if (kind && name) {
    return `${kind}: ${name}`;
  }
  if (name) {
    return name;
  }
  if (path) {
    return path;
  }

  return source;
}

function formatTemplateConfigValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

export function describeProtocolTemplateConfig(config: Record<string, unknown> | null): {
  summary: string;
  detail: string | null;
} {
  if (!config) {
    return {
      summary: "None",
      detail: null,
    };
  }

  const entries = Object.entries(config);
  if (entries.length === 0) {
    return {
      summary: "0 fields",
      detail: "Empty JSON object",
    };
  }

  const detail = entries
    .slice(0, 2)
    .map(([key, value]) => `${key}=${formatTemplateConfigValue(value)}`)
    .join(", ");

  return {
    summary: `${entries.length} field${entries.length === 1 ? "" : "s"}`,
    detail,
  };
}
