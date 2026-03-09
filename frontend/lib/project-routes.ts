export function getProjectExecutionPath(
  projectId: number,
  sprintId?: number | string | null
): string {
  const params = new URLSearchParams({ tab: "execution" });
  if (sprintId !== undefined && sprintId !== null && sprintId !== "") {
    params.set("sprint", String(sprintId));
  }
  return `/projects/${projectId}?${params.toString()}`;
}

export function getProjectSpecWorkspacePath(projectId: number): string {
  return `/projects/${projectId}?tab=spec`;
}

export function getProjectSpecWorkflowPath(projectId: number): string {
  const params = new URLSearchParams({
    wizard: "generate-specs",
    tab: "spec",
  });
  return `/projects/${projectId}?${params.toString()}`;
}
