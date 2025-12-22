"use client"

import type React from "react"

import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table"
import { useMemo, useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ArrowUpDown, Download, Search } from "lucide-react"
import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  onRowClick?: (row: TData) => void
  className?: string
  enableSearch?: boolean
  searchPlaceholder?: string
  enableExport?: boolean
  exportFilename?: string
}

export function DataTable<TData, TValue>({
  columns,
  data,
  onRowClick,
  className,
  enableSearch = false,
  searchPlaceholder = "Search...",
  enableExport = false,
  exportFilename = "export.csv",
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([])
  const [search, setSearch] = useState("")

  const filteredData = useMemo(() => {
    const query = search.trim().toLowerCase()
    if (!query) return data
    return data.filter((row) => {
      try {
        return JSON.stringify(row).toLowerCase().includes(query)
      } catch {
        return false
      }
    })
  }, [data, search])

  const table = useReactTable({
    data: filteredData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: setSorting,
    getSortedRowModel: getSortedRowModel(),
    state: {
      sorting,
    },
  })

  const exportToCsv = () => {
    const exportCols = columns
      .map((col) => {
        const accessorKey = (col as unknown as { accessorKey?: unknown }).accessorKey
        if (typeof accessorKey !== "string") return null
        const header = (col as unknown as { header?: unknown }).header
        return {
          accessorKey,
          header: typeof header === "string" ? header : accessorKey,
        }
      })
      .filter((c): c is { accessorKey: string; header: string } => c != null)

    const escape = (value: unknown) => {
      if (value == null) return ""
      const asString = typeof value === "string" ? value : JSON.stringify(value)
      if (/[",\n]/.test(asString)) {
        return `"${asString.replaceAll('"', '""')}"`
      }
      return asString
    }

    if (exportCols.length === 0) {
      const blob = new Blob([JSON.stringify(filteredData, null, 2)], { type: "application/json;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = exportFilename.replace(/\.csv$/i, ".json")
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      return
    }

    const rows = filteredData as unknown as Array<Record<string, unknown>>
    const headerLine = exportCols.map((c) => escape(c.header)).join(",")
    const dataLines = rows.map((row) => exportCols.map((c) => escape(row[c.accessorKey])).join(","))
    const csv = [headerLine, ...dataLines].join("\n")

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = exportFilename || "export.csv"
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className={cn("rounded-md border", className)}>
      {(enableSearch || enableExport) && (
        <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-muted/30 p-2">
          {enableSearch ? (
            <div className="relative w-full sm:w-80">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={searchPlaceholder || "Search..."}
                className="pl-8"
              />
            </div>
          ) : (
            <div />
          )}
          {enableExport && (
            <Button variant="outline" size="sm" onClick={exportToCsv} disabled={filteredData.length === 0}>
              <Download className="mr-2 h-4 w-4" />
              Export CSV
            </Button>
          )}
        </div>
      )}
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder ? null : (
                    <div
                      className={cn(
                        "flex items-center gap-1",
                        header.column.getCanSort() && "cursor-pointer select-none",
                      )}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {header.column.getCanSort() && <ArrowUpDown className="h-3 w-3 text-muted-foreground" />}
                    </div>
                  )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows?.length ? (
            table.getRowModel().rows.map((row) => (
              <TableRow
                key={row.id}
                data-state={row.getIsSelected() && "selected"}
                className={cn(onRowClick && "cursor-pointer hover:bg-muted/50")}
                onClick={() => onRowClick?.(row.original)}
              >
                {row.getVisibleCells().map((cell) => (
                  <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>
                ))}
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                No results.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}

export function SortableHeader({ children }: { children: React.ReactNode }) {
  return <div className="flex items-center gap-1">{children}</div>
}
