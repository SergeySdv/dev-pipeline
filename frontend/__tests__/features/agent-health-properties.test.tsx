/**
 * Property-Based Tests for Agent Health Dashboard Component
 * **Feature: frontend-comprehensive-refactor**
 *
 * Property 10: Agent card rendering completeness
 *
 * **Validates: Requirements 7.1, 7.2, 7.3**
 */

import * as fc from "fast-check";
import { describe, expect,it } from "vitest";

import {
  computeAgentCardData,
  validateAgentCardCompleteness,
} from "@/components/features/agent-health-dashboard";
import type { Agent, AgentHealth, AgentMetrics } from "@/lib/api/types";

// Arbitrary generator for agent IDs
const agentIdArbitrary = fc
  .string({ minLength: 1, maxLength: 50 })
  .filter((s) => s.trim().length > 0);

// Arbitrary generator for agent names
const agentNameArbitrary = fc
  .string({ minLength: 1, maxLength: 100 })
  .filter((s) => s.trim().length > 0);

// Arbitrary generator for agent kinds
const agentKindArbitrary = fc.constantFrom("opencode", "codex", "claude", "gpt", "custom");

// Arbitrary generator for agent status
const agentStatusArbitrary = fc.constantFrom("available", "busy", "unavailable") as fc.Arbitrary<
  "available" | "busy" | "unavailable"
>;

// Arbitrary generator for a valid Agent
const agentArbitrary: fc.Arbitrary<Agent> = fc.record({
  id: agentIdArbitrary,
  name: agentNameArbitrary,
  kind: agentKindArbitrary,
  capabilities: fc.array(fc.string(), { maxLength: 5 }),
  status: agentStatusArbitrary,
  default_model: fc.option(fc.string(), { nil: null }),
  command_dir: fc.option(fc.string(), { nil: null }),
  enabled: fc.option(fc.boolean(), { nil: undefined }),
});

// Arbitrary generator for AgentHealth
const agentHealthArbitrary = (agentId: string): fc.Arbitrary<AgentHealth> =>
  fc.record({
    agent_id: fc.constant(agentId),
    available: fc.boolean(),
    version: fc.option(fc.string(), { nil: null }),
    error: fc.option(fc.string(), { nil: null }),
    response_time_ms: fc.option(fc.nat({ max: 10000 }), { nil: null }),
  });

// Arbitrary generator for AgentMetrics
const agentMetricsArbitrary = (agentId: string): fc.Arbitrary<AgentMetrics> =>
  fc.record({
    agent_id: fc.constant(agentId),
    active_steps: fc.nat({ max: 100 }),
    completed_steps: fc.nat({ max: 1000 }),
    failed_steps: fc.nat({ max: 100 }),
    total_steps: fc.nat({ max: 1200 }),
    last_activity_at: fc.option(
      fc.date().map((d) => d.toISOString()),
      { nil: undefined }
    ),
  });

// Combined arbitrary for agent with optional health and metrics
const agentWithDataArbitrary = agentArbitrary.chain((agent) =>
  fc.record({
    agent: fc.constant(agent),
    health: fc.option(agentHealthArbitrary(agent.id), { nil: undefined }),
    metrics: fc.option(agentMetricsArbitrary(agent.id), { nil: undefined }),
  })
);

describe("Agent Health Dashboard Property Tests", () => {
  /**
   * Property 10: Agent card rendering completeness
   * For any agent in the health dashboard, the rendered card SHALL display
   * the agent's name, status, and metrics (active/completed/failed counts).
   * **Validates: Requirements 7.1, 7.2, 7.3**
   */
  describe("Property 10: Agent card rendering completeness", () => {
    it("should always produce complete card data for any valid agent", () => {
      fc.assert(
        fc.property(agentWithDataArbitrary, ({ agent, health, metrics }) => {
          const cardData = computeAgentCardData(agent, health, metrics);
          const validation = validateAgentCardCompleteness(cardData);

          // Card should always be complete
          expect(validation.isComplete).toBe(true);
          expect(validation.hasName).toBe(true);
          expect(validation.hasStatus).toBe(true);
          expect(validation.hasActiveSteps).toBe(true);
          expect(validation.hasCompletedSteps).toBe(true);
          expect(validation.hasFailedSteps).toBe(true);
        }),
        { numRuns: 100 }
      );
    });

    it("should preserve agent name in card data", () => {
      fc.assert(
        fc.property(agentWithDataArbitrary, ({ agent, health, metrics }) => {
          const cardData = computeAgentCardData(agent, health, metrics);

          // Name should be preserved from agent
          expect(cardData.name).toBe(agent.name);
        }),
        { numRuns: 100 }
      );
    });

    it("should preserve agent kind in card data", () => {
      fc.assert(
        fc.property(agentWithDataArbitrary, ({ agent, health, metrics }) => {
          const cardData = computeAgentCardData(agent, health, metrics);

          // Kind should be preserved from agent
          expect(cardData.kind).toBe(agent.kind);
        }),
        { numRuns: 100 }
      );
    });

    it("should have valid status for any agent configuration", () => {
      fc.assert(
        fc.property(agentWithDataArbitrary, ({ agent, health, metrics }) => {
          const cardData = computeAgentCardData(agent, health, metrics);

          // Status should be one of the valid values
          expect(["available", "unavailable", "disabled"]).toContain(cardData.status);
        }),
        { numRuns: 100 }
      );
    });

    it("should have non-negative metrics counts", () => {
      fc.assert(
        fc.property(agentWithDataArbitrary, ({ agent, health, metrics }) => {
          const cardData = computeAgentCardData(agent, health, metrics);

          // All metrics should be non-negative
          expect(cardData.activeSteps).toBeGreaterThanOrEqual(0);
          expect(cardData.completedSteps).toBeGreaterThanOrEqual(0);
          expect(cardData.failedSteps).toBeGreaterThanOrEqual(0);
        }),
        { numRuns: 100 }
      );
    });

    it("should use metrics values when provided", () => {
      fc.assert(
        fc.property(
          agentArbitrary,
          agentArbitrary.chain((a) => agentMetricsArbitrary(a.id)),
          (agent, metrics) => {
            const cardData = computeAgentCardData(agent, undefined, metrics);

            // Metrics should be taken from the metrics object
            expect(cardData.activeSteps).toBe(metrics.active_steps);
            expect(cardData.completedSteps).toBe(metrics.completed_steps);
            expect(cardData.failedSteps).toBe(metrics.failed_steps);
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should default metrics to zero when not provided", () => {
      fc.assert(
        fc.property(agentArbitrary, (agent) => {
          const cardData = computeAgentCardData(agent, undefined, undefined);

          // Without metrics, all counts should default to 0
          expect(cardData.activeSteps).toBe(0);
          expect(cardData.completedSteps).toBe(0);
          expect(cardData.failedSteps).toBe(0);
        }),
        { numRuns: 100 }
      );
    });

    it("should correctly determine status based on health and enabled state", () => {
      fc.assert(
        fc.property(
          agentArbitrary,
          fc.boolean(), // enabled
          fc.boolean(), // available from health
          (agent, enabled, available) => {
            const agentWithEnabled = { ...agent, enabled };
            const health: AgentHealth = {
              agent_id: agent.id,
              available,
            };

            const cardData = computeAgentCardData(agentWithEnabled, health, undefined);

            if (!enabled) {
              expect(cardData.status).toBe("disabled");
            } else if (available) {
              expect(cardData.status).toBe("available");
            } else {
              expect(cardData.status).toBe("unavailable");
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
