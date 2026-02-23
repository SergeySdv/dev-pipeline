"use client";

import * as React from "react";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

import { cn } from "@/lib/utils";

export interface StepItem {
  id: string;
  label: string;
  description?: string;
  icon?: React.ElementType;
}

export type StepItemStatus = "pending" | "active" | "completed" | "error" | "loading";

export interface StepIndicatorProps {
  steps: StepItem[];
  currentStep: string;
  completedSteps?: Set<string>;
  stepStatus?: Record<string, StepItemStatus>;
  onStepClick?: (stepId: string) => void;
  variant?: "horizontal" | "vertical" | "compact";
  showLabels?: boolean;
  showConnectors?: boolean;
  className?: string;
}

const getStatusClasses = (status: StepItemStatus): string => {
  switch (status) {
    case "completed":
      return "bg-green-500 text-white border-green-500";
    case "active":
      return "bg-primary text-primary-foreground border-primary";
    case "loading":
      return "bg-blue-500 text-white border-blue-500";
    case "error":
      return "bg-destructive text-destructive-foreground border-destructive";
    default:
      return "bg-muted text-muted-foreground border-muted";
  }
};

const getStatusIcon = (
  status: StepItemStatus,
  stepNumber: number,
  Icon?: React.ElementType
) => {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5" />;
    case "loading":
      return <Loader2 className="h-5 w-5 animate-spin" />;
    default:
      return Icon ? <Icon className="h-5 w-5" /> : <span className="text-sm font-medium">{stepNumber}</span>;
  }
};

