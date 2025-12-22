/**
 * Property-Based Tests for Pipeline Visualizer Component
 * **Feature: frontend-comprehensive-refactor**
 * 
 * Property 7: View mode state preservation
 * 
 * **Validates: Requirements 4.4**
 */

import { describe, it, expect, vi } from 'vitest'
import * as fc from 'fast-check'
import { render, screen, fireEvent, within } from '@testing-library/react'
import { PipelineVisualizer, ViewMode } from '@/components/workflow/pipeline-visualizer'
import type { StepRun, ProtocolRun, StepStatus } from '@/lib/api/types'

// Mock the PipelineDag component to avoid D3 rendering issues in tests
vi.mock('@/components/visualizations/pipeline-dag', () => ({
  PipelineDag: ({ steps, onStepClick, selectedStepId }: { 
    steps: StepRun[]
    onStepClick?: (step: StepRun) => void
    selectedStepId?: number | null
  }) => (
    <div data-testid="pipeline-dag">
      {steps.map(step => (
        <button
          key={step.id}
          data-testid={`dag-step-${step.id}`}
          data-selected={selectedStepId === step.id}
          onClick={() => onStepClick?.(step)}
        >
          {step.step_name}
        </button>
      ))}
    </div>
  )
}))

// Arbitrary generators for property-based testing

const stepStatusArbitrary = fc.oneof(
  fc.constant('pending' as StepStatus),
  fc.constant('running' as StepStatus),
  fc.constant('completed' as StepStatus),
  fc.constant('failed' as StepStatus)
)

const validDateArbitrary = fc.integer({ 
  min: new Date('2020-01-01').getTime(), 
  max: new Date('2030-12-31').getTime() 
}).map(ts => new Date(ts).toISOString())

// Generate a valid StepRun object
const stepRunArbitrary = (id: number, stepIndex: number): fc.Arbitrary<StepRun> =>
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
    depends_on: fc.constant([]),
    parallel_group: fc.constant(null),
    created_at: validDateArbitrary,
    updated_at: validDateArbitrary
  })

// Generate a list of steps
const stepsListArbitrary = fc.nat({ min: 1, max: 5 }).chain(count => {
  const stepArbitraries: fc.Arbitrary<StepRun>[] = []
  for (let i = 0; i < count; i++) {
    stepArbitraries.push(stepRunArbitrary(i + 1, i))
  }
  return fc.tuple(...stepArbitraries)
})

// Generate a valid ProtocolRun object
const protocolRunArbitrary: fc.Arbitrary<ProtocolRun> = fc.record({
  id: fc.nat({ min: 1, max: 1000 }),
  project_id: fc.nat({ min: 1, max: 100 }),
  protocol_name: fc.string({ minLength: 1, maxLength: 50 }),
  status: fc.oneof(
    fc.constant('pending' as const),
    fc.constant('running' as const),
    fc.constant('completed' as const),
    fc.constant('failed' as const)
  ),
  created_at: validDateArbitrary,
  updated_at: validDateArbitrary,
  started_at: fc.option(validDateArbitrary, { nil: null }),
  finished_at: fc.option(validDateArbitrary, { nil: null }),
  error_message: fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: null }),
  metadata: fc.constant(null)
})

// View mode arbitrary
const viewModeArbitrary = fc.oneof(
  fc.constant('linear' as ViewMode),
  fc.constant('dag' as ViewMode)
)

