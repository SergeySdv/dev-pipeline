/**
 * Adapters for transforming backend API responses to frontend types.
 *
 * These adapters handle:
 * - Flattening nested structures (e.g., speckit_metadata)
 * - Mapping field name differences
 * - Providing defaults for optional fields
 */

import type { CodexRun,ProtocolArtifact, ProtocolRun } from "../types";

// Raw backend response types
interface RawProtocolRun {
  id: number;
  project_id: number;
  protocol_name: string;
  status: string;
  base_branch: string;
  worktree_path: string | null;
  windmill_flow_id: string | null;
  speckit_metadata: Record<string, unknown> | null;
  summary?: string | null;
  created_at: string;
  updated_at: string;
}

interface RawProtocolArtifact {
  id: string;
  step_run_id: number;
  step_name: string | null;
  type: string;
  name: string;
  size: number;
  created_at: string | null;
}

/**
 * Adapt a raw protocol run from the backend to the frontend ProtocolRun type.
 *
 * Handles:
 * - Flattening speckit_metadata fields (spec_hash, validation_status, etc.)
 * - Mapping windmill_flow_id to flow info
 */
export function adaptProtocol(data: RawProtocolRun): ProtocolRun {
  const meta = data.speckit_metadata || {};

  return {
    id: data.id,
    project_id: data.project_id,
    protocol_name: data.protocol_name,
    status: data.status as ProtocolRun["status"],
    base_branch: data.base_branch,
    worktree_path: data.worktree_path,
    windmill_flow_id: data.windmill_flow_id,

    // Flatten speckit_metadata
    spec_hash: (meta.spec_hash as string) ?? null,
    spec_validation_status: (meta.validation_status as string) ?? null,
    spec_validated_at: (meta.validated_at as string) ?? null,

    // Template info from metadata
    template_source: (meta.template_source as string) ?? null,
    template_config: (meta.template_config as Record<string, unknown>) ?? null,

    // Protocol root
    protocol_root: (meta.protocol_root as string) ?? null,

    // Description/summary
    description: data.summary ?? (meta.description as string) ?? null,

    // Policy fields
    policy_pack_key: (meta.policy_pack_key as string) ?? null,
    policy_pack_version: (meta.policy_pack_version as string) ?? null,
    policy_effective_hash: (meta.policy_effective_hash as string) ?? null,
    policy_effective_json: (meta.policy_effective_json as Record<string, unknown>) ?? null,

    created_at: data.created_at,
    updated_at: data.updated_at,
  };
}

/**
 * Adapt an array of protocol runs.
 */
export function adaptProtocols(data: RawProtocolRun[]): ProtocolRun[] {
  return data.map(adaptProtocol);
}

/**
 * Adapt a raw protocol artifact from the backend.
 */
export function adaptProtocolArtifact(
  data: RawProtocolArtifact,
  protocolRunId: number
): ProtocolArtifact {
  return {
    id: data.id,
    protocol_run_id: protocolRunId,
    step_run_id: data.step_run_id,
    run_id: null,
    name: data.name,
    type: data.type,
    kind: data.type, // Alias for backwards compatibility
    size: data.size,
    bytes: data.size, // Alias for backwards compatibility
    created_at: data.created_at ?? new Date().toISOString(),
  };
}

/**
 * Adapt an array of protocol artifacts.
 */
export function adaptProtocolArtifacts(
  data: RawProtocolArtifact[],
  protocolRunId: number
): ProtocolArtifact[] {
  return data.map((a) => adaptProtocolArtifact(a, protocolRunId));
}

// Re-export types for convenience
export type { CodexRun,ProtocolArtifact, ProtocolRun };
