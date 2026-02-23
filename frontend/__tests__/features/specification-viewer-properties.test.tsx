/**
 * Property-Based Tests for Specification Viewer Component
 * **Feature: frontend-comprehensive-refactor**
 *
 * Property 12: Specification viewer tabs
 *
 * **Validates: Requirements 9.2**
 */

import * as fc from "fast-check";
import { describe, expect,it } from "vitest";

import {
  computeSpecTabs,
  getAvailableTabCount,
  getAvailableTabs,
  isTabEnabled,
  type SpecificationContentData,
  type SpecTabKey,
  validateTabsPresence,
} from "@/components/features/specification-viewer";

// =============================================================================
// Arbitrary Generators
// =============================================================================

// Generator for markdown content (can be null or a string)
const markdownContentArbitrary = fc.option(fc.string({ minLength: 1, maxLength: 500 }), {
  nil: null,
});

// Generator for specification content data
const specificationContentArbitrary: fc.Arbitrary<SpecificationContentData> = fc.record({
  id: fc.option(fc.nat(), { nil: undefined }),
  path: fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: undefined }),
  title: fc.option(fc.string({ minLength: 1, maxLength: 100 }), { nil: undefined }),
  spec_content: markdownContentArbitrary,
  plan_content: markdownContentArbitrary,
  tasks_content: markdownContentArbitrary,
  checklist_content: markdownContentArbitrary,
});

// Generator for specification content with multiple files (at least 2)
const specificationContentWithMultipleFilesArbitrary: fc.Arbitrary<SpecificationContentData> = fc
  .tuple(
    fc.string({ minLength: 1, maxLength: 500 }),
    fc.string({ minLength: 1, maxLength: 500 }),
    markdownContentArbitrary,
    markdownContentArbitrary
  )
  .map(([spec, plan, tasks, checklist]) => ({
    spec_content: spec,
    plan_content: plan,
    tasks_content: tasks,
    checklist_content: checklist,
  }));

// =============================================================================
// Property Tests
// =============================================================================

describe("Specification Viewer Property Tests", () => {
  /**
   * Property 12: Specification viewer tabs
   * For any specification with multiple files, the viewer SHALL render a tab
   * for each available file type (spec, plan, tasks, checklist).
   * **Validates: Requirements 9.2**
   */
  describe("Property 12: Specification viewer tabs", () => {
    it("should always produce exactly 4 tabs for any specification content", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);

          // Should always produce exactly 4 tabs
          expect(tabs).toHaveLength(4);
        }),
        { numRuns: 100 }
      );
    });

    it("should always include all 4 tab types (spec, plan, tasks, checklist)", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);
          const validation = validateTabsPresence(tabs);

          // All tab types should be present
          expect(validation.allTabTypesPresent).toBe(true);
          expect(validation.hasSpecTab).toBe(true);
          expect(validation.hasPlanTab).toBe(true);
          expect(validation.hasTasksTab).toBe(true);
          expect(validation.hasChecklistTab).toBe(true);
        }),
        { numRuns: 100 }
      );
    });

    it("should preserve content mapping from data to tabs", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);

          // Find each tab and verify content mapping
          const specTab = tabs.find((t) => t.key === "spec");
          const planTab = tabs.find((t) => t.key === "plan");
          const tasksTab = tabs.find((t) => t.key === "tasks");
          const checklistTab = tabs.find((t) => t.key === "checklist");

          expect(specTab?.content).toBe(data.spec_content ?? null);
          expect(planTab?.content).toBe(data.plan_content ?? null);
          expect(tasksTab?.content).toBe(data.tasks_content ?? null);
          expect(checklistTab?.content).toBe(data.checklist_content ?? null);
        }),
        { numRuns: 100 }
      );
    });

    it("should correctly identify enabled tabs based on content presence", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);

          for (const tab of tabs) {
            const enabled = isTabEnabled(tab);
            // Tab should be enabled if and only if content is not null
            expect(enabled).toBe(tab.content !== null);
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should count available tabs correctly", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);
          const availableCount = getAvailableTabCount(tabs);

          // Count should match number of non-null content fields
          let expectedCount = 0;
          if (data.spec_content !== null) expectedCount++;
          if (data.plan_content !== null) expectedCount++;
          if (data.tasks_content !== null) expectedCount++;
          if (data.checklist_content !== null) expectedCount++;

          expect(availableCount).toBe(expectedCount);
        }),
        { numRuns: 100 }
      );
    });

    it("should return only tabs with content from getAvailableTabs", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);
          const availableTabs = getAvailableTabs(tabs);

          // All returned tabs should have content
          for (const tab of availableTabs) {
            expect(tab.content).not.toBeNull();
          }

          // Count should match getAvailableTabCount
          expect(availableTabs.length).toBe(getAvailableTabCount(tabs));
        }),
        { numRuns: 100 }
      );
    });

    it("should have correct labels for each tab type", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);

          const expectedLabels: Record<SpecTabKey, string> = {
            spec: "Spec",
            plan: "Plan",
            tasks: "Tasks",
            checklist: "Checklist",
          };

          for (const tab of tabs) {
            expect(tab.label).toBe(expectedLabels[tab.key]);
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should handle null/undefined data gracefully", () => {
      // Test with null
      const tabsFromNull = computeSpecTabs(null);
      expect(tabsFromNull).toHaveLength(4);
      expect(tabsFromNull.every((t) => t.content === null)).toBe(true);

      // Test with undefined
      const tabsFromUndefined = computeSpecTabs(undefined);
      expect(tabsFromUndefined).toHaveLength(4);
      expect(tabsFromUndefined.every((t) => t.content === null)).toBe(true);
    });

    it("should maintain tab order consistently", () => {
      fc.assert(
        fc.property(specificationContentArbitrary, (data) => {
          const tabs = computeSpecTabs(data);

          // Tabs should always be in the same order
          expect(tabs[0].key).toBe("spec");
          expect(tabs[1].key).toBe("plan");
          expect(tabs[2].key).toBe("tasks");
          expect(tabs[3].key).toBe("checklist");
        }),
        { numRuns: 100 }
      );
    });

    it("should have at least one available tab when spec has multiple files", () => {
      fc.assert(
        fc.property(specificationContentWithMultipleFilesArbitrary, (data) => {
          const tabs = computeSpecTabs(data);
          const availableCount = getAvailableTabCount(tabs);

          // With multiple files, should have at least 2 available tabs
          expect(availableCount).toBeGreaterThanOrEqual(2);
        }),
        { numRuns: 100 }
      );
    });
  });
});