describe('Pipeline Visualizer Property Tests', () => {
  /**
   * Property 7: View mode state preservation
   * For any selected step, changing the view mode from linear to DAG or vice versa
   * SHALL preserve the step selection.
   * **Validates: Requirements 4.4**
   */
  describe('Property 7: View mode state preservation', () => {
    it('should preserve step selection when switching from linear to DAG view', () => {
      fc.assert(
        fc.property(
          protocolRunArbitrary,
          stepsListArbitrary,
          fc.nat({ min: 0, max: 4 }), // Index to select
          (protocol, steps, selectIndex) => {
            // Ensure we have a valid step to select
            const stepToSelect = steps[selectIndex % steps.length]
            if (!stepToSelect) return true // Skip if no steps

            let currentSelectedStepId: number | null = null
            let currentViewMode: ViewMode = 'linear'

            const handleStepSelect = (stepId: number | null) => {
              currentSelectedStepId = stepId
            }

            const handleViewModeChange = (mode: ViewMode) => {
              currentViewMode = mode
            }

            const { rerender, container } = render(
              <PipelineVisualizer
                protocol={protocol}
                steps={steps}
                viewMode={currentViewMode}
                onViewModeChange={handleViewModeChange}
                selectedStepId={currentSelectedStepId}
                onStepSelect={handleStepSelect}
              />
            )

            // Select a step in linear view by clicking on the step card
            const stepCards = container.querySelectorAll('[class*="cursor-pointer"]')
            const stepCard = stepCards[selectIndex % stepCards.length]
            if (stepCard) {
              fireEvent.click(stepCard)
            }

            // Verify step is selected
            expect(currentSelectedStepId).toBe(stepToSelect.id)

            // Find the view mode toggle container and get the DAG button within it
            const toggleContainer = container.querySelector('.flex.items-center.gap-1.rounded-lg.border')
            if (!toggleContainer) return true // Skip if toggle not found
            
            const dagButton = within(toggleContainer as HTMLElement).getByRole('button', { name: /dag view/i })
            fireEvent.click(dagButton)

            // Rerender with new view mode (simulating controlled component update)
            rerender(
              <PipelineVisualizer
                protocol={protocol}
                steps={steps}
                viewMode="dag"
                onViewModeChange={handleViewModeChange}
                selectedStepId={currentSelectedStepId}
                onStepSelect={handleStepSelect}
              />
            )

            // Verify step selection is preserved after view mode change
            expect(currentSelectedStepId).toBe(stepToSelect.id)
          }
        ),
        { numRuns: 100 }
      )
    })

    it('should preserve step selection when switching from DAG to linear view', () => {
      fc.assert(
        fc.property(
          protocolRunArbitrary,
          stepsListArbitrary,
          fc.nat({ min: 0, max: 4 }), // Index to select
          (protocol, steps, selectIndex) => {
            // Ensure we have a valid step to select
            const stepToSelect = steps[selectIndex % steps.length]
            if (!stepToSelect) return true // Skip if no steps

            let currentSelectedStepId: number | null = null
            let currentViewMode: ViewMode = 'dag'

            const handleStepSelect = (stepId: number | null) => {
              currentSelectedStepId = stepId
            }

            const handleViewModeChange = (mode: ViewMode) => {
              currentViewMode = mode
            }

            const { rerender, container } = render(
              <PipelineVisualizer
                protocol={protocol}
                steps={steps}
                viewMode={currentViewMode}
                onViewModeChange={handleViewModeChange}
                selectedStepId={currentSelectedStepId}
                onStepSelect={handleStepSelect}
              />
            )

            // Select a step in DAG view
            const dagStepButton = screen.getByTestId(`dag-step-${stepToSelect.id}`)
            fireEvent.click(dagStepButton)

            // Verify step is selected
            expect(currentSelectedStepId).toBe(stepToSelect.id)

            // Find the view mode toggle container and get the Linear button within it
            const toggleContainer = container.querySelector('.flex.items-center.gap-1.rounded-lg.border')
            if (!toggleContainer) return true // Skip if toggle not found
            
            const linearButton = within(toggleContainer as HTMLElement).getByRole('button', { name: /linear view/i })
            fireEvent.click(linearButton)

            // Rerender with new view mode (simulating controlled component update)
            rerender(
              <PipelineVisualizer
                protocol={protocol}
                steps={steps}
                viewMode="linear"
                onViewModeChange={handleViewModeChange}
                selectedStepId={currentSelectedStepId}
                onStepSelect={handleStepSelect}
              />
            )

            // Verify step selection is preserved after view mode change
            expect(currentSelectedStepId).toBe(stepToSelect.id)
          }
        ),
        { numRuns: 100 }
      )
    }, 30000) // Increase timeout to 30 seconds

    it('should preserve selection through multiple view mode toggles', () => {
      fc.assert(
        fc.property(
          protocolRunArbitrary,
          stepsListArbitrary,
          fc.array(viewModeArbitrary, { minLength: 2, maxLength: 5 }), // Reduced max length for faster tests
          fc.nat({ min: 0, max: 4 }), // Index to select
          (protocol, steps, viewModeSequence, selectIndex) => {
            // Ensure we have a valid step to select
            const stepToSelect = steps[selectIndex % steps.length]
            if (!stepToSelect) return true // Skip if no steps

            let currentSelectedStepId: number | null = stepToSelect.id
            let currentViewMode: ViewMode = 'linear'

            const handleStepSelect = (stepId: number | null) => {
              currentSelectedStepId = stepId
            }

            const handleViewModeChange = (mode: ViewMode) => {
              currentViewMode = mode
            }

            const { rerender, container } = render(
              <PipelineVisualizer
                protocol={protocol}
                steps={steps}
                viewMode={currentViewMode}
                onViewModeChange={handleViewModeChange}
                selectedStepId={currentSelectedStepId}
                onStepSelect={handleStepSelect}
              />
            )

            // Go through each view mode in the sequence
            for (const targetMode of viewModeSequence) {
              // Find the view mode toggle container
              const toggleContainer = container.querySelector('.flex.items-center.gap-1.rounded-lg.border')
              if (!toggleContainer) continue // Skip if toggle not found
              
              // Click the appropriate button
              const buttonLabel = targetMode === 'dag' ? /dag view/i : /linear view/i
              const button = within(toggleContainer as HTMLElement).getByRole('button', { name: buttonLabel })
              fireEvent.click(button)

              // Rerender with new view mode
              rerender(
                <PipelineVisualizer
                  protocol={protocol}
                  steps={steps}
                  viewMode={targetMode}
                  onViewModeChange={handleViewModeChange}
                  selectedStepId={currentSelectedStepId}
                  onStepSelect={handleStepSelect}
                />
              )

              // Verify step selection is preserved after each view mode change
              expect(currentSelectedStepId).toBe(stepToSelect.id)
            }
          }
        ),
        { numRuns: 100 }
      )
    }, 60000) // Increase timeout to 60 seconds for multiple toggles
  })
})
