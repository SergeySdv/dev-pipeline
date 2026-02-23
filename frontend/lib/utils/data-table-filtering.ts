/**
 * Data Table Filtering Utilities
 *
 * Extracted filtering logic from DataTable component for testability.
 * These functions implement the search and column filter logic.
 */

export interface ColumnFilterConfig {
  columnId: string;
  accessorKey: string;
}

export interface ColumnFilter {
  columnId: string;
  value: string;
}

/**
 * Gets a value from a row object using a dot-notation accessor key.
 * Supports nested properties like "user.name" or "metadata.status".
 */
export function getRowValue(row: unknown, accessorKey: string): unknown {
  if (!row || typeof row !== "object") return undefined;
  if (!accessorKey.includes(".")) return (row as Record<string, unknown>)[accessorKey];
  return accessorKey.split(".").reduce<unknown>((acc, key) => {
    if (!acc || typeof acc !== "object") return undefined;
    return (acc as Record<string, unknown>)[key];
  }, row);
}

/**
 * Converts a value to a searchable string representation.
 */
export function valueToSearchString(value: unknown): string {
  if (typeof value === "string") return value;
  if (value == null) return "";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

/**
 * Checks if a row matches a global search query.
 * The search is case-insensitive and matches against the JSON stringified row.
 */
export function rowMatchesGlobalSearch<T>(row: T, query: string): boolean {
  if (!query) return true;
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;

  try {
    return JSON.stringify(row).toLowerCase().includes(normalizedQuery);
  } catch {
    return false;
  }
}

/**
 * Checks if a row matches a specific column filter.
 * The filter is case-insensitive and matches against the column value.
 */
export function rowMatchesColumnFilter<T>(
  row: T,
  filter: ColumnFilter,
  accessorKeyByColumnId: Map<string, string>
): boolean {
  const normalizedValue = filter.value.trim().toLowerCase();
  if (!normalizedValue) return true;

  const accessorKey = accessorKeyByColumnId.get(filter.columnId);
  if (!accessorKey) return true; // If no accessor key, don't filter

  const cellValue = getRowValue(row, accessorKey);
  const asString = valueToSearchString(cellValue);

  return asString.toLowerCase().includes(normalizedValue);
}

/**
 * Filters data based on global search and column filters.
 *
 * @param data - The array of data rows to filter
 * @param globalSearch - The global search query string
 * @param columnFilters - Array of column-specific filters
 * @param accessorKeyByColumnId - Map of column IDs to their accessor keys
 * @returns Filtered array of data rows
 */
export function filterTableData<T>(
  data: T[],
  globalSearch: string,
  columnFilters: ColumnFilter[],
  accessorKeyByColumnId: Map<string, string>
): T[] {
  const query = globalSearch.trim().toLowerCase();
  const activeColumnFilters = columnFilters
    .map((f) => ({ columnId: f.columnId, value: f.value.trim().toLowerCase() }))
    .filter((f) => f.value.length > 0);

  if (!query && activeColumnFilters.length === 0) return data;

  return data.filter((row) => {
    // Check column filters first
    for (const filter of activeColumnFilters) {
      if (!rowMatchesColumnFilter(row, filter, accessorKeyByColumnId)) {
        return false;
      }
    }

    // Then check global search
    if (!query) return true;
    return rowMatchesGlobalSearch(row, query);
  });
}

/**
 * Extracts filterable columns from column definitions.
 * A column is filterable if it has an accessorKey.
 */
export function extractFilterableColumns<_TData, _TValue>(
  columns: Array<{ accessorKey?: string; id?: string }>
): ColumnFilterConfig[] {
  return columns
    .map((col) => {
      if (typeof col.accessorKey !== "string") return null;
      const columnId = typeof col.id === "string" ? col.id : col.accessorKey;
      return { columnId, accessorKey: col.accessorKey };
    })
    .filter((v): v is ColumnFilterConfig => v != null);
}

/**
 * Creates a map of column IDs to accessor keys for efficient lookup.
 */
export function createAccessorKeyMap(filterableColumns: ColumnFilterConfig[]): Map<string, string> {
  return new Map(filterableColumns.map((c) => [c.columnId, c.accessorKey]));
}
