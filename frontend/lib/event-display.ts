import type { Event } from "@/lib/api/types";

type EventLike = Pick<Event, "event_type" | "event_category" | "message" | "metadata">;

function promptQaOnly(metadata: Record<string, unknown> | null | undefined): boolean {
  if (!metadata) return false;
  const gates = metadata.gates;
  if (!Array.isArray(gates) || gates.length !== 1) return false;
  return gates[0] === "prompt_qa";
}

export function getDisplayEventType(event: EventLike): string {
  if (promptQaOnly(event.metadata)) {
    if (event.event_type === "qa_started") return "execution_qa_started";
    if (event.event_type === "qa_passed") return "execution_qa_passed";
    if (event.event_type === "qa_failed") return "execution_qa_failed";
  }
  return event.event_type;
}

export function getDisplayEventCategory(event: EventLike): string | null | undefined {
  if (promptQaOnly(event.metadata) && event.event_type.startsWith("qa_")) {
    return "execution";
  }
  return event.event_category;
}

export function getDisplayEventMessage(event: EventLike): string {
  if (promptQaOnly(event.metadata)) {
    const stepName =
      typeof event.metadata?.step_name === "string" && event.metadata.step_name
        ? `${event.metadata.step_name} `
        : "";
    if (event.event_type === "qa_started") {
      return `${stepName}implementation quality checks started`.trim();
    }
    if (event.event_type === "qa_passed") {
      return `${stepName}implementation quality checks passed`.trim();
    }
    if (event.event_type === "qa_failed") {
      return `${stepName}implementation quality checks failed`.trim();
    }
  }
  return event.message;
}
