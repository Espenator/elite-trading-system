import clsx from 'clsx';

export default function DataTable({
  columns = [],
  data = [],
  onRowClick,
  emptyMessage = 'No data',
  className,
  headerClassName,
  bodyClassName,
  rowClassName,
}) {
  return (
    <div className={clsx('overflow-x-auto rounded-xl border border-secondary/50', className)}>
      <table className="w-full text-sm text-left">
        <thead className={clsx('bg-secondary/10 border-b border-secondary/50', headerClassName)}>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx('px-4 py-3 font-semibold text-white whitespace-nowrap', col.headerClassName ?? col.className)}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={clsx('divide-y divide-secondary/30', bodyClassName)}>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-secondary">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={rowIndex}
                onClick={() => onRowClick?.(row, rowIndex)}
                className={clsx(
                  'transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-secondary/10',
                  typeof rowClassName === 'function' ? rowClassName(row, rowIndex) : rowClassName
                )}
              >
                {columns.map((col) => (
                  <td key={col.key} className={clsx('px-4 py-3 text-white', col.cellClassName ?? col.className)}>
                    {typeof col.render === 'function' ? col.render(row[col.key], row, rowIndex) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
