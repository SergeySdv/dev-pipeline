export function parseTemplateConfigInput(raw: string): Record<string, unknown> | undefined {
  const trimmed = raw.trim();
  if (!trimmed) {
    return undefined;
  }

  let value: unknown;
  try {
    value = JSON.parse(trimmed);
  } catch {
    throw new Error("Template config must be valid JSON");
  }

  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Template config must be a JSON object");
  }

  return value as Record<string, unknown>;
}
