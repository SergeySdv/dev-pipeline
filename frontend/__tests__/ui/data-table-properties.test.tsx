/**
 * Property-Based Tests for Data Table Filtering
 * **Feature: frontend-comprehensive-refactor**
 *
 * Property 17: Data table search filtering
 *
 * **Validates: Requirements 14.2, 14.3**
 */

import * as fc from "fast-check";
import { describe, expect,it } from "vitest";

import {
  type ColumnFilter,
  createAccessorKeyMap,
  filterTableData,
  getRowValue,
  rowMatchesGlobalSearch,
  valueToSearchString,
} from "@/lib/utils/data-table-filtering";

// Arbitrary generator for simple row data
interface TestRow {
  id: number;
  name: string;
  status: string;
  count: number;
  active: boolean;
  metadata?: {
    category: string;
    priority: number;
  };
}

const testRowArbitrary: fc.Arbitrary<TestRow> = fc.record({
  id: fc.nat({ min: 1, max: 100000 }),
  name: fc.string({ minLength: 1, maxLength: 100 }),
  status: fc.constantFrom("pending", "active", "completed", "failed", "cancelled"),
  count: fc.integer({ min: 0, max: 1000 }),
  active: fc.boolean(),
  metadata: fc.option(
    fc.record({
      category: fc.constantFrom("A", "B", "C", "D"),
      priority: fc.integer({ min: 1, max: 5 }),
    }),
    { nil: undefined }
  ),
});

// Arbitrary generator for array of test rows
const testRowsArbitrary = fc.array(testRowArbitrary, { minLength: 0, maxLength: 50 });

// Arbitrary generator for search queries
const searchQueryArbitrary = fc.oneof(
  fc.constant(""),
  fc.string({ minLength: 1, maxLength: 20 }),
  // Include some realistic search terms
  fc.constantFrom("pending", "active", "completed", "test", "123", "true", "false")
);

// Arbitrary generator for column filter values
const columnFilterValueArbitrary = fc.oneof(
  fc.constant(""),
  fc.string({ minLength: 1, maxLength: 20 }),
  fc.constantFrom("pending", "active", "A", "B", "1", "2", "3")
);

// Standard accessor key map for test rows
const standardAccessorKeyMap = createAccessorKeyMap([
  { columnId: "id", accessorKey: "id" },
  { columnId: "name", accessorKey: "name" },
  { columnId: "status", accessorKey: "status" },
  { columnId: "count", accessorKey: "count" },
  { columnId: "active", accessorKey: "active" },
  { columnId: "category", accessorKey: "metadata.category" },
]);

