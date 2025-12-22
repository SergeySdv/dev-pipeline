/**
 * Property-Based Tests for Velocity Chart Component
 * **Feature: frontend-comprehensive-refactor**
 * 
 * Property 9: Velocity average calculation
 * 
 * **Validates: Requirements 6.3**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  calculateVelocityAverage,
  calculateTrendLine,
  type VelocityPoint
} from '@/components/visualizations/velocity-trend-chart'

// Arbitrary generator for sprint names
const sprintNameArbitrary = fc.stringMatching(/^S\d{1,3}$/)

// Arbitrary generator for non-negative velocity values
const velocityArbitrary = fc.nat({ max: 200 })

// Arbitrary generator for a single VelocityPoint
const velocityPointArbitrary: fc.Arbitrary<VelocityPoint> = fc.record({
  sprintName: sprintNameArbitrary,
  velocity: velocityArbitrary,
  sprintId: fc.option(fc.nat({ max: 100 }), { nil: undefined })
})

// Arbitrary generator for a list of VelocityPoints (at least 1 point)
const velocityDataArbitrary = fc.array(velocityPointArbitrary, { minLength: 1, maxLength: 20 })

// Arbitrary generator for a list of VelocityPoints (at least 2 points for trend line)
const velocityDataForTrendArbitrary = fc.array(velocityPointArbitrary, { minLength: 2, maxLength: 20 })

describe('Velocity Chart Property Tests', () => {
  /**
   * Property 9: Velocity average calculation
   * For any velocity data, the displayed average SHALL equal the arithmetic mean
   * of all velocity values.
   * **Validates: Requirements 6.3**
   */
  describe('Property 9: Velocity average calculation', () => {
    it('should calculate correct arithmetic mean for any velocity data', () => {
      fc.assert(
        fc.property(velocityDataArbitrary, (data) => {
          const calculatedAverage = calculateVelocityAverage(data)
          
          // Calculate expected average manually
          const expectedAverage = data.reduce((sum, p) => sum + p.velocity, 0) / data.length
          
          // Should match the arithmetic mean
          expect(calculatedAverage).not.toBeNull()
          expect(calculatedAverage).toBeCloseTo(expectedAverage, 10)
        }),
        { numRuns: 100 }
      )
    })

    it('should return null for empty data', () => {
      const average = calculateVelocityAverage([])
      expect(average).toBeNull()
    })

    it('should handle single data point correctly', () => {
      fc.assert(
        fc.property(velocityPointArbitrary, (point) => {
          const average = calculateVelocityAverage([point])
          
          // Average of single point should equal that point's velocity
          expect(average).toBe(point.velocity)
        }),
        { numRuns: 100 }
      )
    })

    it('should return same value when all velocities are equal', () => {
      fc.assert(
        fc.property(
          velocityArbitrary,
          fc.integer({ min: 1, max: 10 }),
          (velocity, count) => {
            const data: VelocityPoint[] = Array.from({ length: count }, (_, i) => ({
              sprintName: `S${i + 1}`,
              velocity,
              sprintId: i + 1
            }))
            
            const average = calculateVelocityAverage(data)
            
            // Average should equal the common velocity value
            expect(average).toBe(velocity)
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should be bounded by min and max velocities', () => {
      fc.assert(
        fc.property(velocityDataArbitrary, (data) => {
          const average = calculateVelocityAverage(data)
          
          if (average === null) return true
          
          const minVelocity = Math.min(...data.map(p => p.velocity))
          const maxVelocity = Math.max(...data.map(p => p.velocity))
          
          // Average should be between min and max (inclusive)
          expect(average).toBeGreaterThanOrEqual(minVelocity)
          expect(average).toBeLessThanOrEqual(maxVelocity)
        }),
        { numRuns: 100 }
      )
    })
  })

  /**
   * Additional property tests for trend line calculation
   */
  describe('Trend line calculation', () => {
    it('should return empty array for insufficient data', () => {
      expect(calculateTrendLine([])).toEqual([])
      
      fc.assert(
        fc.property(velocityPointArbitrary, (point) => {
          const trend = calculateTrendLine([point])
          expect(trend).toEqual([])
        }),
        { numRuns: 100 }
      )
    })

    it('should return same length array as input for valid data', () => {
      fc.assert(
        fc.property(velocityDataForTrendArbitrary, (data) => {
          const trend = calculateTrendLine(data)
          
          // Trend line should have same number of points as input
          expect(trend.length).toBe(data.length)
        }),
        { numRuns: 100 }
      )
    })

    it('should produce numeric values for all trend points', () => {
      fc.assert(
        fc.property(velocityDataForTrendArbitrary, (data) => {
          const trend = calculateTrendLine(data)
          
          // All trend values should be finite numbers
          trend.forEach(value => {
            expect(typeof value).toBe('number')
            expect(Number.isFinite(value)).toBe(true)
          })
        }),
        { numRuns: 100 }
      )
    })

    it('should produce flat line when all velocities are equal', () => {
      fc.assert(
        fc.property(
          velocityArbitrary,
          fc.integer({ min: 2, max: 10 }),
          (velocity, count) => {
            const data: VelocityPoint[] = Array.from({ length: count }, (_, i) => ({
              sprintName: `S${i + 1}`,
              velocity,
              sprintId: i + 1
            }))
            
            const trend = calculateTrendLine(data)
            
            // All trend values should be approximately equal to the velocity
            trend.forEach(value => {
              expect(value).toBeCloseTo(velocity, 10)
            })
          }
        ),
        { numRuns: 100 }
      )
    })
  })
})
