import {
  ClipboardCheck,
  ClipboardList,
  FileSearch,
  FileText,
  Kanban,
  ListTodo,
  MessageSquare,
  PlayCircle,
} from "lucide-react";

export type WorkflowStep =
  | "spec"
  | "clarify"
  | "plan"
  | "checklist"
  | "tasks"
  | "analyze"
  | "implement"
  | "sprint";

export type WorkflowStepStatus = "pending" | "in-progress" | "completed" | "failed" | "skipped";

export interface WorkflowStepConfig {
  key: WorkflowStep;
  order: number;
  label: string;
  icon: typeof FileText;
  description: string;
  wizard?: string;
  tab: string;
  requiredSteps?: WorkflowStep[];
}

export const WORKFLOW_STEPS: Record<WorkflowStep, WorkflowStepConfig> = {
  spec: {
    key: "spec",
    order: 1,
    label: "Specification",
    icon: FileText,
    description: "Define feature requirements",
    wizard: "generate-specs",
    tab: "spec",
  },
  clarify: {
    key: "clarify",
    order: 2,
    label: "Clarify",
    icon: MessageSquare,
    description: "Resolve ambiguity",
    tab: "spec",
    requiredSteps: ["spec"],
  },
  plan: {
    key: "plan",
    order: 3,
    label: "Implementation Plan",
    icon: ClipboardList,
    description: "Design architecture & approach",
    wizard: "design-solution",
    tab: "spec",
    requiredSteps: ["spec"],
  },
  checklist: {
    key: "checklist",
    order: 4,
    label: "Checklist",
    icon: ClipboardCheck,
    description: "Validate requirements",
    tab: "spec",
    requiredSteps: ["spec", "plan"],
  },
  tasks: {
    key: "tasks",
    order: 5,
    label: "Task List",
    icon: ListTodo,
    description: "Break down into tasks",
    wizard: "implement-feature",
    tab: "spec",
    requiredSteps: ["spec", "plan"],
  },
  analyze: {
    key: "analyze",
    order: 6,
    label: "Analyze",
    icon: FileSearch,
    description: "Consistency report",
    tab: "spec",
    requiredSteps: ["spec", "plan", "tasks"],
  },
  implement: {
    key: "implement",
    order: 7,
    label: "Implement",
    icon: PlayCircle,
    description: "Initialize execution",
    tab: "spec",
    requiredSteps: ["spec", "plan", "tasks"],
  },
  sprint: {
    key: "sprint",
    order: 8,
    label: "Execution",
    icon: Kanban,
    description: "Assign to execution cycle",
    tab: "execution",
    requiredSteps: ["spec", "plan", "tasks", "implement"],
  },
} as const;

export const WORKFLOW_STEP_ORDER: WorkflowStep[] = [
  "spec",
  "clarify",
  "plan",
  "checklist",
  "tasks",
  "analyze",
  "implement",
  "sprint",
];

export function getWorkflowStepConfig(step: WorkflowStep): WorkflowStepConfig {
  return WORKFLOW_STEPS[step];
}

export function getStepHref(step: WorkflowStep, projectId: number): string {
  const config = WORKFLOW_STEPS[step];
  const base = `/projects/${projectId}`;

  if (config.wizard) {
    return `${base}?wizard=${config.wizard}`;
  }
  return `${base}?tab=${config.tab}`;
}

export function isStepAccessible(
  step: WorkflowStep,
  completedSteps: Set<WorkflowStep>
): boolean {
  const config = WORKFLOW_STEPS[step];
  if (!config.requiredSteps) return true;
  return config.requiredSteps.every((required) => completedSteps.has(required));
}

export function getNextStep(
  currentStep: WorkflowStep,
  completedSteps: Set<WorkflowStep>
): WorkflowStep | null {
  const currentIndex = WORKFLOW_STEP_ORDER.indexOf(currentStep);

  for (let i = currentIndex + 1; i < WORKFLOW_STEP_ORDER.length; i++) {
    const nextStep = WORKFLOW_STEP_ORDER[i];
    if (isStepAccessible(nextStep, completedSteps)) {
      return nextStep;
    }
  }

  return null;
}

export function inferStepStatus(
  step: WorkflowStep,
  specData: {
    hasSpec?: boolean;
    hasPlan?: boolean;
    hasTasks?: boolean;
    hasChecklist?: boolean;
    hasAnalysis?: boolean;
    hasImplement?: boolean;
    inSprint?: boolean;
  }
): WorkflowStepStatus {
  const stepIndex = WORKFLOW_STEP_ORDER.indexOf(step);

  if (step === "spec") {
    return specData.hasSpec ? "completed" : "pending";
  }
  if (step === "clarify") {
    return specData.hasSpec ? "in-progress" : "pending";
  }
  if (step === "plan") {
    return specData.hasPlan ? "completed" : specData.hasSpec ? "pending" : "pending";
  }
  if (step === "checklist") {
    return specData.hasChecklist ? "completed" : specData.hasPlan ? "pending" : "pending";
  }
  if (step === "tasks") {
    return specData.hasTasks ? "completed" : specData.hasPlan ? "pending" : "pending";
  }
  if (step === "analyze") {
    return specData.hasAnalysis ? "completed" : specData.hasTasks ? "pending" : "pending";
  }
  if (step === "implement") {
    return specData.hasImplement ? "completed" : specData.hasTasks ? "pending" : "pending";
  }
  if (step === "sprint") {
    return specData.inSprint ? "completed" : specData.hasImplement ? "pending" : "pending";
  }

  return "pending";
}

export function inferCompletedSteps(specData: {
  hasSpec?: boolean;
  hasPlan?: boolean;
  hasTasks?: boolean;
  hasChecklist?: boolean;
  hasAnalysis?: boolean;
  hasImplement?: boolean;
  inSprint?: boolean;
}): Set<WorkflowStep> {
  const completed = new Set<WorkflowStep>();

  if (specData.hasSpec) completed.add("spec");
  if (specData.hasPlan) completed.add("plan");
  if (specData.hasTasks) completed.add("tasks");
  if (specData.hasChecklist) completed.add("checklist");
  if (specData.hasAnalysis) completed.add("analyze");
  if (specData.hasImplement) completed.add("implement");
  if (specData.inSprint) completed.add("sprint");

  return completed;
}
