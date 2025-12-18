import { cn } from '@/lib/cn';

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T>[];
  className?: string;
  emptyMessage?: string;
}

export interface ColumnDef<T> {
  key: keyof T | string;
  header: string;
  cell?: (value: any, row: T) => React.ReactNode;
  className?: string;
}

export function DataTable<T>({ data, columns, className, emptyMessage = 'No data available' }: DataTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className={cn('text-center py-8 text-gray-500', className)}>
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={cn('overflow-x-auto', className)}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            {columns.map((column) => (
              <th
                key={String(column.key)}
                className={cn('text-left py-3 px-4 font-medium text-gray-700', column.className)}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
              {columns.map((column) => (
                <td
                  key={String(column.key)}
                  className={cn('py-3 px-4', column.className)}
                >
                  {column.cell
                    ? column.cell(row[column.key as keyof T], row)
                    : String(row[column.key as keyof T] ?? '')
                  }
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}