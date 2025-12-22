/**
 * Property-Based Tests for Quality Gates Drilldown Component
 * **Feature: frontend-comprehensive-refactor**
 * 
 * Property 11: Quality gates listing completeness
 * 
 * **Validates: Requirements 8.1, 8.3**
 */

import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import {
  computeQualityGateListItemData,
  validateQualityGateListItemCompleteness,
  getStatusMeta,
  getSeverityFromFinding,
  getMaxSeverity,
  getSeverityBadgeProps,
  type QualityGateFinding,
  type FindingSeverity,
} from '@/components/features/quality-gates-drilldown'
import type { ProtocolQualityGate } from '@/lib/api/hooks/use-quality'

// Arbitrary generator for gate articles
const articleArbitrary = fc.string({ minLength: 1, maxLength: 20 })
  .filter(s => s.trim().length > 0)

// Arbitrary generator for gate names
const gateNameArbitrary = fc.string({ minLength: 1, maxLength: 100 })
  .filter(s => s.trim().length > 0)

// Arbitrary generator for gate status
const gateStatusArbitrary = fc.constantFrom('passed', 'warning', 'failed', 'skipped')

// Arbitrary generator for severity levels
const severityArbitrary = fc.constantFrom('critical', 'high', 'medium', 'low', 'info', undefined)

// Arbitrary generator for a finding
const findingArbitrary: fc.Arbitrary<QualityGateFinding> = fc.record({
  severity: severityArbitrary,
  message: fc.option(fc.string({ minLength: 1, maxLength: 200 }), { nil: undefined }),
})

// Arbitrary generator for a valid ProtocolQualityGate
const qualityGateArbitrary: fc.Arbitrary<ProtocolQualityGate> = fc.record({
  article: articleArbitrary,
  name: gateNameArbitrary,
  status: gateStatusArbitrary,
  findings: fc.array(findingArbitrary as fc.Arbitrary<Record<string, unknown>>, { maxLength: 10 }),
})

describe('Quality Gates Drilldown Property Tests', () => {
  /**
   * Property 11: Quality gates listing completeness
   * For any quality gate, the rendered list item SHALL display the gate name,
   * pass/fail status, and severity indicator for any findings.
   * **Validates: Requirements 8.1, 8.3**
   */
  describe('Property 11: Quality gates listing completeness', () => {
    it('should always produce complete list item data for any valid quality gate', () => {
      fc.assert(
        fc.property(qualityGateArbitrary, (gate) => {
          const itemData = computeQualityGateListItemData(gate)
          const validation = validateQualityGateListItemCompleteness(itemData)
          
          // List item should always be complete
          expect(validation.isComplete).toBe(true)
          expect(validation.hasName).toBe(true)
          expect(validation.hasStatus).toBe(true)
        }),
        { numRuns: 100 }
      )
    })

    it('should preserve gate name in list item data', () => {
      fc.assert(
        fc.property(qualityGateArbitrary, (gate) => {
          const itemData = computeQualityGateListItemData(gate)
          
          // Name should be preserved from gate
          expect(itemData.name).toBe(gate.name)
        }),
        { numRuns: 100 }
      )
    })

    it('should preserve gate article in list item data', () => {
      fc.assert(
        fc.property(qualityGateArbitrary, (gate) => {
          const itemData = computeQualityGateListItemData(gate)
          
          // Article should be preserved from gate
          expect(itemData.article).toBe(gate.article)
        }),
        { numRuns: 100 }
      )
    })

    it('should preserve gate status in list item data', () => {
      fc.assert(
        fc.property(qualityGateArbitrary, (gate) => {
          const itemData = computeQualityGateListItemData(gate)
          
          // Status should be preserved from gate
          expect(itemData.status).toBe(gate.status)
        }),
        { numRuns: 100 }
      )
    })

    it('should correctly count findings', () => {
      fc.assert(
        fc.property(qualityGateArbitrary, (gate) => {
          const itemData = computeQualityGateListItemData(gate)
          
          // Findings count should match the array length
          expect(itemData.findingsCount).toBe(gate.findings.length)
        }),
        { numRuns: 100 }
      )
    })

    it('should have valid status metadata for any status', () => {
      fc.assert(
        fc.property(gateStatusArbitrary, (status) => {
          const meta = getStatusMeta(status)
          
          // Status metadata should always have required fields
          expect(typeof meta.label).toBe('string')
          expect(meta.label.length).toBeGreaterThan(0)
          expect(typeof meta.className).toBe('string')
          expect(meta.icon).toBeDefined()
        }),
        { numRuns: 100 }
      )
    })

    it('should correctly identify severity from findings', () => {
      const validSeverities: FindingSeverity[] = ['critical', 'high', 'medium', 'low', 'info', 'unknown']
      
      fc.assert(
        fc.property(findingArbitrary, (finding) => {
          const severity = getSeverityFromFinding(finding)
          
          // Severity should be one of the valid values
          expect(validSeverities).toContain(severity)
        }),
        { numRuns: 100 }
      )
    })

    it('should return highest severity from multiple findings', () => {
      const severityOrder: FindingSeverity[] = ['critical', 'high', 'medium', 'low', 'info', 'unknown']
      
      fc.assert(
        fc.property(
          fc.array(findingArbitrary, { minLength: 1, maxLength: 10 }),
          (findings) => {
            const maxSeverity = getMaxSeverity(findings)
            
            // Max severity should be the highest (lowest index) among all findings
            const findingSeverities = findings.map(f => getSeverityFromFinding(f))
            const expectedMaxIndex = Math.min(...findingSeverities.map(s => severityOrder.indexOf(s)))
            const expectedMax = severityOrder[expectedMaxIndex]
            
            expect(maxSeverity).toBe(expectedMax)
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should return unknown severity for empty findings array', () => {
      const maxSeverity = getMaxSeverity([])
      expect(maxSeverity).toBe('unknown')
    })

    it('should have severity indicator when findings have known severity', () => {
      fc.assert(
        fc.property(
          fc.record({
            article: articleArbitrary,
            name: gateNameArbitrary,
            status: gateStatusArbitrary,
            findings: fc.array(
              fc.record({
                severity: fc.constantFrom('critical', 'high', 'medium', 'low', 'info'),
                message: fc.option(fc.string(), { nil: undefined }),
              }) as fc.Arbitrary<Record<string, unknown>>,
              { minLength: 1, maxLength: 5 }
            ),
          }),
          (gate) => {
            const itemData = computeQualityGateListItemData(gate)
            
            // Should have severity indicator when findings have known severity
            expect(itemData.hasSeverityIndicator).toBe(true)
            expect(itemData.maxSeverity).not.toBe('unknown')
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should provide valid badge props for any severity', () => {
      const validSeverities: FindingSeverity[] = ['critical', 'high', 'medium', 'low', 'info', 'unknown']
      
      fc.assert(
        fc.property(fc.constantFrom(...validSeverities), (severity) => {
          const badgeProps = getSeverityBadgeProps(severity)
          
          // Badge props should have valid variant
          expect(['destructive', 'secondary', 'outline']).toContain(badgeProps.variant)
          expect(typeof badgeProps.className).toBe('string')
        }),
        { numRuns: 100 }
      )
    })
  })
})