describe("Data Table Property Tests", () => {
  /**
   * Property 17: Data table search filtering
   * For any search term entered in the data table, all displayed rows SHALL contain
   * the search term in at least one searchable column.
   * **Validates: Requirements 14.2, 14.3**
   */
  describe("Property 17: Data table search filtering", () => {
    it("should return all rows when search query is empty", () => {
      fc.assert(
        fc.property(testRowsArbitrary, (rows) => {
          const filtered = filterTableData(rows, "", [], standardAccessorKeyMap);

          // Empty search should return all rows
          expect(filtered.length).toBe(rows.length);
          expect(filtered).toEqual(rows);
        }),
        { numRuns: 100 }
      );
    });

    it("should return all rows when search query is whitespace only", () => {
      fc.assert(
        fc.property(
          testRowsArbitrary,
          fc.constantFrom("   ", "\t", "\n", "  \t  ", "\n\n"),
          (rows, whitespace) => {
            const filtered = filterTableData(rows, whitespace, [], standardAccessorKeyMap);

            // Whitespace-only search should return all rows
            expect(filtered.length).toBe(rows.length);
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should only return rows containing the search term", () => {
      fc.assert(
        fc.property(testRowsArbitrary, searchQueryArbitrary, (rows, query) => {
          const filtered = filterTableData(rows, query, [], standardAccessorKeyMap);
          const normalizedQuery = query.trim().toLowerCase();

          if (!normalizedQuery) {
            // Empty query returns all rows
            expect(filtered.length).toBe(rows.length);
          } else {
            // All filtered rows should contain the search term
            for (const row of filtered) {
              const rowString = JSON.stringify(row).toLowerCase();
              expect(rowString).toContain(normalizedQuery);
            }
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should return subset of original rows when filtering", () => {
      fc.assert(
        fc.property(testRowsArbitrary, searchQueryArbitrary, (rows, query) => {
          const filtered = filterTableData(rows, query, [], standardAccessorKeyMap);

          // Filtered result should never be larger than original
          expect(filtered.length).toBeLessThanOrEqual(rows.length);
        }),
        { numRuns: 100 }
      );
    });

    it("should preserve row order when filtering", () => {
      fc.assert(
        fc.property(testRowsArbitrary, searchQueryArbitrary, (rows, query) => {
          const filtered = filterTableData(rows, query, [], standardAccessorKeyMap);

          // Check that filtered rows maintain their relative order
          const filteredIds = filtered.map((r) => r.id);
          const normalizedQuery = query.trim().toLowerCase();
          const expectedIds = rows
            .filter(
              (r) => !normalizedQuery || JSON.stringify(r).toLowerCase().includes(normalizedQuery)
            )
            .map((r) => r.id);

          expect(filteredIds).toEqual(expectedIds);
        }),
        { numRuns: 100 }
      );
    });

    it("should be case-insensitive", () => {
      fc.assert(
        fc.property(
          testRowsArbitrary,
          fc.string({ minLength: 1, maxLength: 10 }),
          (rows, query) => {
            const lowerFiltered = filterTableData(
              rows,
              query.toLowerCase(),
              [],
              standardAccessorKeyMap
            );
            const upperFiltered = filterTableData(
              rows,
              query.toUpperCase(),
              [],
              standardAccessorKeyMap
            );
            const mixedFiltered = filterTableData(rows, query, [], standardAccessorKeyMap);

            // All case variations should return the same results
            expect(lowerFiltered.length).toBe(upperFiltered.length);
            expect(lowerFiltered.length).toBe(mixedFiltered.length);
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should be idempotent - filtering twice gives same result", () => {
      fc.assert(
        fc.property(testRowsArbitrary, searchQueryArbitrary, (rows, query) => {
          const filtered1 = filterTableData(rows, query, [], standardAccessorKeyMap);
          const filtered2 = filterTableData(filtered1, query, [], standardAccessorKeyMap);

          // Filtering twice should give the same result
          expect(filtered2).toEqual(filtered1);
        }),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Column filter tests
   * **Validates: Requirements 14.3**
   */
  describe("Column-level filtering", () => {
    it("should return all rows when column filters are empty", () => {
      fc.assert(
        fc.property(testRowsArbitrary, (rows) => {
          const filtered = filterTableData(rows, "", [], standardAccessorKeyMap);

          expect(filtered.length).toBe(rows.length);
          expect(filtered).toEqual(rows);
        }),
        { numRuns: 100 }
      );
    });

    it("should filter by specific column value", () => {
      fc.assert(
        fc.property(testRowsArbitrary, columnFilterValueArbitrary, (rows, filterValue) => {
          const columnFilters: ColumnFilter[] = [{ columnId: "status", value: filterValue }];
          const filtered = filterTableData(rows, "", columnFilters, standardAccessorKeyMap);
          const normalizedValue = filterValue.trim().toLowerCase();

          if (!normalizedValue) {
            // Empty filter returns all rows
            expect(filtered.length).toBe(rows.length);
          } else {
            // All filtered rows should have status containing the filter value
            for (const row of filtered) {
              expect(row.status.toLowerCase()).toContain(normalizedValue);
            }
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should apply multiple column filters with AND logic", () => {
      fc.assert(
        fc.property(
          testRowsArbitrary,
          columnFilterValueArbitrary,
          columnFilterValueArbitrary,
          (rows, statusFilter, nameFilter) => {
            const columnFilters: ColumnFilter[] = [
              { columnId: "status", value: statusFilter },
              { columnId: "name", value: nameFilter },
            ];
            const filtered = filterTableData(rows, "", columnFilters, standardAccessorKeyMap);

            const normalizedStatus = statusFilter.trim().toLowerCase();
            const normalizedName = nameFilter.trim().toLowerCase();

            // All filtered rows should match ALL active filters
            for (const row of filtered) {
              if (normalizedStatus) {
                expect(row.status.toLowerCase()).toContain(normalizedStatus);
              }
              if (normalizedName) {
                expect(row.name.toLowerCase()).toContain(normalizedName);
              }
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should combine global search with column filters", () => {
      fc.assert(
        fc.property(
          testRowsArbitrary,
          searchQueryArbitrary,
          columnFilterValueArbitrary,
          (rows, globalSearch, columnFilter) => {
            const columnFilters: ColumnFilter[] = [{ columnId: "status", value: columnFilter }];
            const filtered = filterTableData(
              rows,
              globalSearch,
              columnFilters,
              standardAccessorKeyMap
            );

            const normalizedSearch = globalSearch.trim().toLowerCase();
            const normalizedColumn = columnFilter.trim().toLowerCase();

            // All filtered rows should match both global search AND column filter
            for (const row of filtered) {
              if (normalizedSearch) {
                expect(JSON.stringify(row).toLowerCase()).toContain(normalizedSearch);
              }
              if (normalizedColumn) {
                expect(row.status.toLowerCase()).toContain(normalizedColumn);
              }
            }
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should handle nested accessor keys", () => {
      fc.assert(
        fc.property(testRowsArbitrary, (rows) => {
          // Filter by nested metadata.category
          const columnFilters: ColumnFilter[] = [{ columnId: "category", value: "A" }];
          const filtered = filterTableData(rows, "", columnFilters, standardAccessorKeyMap);

          // All filtered rows should have metadata.category containing 'A'
          for (const row of filtered) {
            expect(row.metadata?.category?.toLowerCase()).toContain("a");
          }
        }),
        { numRuns: 100 }
      );
    });

    it("should ignore filters for non-existent columns", () => {
      fc.assert(
        fc.property(testRowsArbitrary, (rows) => {
          const columnFilters: ColumnFilter[] = [{ columnId: "nonexistent", value: "test" }];
          const filtered = filterTableData(rows, "", columnFilters, standardAccessorKeyMap);

          // Non-existent column filter should not filter anything
          expect(filtered.length).toBe(rows.length);
        }),
        { numRuns: 100 }
      );
    });
  });

  /**
   * Utility function tests
   */
  describe("getRowValue utility", () => {
    it("should return undefined for null/undefined rows", () => {
      expect(getRowValue(null, "key")).toBeUndefined();
      expect(getRowValue(undefined, "key")).toBeUndefined();
    });

    it("should return direct property value", () => {
      fc.assert(
        fc.property(
          // Use alphanumeric keys to avoid edge cases with dots
          fc
            .string({ minLength: 1, maxLength: 20 })
            .filter((s) => !s.includes(".") && s.trim().length > 0),
          fc.string(),
          (key, value) => {
            const row = { [key]: value };
            expect(getRowValue(row, key)).toBe(value);
          }
        ),
        { numRuns: 100 }
      );
    });

    it("should return nested property value", () => {
      fc.assert(
        fc.property(
          // Use alphanumeric keys to avoid edge cases with dots
          fc
            .string({ minLength: 1, maxLength: 10 })
            .filter((s) => !s.includes(".") && s.trim().length > 0),
          fc
            .string({ minLength: 1, maxLength: 10 })
            .filter((s) => !s.includes(".") && s.trim().length > 0),
          fc.string(),
          (key1, key2, value) => {
            const row = { [key1]: { [key2]: value } };
            expect(getRowValue(row, `${key1}.${key2}`)).toBe(value);
          }
        ),
        { numRuns: 100 }
      );
    });
  });

  describe("valueToSearchString utility", () => {
    it("should return string values as-is", () => {
      fc.assert(
        fc.property(fc.string(), (value) => {
          expect(valueToSearchString(value)).toBe(value);
        }),
        { numRuns: 100 }
      );
    });

    it("should convert numbers to strings", () => {
      fc.assert(
        fc.property(fc.integer(), (value) => {
          expect(valueToSearchString(value)).toBe(String(value));
        }),
        { numRuns: 100 }
      );
    });

    it("should convert booleans to strings", () => {
      fc.assert(
        fc.property(fc.boolean(), (value) => {
          expect(valueToSearchString(value)).toBe(String(value));
        }),
        { numRuns: 100 }
      );
    });

    it("should return empty string for null/undefined", () => {
      expect(valueToSearchString(null)).toBe("");
      expect(valueToSearchString(undefined)).toBe("");
    });
  });

  describe("rowMatchesGlobalSearch utility", () => {
    it("should return true for empty query", () => {
      fc.assert(
        fc.property(testRowArbitrary, (row) => {
          expect(rowMatchesGlobalSearch(row, "")).toBe(true);
          expect(rowMatchesGlobalSearch(row, "   ")).toBe(true);
        }),
        { numRuns: 100 }
      );
    });

    it("should match when query is found in row", () => {
      fc.assert(
        fc.property(testRowArbitrary, (row) => {
          // Search for the row's status - should always match
          expect(rowMatchesGlobalSearch(row, row.status)).toBe(true);
        }),
        { numRuns: 100 }
      );
    });
  });
});
