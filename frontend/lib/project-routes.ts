export function getProjectExecutionPath(
  projectId: number | string,
  sprintId?: number | string | null
): string {
  const params = new URLSearchParams({ tab: "execution" });
  if (sprintId !== undefined && sprintId !== null && sprintId !== "") {
    params.set("sprint", String(sprintId));
  }
  return `/projects/${projectId}?${params.toString()}`;
}

export function getProjectSpecWorkspacePath(projectId: number | string): string {
  return `/projects/${projectId}?tab=spec`;
}

export function getProjectSpecWorkflowPath(projectId: number | string): string {
  const params = new URLSearchParams({
    wizard: "generate-specs",
    tab: "spec",
  });
  return `/projects/${projectId}?${params.toString()}`;
}

export function getProjectManualPlanWizardPath(projectId: number | string): string {
  return `/projects/${projectId}?wizard=design-solution`;
}

export function getProjectManualTasksWizardPath(projectId: number | string): string {
  return `/projects/${projectId}?wizard=implement-feature`;
}
