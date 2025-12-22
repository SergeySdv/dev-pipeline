/**
 * Property-Based Tests for Pipeline DAG Component
 * **Feature: frontend-comprehensive-refactor**
 * 
 * Property 3: DAG edge rendering from dependencies
 * Property 4: DAG swimlane grouping
 * Property 5: DAG node color mapping by status
 * Property 6: DAG duration calculation
 * 
 * **Validates: Requirements 3.1, 3.2, 3.3, 3.6**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  getStatusColor,
  calculateDuration,
  groupByParallelGroup,
  buildEdges
} from '@/components/visualizations/pipeline-dag'
import type { StepRun, StepStatus } from '@/lib/api/types'

// Arbitrary generators for property-based testing

const stepStatusArbitrary = fc.oneof(
  fc.constant('pending' as StepStatus),
  fc.constant('running' as StepStatus),
  fc.constant('completed' as StepStatus),
  fc.constant('failed' as StepStatus),
  fc.constant('cancelled' as StepStatus),
  fc.constant('blocked' as StepStatus),
  fc.constant('needs_qa' as StepStatus)
)

const validDateArbitrary = fc.integer({
  min: new Date('2020-01-01').getTime(),
  max: new Date('2030-12-31').getTime()
}).map(ts => new Date(ts).toISOString())

const parallelGroupArbitrary = fc.oneof(
  fc.constant(null),
  fc.constant(undefined),
  fc.string({ minLength: 1, maxLength: 20 }).filter(s => s.trim().length > 0)
)

// Generate a valid StepRun object
const stepRunArbitrary = (id: number, stepIndex: number, dependsOn: number[] = []): fc.Arbitrary<StepRun> =>
  fc.record({
    id: fc.constant(id),
    protocol_run_id: fc.nat({ max: 1000 }),
    step_index: fc.constant(stepIndex),
    step_name: fc.string({ minLength: 1, maxLength: 50 }),
    step_type: fc.oneof(fc.constant('code_gen'), fc.constant('planning'), fc.constant('exec')),
    status: stepStatusArbitrary,
    retries: fc.nat({ max: 5 }),
    model: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: null }),
    engine_id: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: null }),
    policy: fc.constant(null),
    runtime_state: fc.constant(null),
    summary: fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: null }),
    assigned_agent: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: null }),
    depends_on: fc.constant(dependsOn),
    parallel_group: parallelGroupArbitrary as fc.Arbitrary<string | null | undefined>,
    created_at: validDateArbitrary,
    updated_at: validDateArbitrary
  })

// Generate a list of steps with valid dependencies (DAG structure)
const stepsListArbitrary = fc.integer({ min: 1, max: 10 }).chain(count => {
  const stepArbitraries: fc.Arbitrary<StepRun>[] = []

  for (let i = 0; i < count; i++) {
    // Each step can only depend on previous steps (ensures DAG)
    const possibleDeps = Array.from({ length: i }, (_, j) => j + 1)
    const depsArbitrary = fc.subarray(possibleDeps, { minLength: 0, maxLength: Math.min(3, i) })

    stepArbitraries.push(
      depsArbitrary.chain(deps => stepRunArbitrary(i + 1, i, deps))
    )
  }

  return fc.tuple(...stepArbitraries)
})

describe('Pipeline DAG Property Tests', () => {
  /**
   * Property 3: DAG edge rendering from dependencies
   * For any step with a non-empty depends_on array, the rendered DAG SHALL contain
   * edges from each dependency to that step.
   * **Validates: Requirements 3.1**
   */
  describe('Property 3: DAG edge rendering from dependencies', () => {
    it('should create edges for all dependencies', () => {
      fc.assert(
        fc.property(stepsListArbitrary, (steps) => {
          const edges = buildEdges(steps)

          // For each step with dependencies, verify edges exist
          for (const step of steps) {
            const deps = step.depends_on ?? []
            for (const dep of deps) {
              // Find the edge from dependency to this step
              const edgeExists = edges.some(
                edge => edge.source === dep && edge.target === step.id
              )

              // Edge should exist for valid dependencies
              const depExists = steps.some(s => s.id === dep || s.step_index === dep)
              if (depExists) {
                expect(edgeExists).toBe(true)
              }
            }
          }
        }),
        { numRuns: 100 }
      )
    })

    it('should not create edges for non-existent dependencies', () => {
      fc.assert(
        fc.property(stepsListArbitrary, (steps) => {
          const edges = buildEdges(steps)
          const validIds = new Set(steps.map(s => s.id))
          const validIndices = new Set(steps.map(s => s.step_index))

          // All edge sources should reference valid steps
          for (const edge of edges) {
            expect(validIds.has(edge.source) || validIndices.has(edge.source)).toBe(true)
            expect(validIds.has(edge.target)).toBe(true)
          }
        }),
        { numRuns: 100 }
      )
    })
  })

  /**
   * Property 4: DAG swimlane grouping
   * For any set of steps sharing the same parallel_group value, those steps SHALL
   * be rendered in the same visual swimlane.
   * **Validates: Requirements 3.2**
   */
  describe('Property 4: DAG swimlane grouping', () => {
    it('should group steps by parallel_group', () => {
      fc.assert(
        fc.property(stepsListArbitrary, (steps) => {
          const groups = groupByParallelGroup(steps)

          // Verify all steps are accounted for
          let totalSteps = 0
          for (const groupSteps of groups.values()) {
            totalSteps += groupSteps.length
          }
          expect(totalSteps).toBe(steps.length)

          // Verify steps in each group have the same parallel_group
          for (const [groupKey, groupSteps] of groups) {
            for (const step of groupSteps) {
              const stepGroup = step.parallel_group ?? null
              expect(stepGroup).toBe(groupKey)
            }
          }
        }),
        { numRuns: 100 }
      )
    })

    it('should place steps with same parallel_group in same group', () => {
      fc.assert(
        fc.property(stepsListArbitrary, (steps) => {
          const groups = groupByParallelGroup(steps)

          // For each pair of steps with same parallel_group, they should be in same group
          for (let i = 0; i < steps.length; i++) {
            for (let j = i + 1; j < steps.length; j++) {
              const group1 = steps[i].parallel_group ?? null
              const group2 = steps[j].parallel_group ?? null

              if (group1 === group2) {
                // Both should be in the same group
                const groupSteps = groups.get(group1) ?? []
                expect(groupSteps).toContain(steps[i])
                expect(groupSteps).toContain(steps[j])
              }
            }
          }
        }),
        { numRuns: 100 }
      )
    })
  })

  /**
   * Property 5: DAG node color mapping by status
   * For any step with a given status, the rendered node color SHALL match the
   * defined color mapping (running=blue, completed=green, failed=red, pending=gray).
   * **Validates: Requirements 3.3**
   */
  describe('Property 5: DAG node color mapping by status', () => {
    it('should return correct color for each status', () => {
      fc.assert(
        fc.property(stepStatusArbitrary, (status) => {
          const color = getStatusColor(status)

          switch (status) {
            case 'running':
              expect(color).toBe('#3b82f6') // blue
              break
            case 'completed':
              expect(color).toBe('#22c55e') // green
              break
            case 'failed':
              expect(color).toBe('#ef4444') // red
              break
            case 'pending':
            default:
              expect(color).toBe('#9ca3af') // gray
              break
          }
        }),
        { numRuns: 100 }
      )
    })

    it('should return gray for unknown statuses', () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 20 }).filter(
            s => !['running', 'completed', 'failed', 'pending'].includes(s)
          ),
          (unknownStatus) => {
            const color = getStatusColor(unknownStatus)
            expect(color).toBe('#9ca3af') // gray (default)
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should always return a valid hex color', () => {
      fc.assert(
        fc.property(fc.string(), (status) => {
          const color = getStatusColor(status)
          // Should be a valid hex color
          expect(color).toMatch(/^#[0-9a-f]{6}$/i)
        }),
        { numRuns: 100 }
      )
    })
  })

  /**
   * Property 6: DAG duration calculation
   * For any step with both started_at and finished_at timestamps, the displayed
   * duration SHALL equal the difference between these timestamps.
   * **Validates: Requirements 3.6**
   */
  describe('Property 6: DAG duration calculation', () => {
    it('should calculate correct duration for valid timestamps', () => {
      // Use integer timestamps to avoid Date edge cases during shrinking
      const minTime = new Date('2020-01-01').getTime()
      const maxTime = new Date('2025-01-01').getTime()

      fc.assert(
        fc.property(
          fc.integer({ min: minTime, max: maxTime }),
          fc.integer({ min: 1, max: 86400 }), // 1 second to 24 hours in seconds
          (startTimeMs, durationSeconds) => {
            const startedAt = new Date(startTimeMs).toISOString()
            const finishedAt = new Date(startTimeMs + durationSeconds * 1000).toISOString()

            const duration = calculateDuration(startedAt, finishedAt)

            // Duration should not be null for valid timestamps
            expect(duration).not.toBeNull()

            // Verify the duration string contains expected time units
            if (durationSeconds >= 3600) {
              expect(duration).toContain('h')
            } else if (durationSeconds >= 60) {
              expect(duration).toContain('m')
            } else {
              expect(duration).toContain('s')
            }
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should return null for missing timestamps', () => {
      fc.assert(
        fc.property(
          fc.option(validDateArbitrary, { nil: null }),
          fc.option(validDateArbitrary, { nil: null }),
          (startedAt, finishedAt) => {
            // If either timestamp is null, duration should be null
            if (startedAt === null || finishedAt === null) {
              const duration = calculateDuration(startedAt, finishedAt)
              expect(duration).toBeNull()
            }
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should return null for negative duration (end before start)', () => {
      // Use integer timestamps to avoid Date edge cases during shrinking
      const minTime = new Date('2020-01-01').getTime()
      const maxTime = new Date('2025-01-01').getTime()

      fc.assert(
        fc.property(
          fc.integer({ min: minTime, max: maxTime }),
          fc.integer({ min: 1000, max: 86400000 }), // 1 second to 24 hours in milliseconds
          (endTimeMs, durationMs) => {
            // Create a start date that's after the end date
            const finishedAt = new Date(endTimeMs).toISOString()
            const startedAt = new Date(endTimeMs + durationMs).toISOString()

            const duration = calculateDuration(startedAt, finishedAt)
            expect(duration).toBeNull()
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should handle zero duration', () => {
      // Use integer timestamps to avoid Date edge cases during shrinking
      const minTime = new Date('2020-01-01').getTime()
      const maxTime = new Date('2025-01-01').getTime()

      fc.assert(
        fc.property(
          fc.integer({ min: minTime, max: maxTime }),
          (timeMs) => {
            const timestamp = new Date(timeMs).toISOString()
            const duration = calculateDuration(timestamp, timestamp)

            // Zero duration should return "0s"
            expect(duration).toBe('0s')
          }
        ),
        { numRuns: 100 }
      )
    })
  })
})
