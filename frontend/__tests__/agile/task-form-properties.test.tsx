/**
 * Property-Based Tests for Task Form Validation
 * **Feature: frontend-comprehensive-refactor**
 *
 * Property 16: Task form validation
 *
 * **Validates: Requirements 12.2**
 */

import * as fc from "fast-check";
import { describe, expect,it } from "vitest";

import { validateTaskForm } from "@/components/agile/task-form";
import type { AgileTaskCreate, TaskBoardStatus,TaskPriority, TaskType } from "@/lib/api/types";

// Arbitrary generator for task types
const taskTypeArbitrary: fc.Arbitrary<TaskType> = fc.constantFrom(
  "story",
  "bug",
  "task",
  "spike",
  "epic"
);

// Arbitrary generator for task priorities
const taskPriorityArbitrary: fc.Arbitrary<TaskPriority> = fc.constantFrom(
  "critical",
  "high",
  "medium",
  "low"
);

// Arbitrary generator for board statuses
const boardStatusArbitrary: fc.Arbitrary<TaskBoardStatus> = fc.constantFrom(
  "backlog",
  "todo",
  "in_progress",
  "review",
  "testing",
  "done"
);

// Arbitrary generator for non-empty strings (valid titles)
const validTitleArbitrary = fc
  .string({ minLength: 1, maxLength: 200 })
  .filter((s) => s.trim().length > 0);

// Arbitrary generator for empty or whitespace-only strings (invalid titles)
const emptyTitleArbitrary = fc.constantFrom("", "   ", "\t", "\n", "  \t\n  ");

// Arbitrary generator for valid date strings
const validDateArbitrary = fc
  .date({
    min: new Date("2020-01-01"),
    max: new Date("2030-12-31"),
  })
  .map((d) => d.toISOString().split("T")[0]);

// Arbitrary generator for a valid AgileTaskCreate
const validTaskFormArbitrary: fc.Arbitrary<AgileTaskCreate> = fc.record({
  title: validTitleArbitrary,
  description: fc.option(fc.string(), { nil: undefined }),
  task_type: fc.option(taskTypeArbitrary, { nil: undefined }),
  priority: fc.option(taskPriorityArbitrary, { nil: undefined }),
  board_status: fc.option(boardStatusArbitrary, { nil: undefined }),
  story_points: fc.option(fc.nat({ max: 100 }), { nil: undefined }),
  assignee: fc.option(fc.string(), { nil: undefined }),
  sprint_id: fc.option(fc.nat(), { nil: undefined }),
  labels: fc.option(fc.array(fc.string(), { maxLength: 10 }), { nil: undefined }),
  acceptance_criteria: fc.option(fc.array(fc.string(), { maxLength: 20 }), { nil: undefined }),
  due_date: fc.option(validDateArbitrary, { nil: undefined }),
});

// Arbitrary generator for an invalid AgileTaskCreate (empty title)
const invalidTaskFormArbitrary: fc.Arbitrary<AgileTaskCreate> = fc.record({
  title: emptyTitleArbitrary,
  description: fc.option(fc.string(), { nil: undefined }),
  task_type: fc.option(taskTypeArbitrary, { nil: undefined }),
  priority: fc.option(taskPriorityArbitrary, { nil: undefined }),
  board_status: fc.option(boardStatusArbitrary, { nil: undefined }),
  story_points: fc.option(fc.nat({ max: 100 }), { nil: undefined }),
  assignee: fc.option(fc.string(), { nil: undefined }),
  sprint_id: fc.option(fc.nat(), { nil: undefined }),
  labels: fc.option(fc.array(fc.string(), { maxLength: 10 }), { nil: undefined }),
  acceptance_criteria: fc.option(fc.array(fc.string(), { maxLength: 20 }), { nil: undefined }),
  due_date: fc.option(validDateArbitrary, { nil: undefined }),
});

describe("Task Form Validation Property Tests", () => {
  /**
   * Property 16: Task form validation
   * For any task form submission with an empty title, the form SHALL prevent
   * submission and display a validation error.
   * **Validates: Requirements 12.2**
   */
  describe("Property 16: Task form validation", () => {
    it("should reject any form with empty or whitespace-only title", () => {
      fc.assert(
        fc.property(invalidTaskFormArbitrary, (formData) => {
          const result = validateTaskForm(formData);

          // Form should be invalid
          expect(result.isValid).toBe(false);
          // Should have a title error
          expect(result.errors.title).toBeDefined();
          expect(result.errors.title).toBe("Title is required");
        }),
        { numRuns: 100 }
      );
    });

    it("should accept any form with a non-empty title", () => {
      fc.assert(
        fc.property(validTaskFormArbitrary, (formData) => {
          const result = validateTaskForm(formData);

          // Form should be valid
          expect(result.isValid).toBe(true);
          // Should have no errors
          expect(Object.keys(result.errors).length).toBe(0);
        }),
        { numRuns: 100 }
      );
    });

    it("should return consistent validation results for the same input", () => {
      fc.assert(
        fc.property(fc.oneof(validTaskFormArbitrary, invalidTaskFormArbitrary), (formData) => {
          const result1 = validateTaskForm(formData);
          const result2 = validateTaskForm(formData);

          // Results should be identical
          expect(result1.isValid).toBe(result2.isValid);
          expect(result1.errors).toEqual(result2.errors);
        }),
        { numRuns: 100 }
      );
    });

    it("should have errors object when invalid and empty errors when valid", () => {
      fc.assert(
        fc.property(fc.oneof(validTaskFormArbitrary, invalidTaskFormArbitrary), (formData) => {
          const result = validateTaskForm(formData);

          if (result.isValid) {
            // Valid forms should have no errors
            expect(Object.keys(result.errors).length).toBe(0);
          } else {
            // Invalid forms should have at least one error
            expect(Object.keys(result.errors).length).toBeGreaterThan(0);
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should validate title trimming correctly", () => {
      fc.assert(
        fc.property(
          fc.string({ minLength: 1, maxLength: 100 }),
          fc.string({ minLength: 0, maxLength: 10 }).filter((s) => /^\s*$/.test(s)),
          (content, whitespace) => {
            // Title with content surrounded by whitespace should be valid
            const formWithPaddedTitle: AgileTaskCreate = {
              title: whitespace + content + whitespace,
            };
            const result = validateTaskForm(formWithPaddedTitle);

            // Should be valid if content is non-empty after trimming
            if (content.trim().length > 0) {
              expect(result.isValid).toBe(true);
            }
          }
        ),
        { numRuns: 100 }
      );
    });
  });
});