export function StepIndicator({
  steps,
  currentStep,
  completedSteps = new Set(),
  stepStatus,
  onStepClick,
  variant = "horizontal",
  showLabels = true,
  showConnectors = true,
  className,
}: StepIndicatorProps) {
  const getStepStatus = (stepId: string): StepItemStatus => {
    if (stepStatus?.[stepId]) return stepStatus[stepId];
    if (completedSteps.has(stepId)) return "completed";
    if (currentStep === stepId) return "active";
    return "pending";
  };

  const stepIndex = steps.findIndex((s) => s.id === currentStep);

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        {steps.map((step, index) => {
          const status = getStepStatus(step.id);
          const Icon = step.icon;
          const isClickable = onStepClick && (status === "completed" || index <= stepIndex + 1);

          return (
            <React.Fragment key={step.id}>
              <button
                type="button"
                disabled={!isClickable}
                onClick={() => onStepClick?.(step.id)}
                className={cn(
                  "flex items-center gap-1.5 rounded-md px-2 py-1 text-sm transition-colors",
                  status === "completed" && "text-green-600 hover:bg-green-500/10",
                  status === "active" && "text-primary font-medium hover:bg-primary/10",
                  status === "loading" && "text-blue-600 hover:bg-blue-500/10",
                  status === "error" && "text-destructive hover:bg-destructive/10",
                  status === "pending" && "text-muted-foreground hover:bg-muted",
                  isClickable && "cursor-pointer",
                  !isClickable && "cursor-default"
                )}
                aria-current={status === "active" ? "step" : undefined}
              >
                {status === "completed" ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : Icon ? (
                  <Icon className="h-4 w-4" />
                ) : (
                  <Circle className="h-4 w-4" />
                )}
                {showLabels && <span className="hidden sm:inline">{step.label}</span>}
              </button>
              {showConnectors && index < steps.length - 1 && (
                <div className="bg-muted h-0.5 w-4 flex-shrink-0" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  }

  if (variant === "vertical") {
    return (
      <div className={cn("flex flex-col gap-4", className)} role="navigation" aria-label="Progress steps">
        {steps.map((step, index) => {
          const status = getStepStatus(step.id);
          const Icon = step.icon;
          const isClickable = onStepClick && (status === "completed" || index <= stepIndex + 1);

          return (
            <div key={step.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => onStepClick?.(step.id)}
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors",
                    getStatusClasses(status),
                    isClickable && "cursor-pointer hover:opacity-80",
                    !isClickable && "cursor-default"
                  )}
                  aria-current={status === "active" ? "step" : undefined}
                >
                  {getStatusIcon(status, index + 1, Icon)}
                </button>
                {showConnectors && index < steps.length - 1 && (
                  <div
                    className={cn(
                      "my-2 w-0.5 flex-1",
                      completedSteps.has(step.id) ? "bg-green-500" : "bg-muted"
                    )}
                  />
                )}
              </div>
              <div className="flex-1 pb-4">
                {showLabels && (
                  <>
                    <p
                      className={cn(
                        "text-sm font-medium",
                        status === "active" && "text-primary",
                        status === "pending" && "text-muted-foreground"
                      )}
                    >
                      {step.label}
                    </p>
                    {step.description && (
                      <p className="text-muted-foreground text-xs">{step.description}</p>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Horizontal (default)
  return (
    <div
      className={cn("bg-muted/30 rounded-lg border p-4", className)}
      role="navigation"
      aria-label="Progress steps"
    >
      <div className="flex items-center justify-between text-sm">
        {steps.map((step, index) => {
          const status = getStepStatus(step.id);
          const Icon = step.icon;
          const isClickable = onStepClick && (status === "completed" || index <= stepIndex + 1);

          return (
            <React.Fragment key={step.id}>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  disabled={!isClickable}
                  onClick={() => onStepClick?.(step.id)}
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors",
                    getStatusClasses(status),
                    isClickable && "cursor-pointer hover:opacity-80",
                    !isClickable && "cursor-default"
                  )}
                  aria-current={status === "active" ? "step" : undefined}
                  aria-label={`${step.label}${status === "completed" ? " (completed)" : status === "active" ? " (current)" : ""}`}
                >
                  {getStatusIcon(status, index + 1, Icon)}
                </button>
                {showLabels && (
                  <span
                    className={cn(
                      status === "active" ? "font-medium" : "text-muted-foreground"
                    )}
                  >
                    {step.label}
                  </span>
                )}
              </div>
              {showConnectors && index < steps.length - 1 && (
                <div
                  className={cn(
                    "mx-2 h-0.5 flex-1",
                    completedSteps.has(step.id) ? "bg-green-500" : "bg-muted"
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

export function useStepNavigation(
  steps: StepItem[],
  initialStep?: string
) {
  const [currentStep, setCurrentStep] = React.useState(
    initialStep ?? steps[0]?.id ?? ""
  );
  const [completedSteps, setCompletedSteps] = React.useState<Set<string>>(new Set());

  const currentIndex = steps.findIndex((s) => s.id === currentStep);

  const goToNext = React.useCallback(() => {
    if (currentIndex < steps.length - 1) {
      setCompletedSteps((prev) => new Set([...prev, currentStep]));
      setCurrentStep(steps[currentIndex + 1].id);
    }
  }, [currentIndex, currentStep, steps]);

  const goToPrevious = React.useCallback(() => {
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1].id);
    }
  }, [currentIndex, steps]);

  const goToStep = React.useCallback(
    (stepId: string) => {
      const index = steps.findIndex((s) => s.id === stepId);
      if (index !== -1 && index <= currentIndex + 1) {
        setCurrentStep(stepId);
      }
    },
    [currentIndex, steps]
  );

  const isFirst = currentIndex === 0;
  const isLast = currentIndex === steps.length - 1;

  return {
    currentStep,
    setCurrentStep,
    completedSteps,
    setCompletedSteps,
    currentIndex,
    goToNext,
    goToPrevious,
    goToStep,
    isFirst,
    isLast,
    markComplete: (stepId: string) =>
      setCompletedSteps((prev) => new Set([...prev, stepId])),
    reset: (step?: string) => {
      setCurrentStep(step ?? steps[0]?.id ?? "");
      setCompletedSteps(new Set());
    },
  };
}
