/**
 * Property-Based Tests for Queue Stats Panel Component
 * **Feature: frontend-comprehensive-refactor**
 *
 * Property 15: Queue stats status breakdown
 *
 * **Validates: Requirements 11.2**
 */

import * as fc from "fast-check";
import { describe, expect,it } from "vitest";

import {
  computeQueueStatusBreakdown,
  validateQueueStatsBreakdown,
  verifyBreakdownSums,
} from "@/components/features/queue-stats-panel";
import type { QueueStats } from "@/lib/api/types";

// Arbitrary generator for queue names
const queueNameArbitrary = fc
  .string({ minLength: 1, maxLength: 50 })
  .filter((s) => s.trim().length > 0);

// Arbitrary generator for non-negative counts
const countArbitrary = fc.nat({ max: 10000 });

// Arbitrary generator for a valid QueueStats entry
const queueStatsArbitrary: fc.Arbitrary<QueueStats> = fc.record({
  name: queueNameArbitrary,
  queued: countArbitrary,
  started: countArbitrary,
  failed: countArbitrary,
});

// Arbitrary generator for an array of QueueStats
const queueStatsArrayArbitrary = fc.array(queueStatsArbitrary, { minLength: 0, maxLength: 20 });

describe("Queue Stats Panel Property Tests", () => {
  /**
   * Property 15: Queue stats status breakdown
   * For any queue statistics data, the panel SHALL display counts for all job statuses present in the data.
   * **Validates: Requirements 11.2**
   */
  describe("Property 15: Queue stats status breakdown", () => {
    it("should always produce complete breakdown for any valid queue stats", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown = computeQueueStatusBreakdown(stats);
          const validation = validateQueueStatsBreakdown(breakdown);

          // Breakdown should always be complete
          expect(validation.isComplete).toBe(true);
          expect(validation.hasQueuedCount).toBe(true);
          expect(validation.hasStartedCount).toBe(true);
          expect(validation.hasFailedCount).toBe(true);
          expect(validation.allCountsNonNegative).toBe(true);
        }),
        { numRuns: 100 }
      );
    });

    it("should correctly sum all queue stats for queued status", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown = computeQueueStatusBreakdown(stats);
          const expectedQueued = stats.reduce((sum, s) => sum + s.queued, 0);

          expect(breakdown.queued).toBe(expectedQueued);
        }),
        { numRuns: 100 }
      );
    });

    it("should correctly sum all queue stats for started status", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown = computeQueueStatusBreakdown(stats);
          const expectedStarted = stats.reduce((sum, s) => sum + s.started, 0);

          expect(breakdown.started).toBe(expectedStarted);
        }),
        { numRuns: 100 }
      );
    });

    it("should correctly sum all queue stats for failed status", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown = computeQueueStatusBreakdown(stats);
          const expectedFailed = stats.reduce((sum, s) => sum + s.failed, 0);

          expect(breakdown.failed).toBe(expectedFailed);
        }),
        { numRuns: 100 }
      );
    });

    it("should verify breakdown sums match individual stats", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown = computeQueueStatusBreakdown(stats);

          expect(verifyBreakdownSums(stats, breakdown)).toBe(true);
        }),
        { numRuns: 100 }
      );
    });

    it("should return zero counts for empty stats array", () => {
      const breakdown = computeQueueStatusBreakdown([]);

      expect(breakdown.queued).toBe(0);
      expect(breakdown.started).toBe(0);
      expect(breakdown.failed).toBe(0);
    });

    it("should handle single queue stats correctly", () => {
      fc.assert(
        fc.property(queueStatsArbitrary, (stat) => {
          const breakdown = computeQueueStatusBreakdown([stat]);

          expect(breakdown.queued).toBe(stat.queued);
          expect(breakdown.started).toBe(stat.started);
          expect(breakdown.failed).toBe(stat.failed);
        }),
        { numRuns: 100 }
      );
    });

    it("should have non-negative counts for any input", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown = computeQueueStatusBreakdown(stats);

          expect(breakdown.queued).toBeGreaterThanOrEqual(0);
          expect(breakdown.started).toBeGreaterThanOrEqual(0);
          expect(breakdown.failed).toBeGreaterThanOrEqual(0);
        }),
        { numRuns: 100 }
      );
    });

    it("should be associative - order of stats should not matter", () => {
      fc.assert(
        fc.property(queueStatsArrayArbitrary, (stats) => {
          const breakdown1 = computeQueueStatusBreakdown(stats);
          const breakdown2 = computeQueueStatusBreakdown([...stats].reverse());

          expect(breakdown1.queued).toBe(breakdown2.queued);
          expect(breakdown1.started).toBe(breakdown2.started);
          expect(breakdown1.failed).toBe(breakdown2.failed);
        }),
        { numRuns: 100 }
      );
    });
  });
});
