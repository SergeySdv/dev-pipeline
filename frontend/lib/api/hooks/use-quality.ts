"use client";

import { useQuery } from "@tanstack/react-query";

import { useVisibility } from "@/lib/hooks/use-visibility";

import { apiClient } from "../client";
import { queryKeys } from "../query-keys";

// Types for Quality Dashboard
export interface QAOverview {
  total_protocols: number;
  passed: number;
  warnings: number;
  failed: number;
  average_score: number;
}

export interface QAFinding {
  id: number;
  protocol_id: number;
  project_name: string;
  article: string;
  article_name: string;
  severity: string;
  message: string;
  timestamp: string;
}

export interface ConstitutionalGate {
  article: string;
  name: string;
  status: string;
  checks: number;
}

export interface QualityDashboard {
  overview: QAOverview;
  recent_findings: QAFinding[];
  constitutional_gates: ConstitutionalGate[];
}

export interface ProtocolQualityGate {
  article: string;
  name: string;
  status: "passed" | "warning" | "failed" | "skipped" | string;
  findings: Array<Record<string, unknown>>;
}

export interface ProtocolQualityChecklistItem {
  id: string;
  description: string;
  passed: boolean;
  required: boolean;
}

export interface ProtocolQualityChecklist {
  passed: number;
  total: number;
  items: ProtocolQualityChecklistItem[];
}

export interface ProtocolQualitySummary {
  protocol_run_id: number;
  score: number;
  gates: ProtocolQualityGate[];
  checklist: ProtocolQualityChecklist;
  overall_status: "passed" | "warning" | "failed" | string;
  blocking_issues: number;
  warnings: number;
}

function useConditionalRefetchInterval(baseInterval: number) {
  const isVisible = useVisibility();
  return isVisible ? baseInterval : false;
}

// Get Quality Dashboard
export function useQualityDashboard() {
  return useQuery({
    queryKey: queryKeys.quality.dashboard(),
    queryFn: () => apiClient.get<QualityDashboard>("/quality/dashboard"),
  });
}

export function useProtocolQualitySummary(protocolId: number | undefined, enabled = true) {
  const refetchInterval = useConditionalRefetchInterval(5000);
  return useQuery({
    queryKey: queryKeys.protocols.qualitySummary(protocolId as number),
    queryFn: () => apiClient.get<ProtocolQualitySummary>(`/protocols/${protocolId}/quality`),
    enabled: !!protocolId && enabled,
    refetchInterval,
  });
}

export function useProtocolQualityGates(protocolId: number | undefined, enabled = true) {
  const refetchInterval = useConditionalRefetchInterval(5000);
  return useQuery({
    queryKey: queryKeys.protocols.qualityGates(protocolId as number),
    queryFn: () =>
      apiClient.get<{ gates: ProtocolQualityGate[] }>(`/protocols/${protocolId}/quality/gates`),
    enabled: !!protocolId && enabled,
    refetchInterval,
  });
}
