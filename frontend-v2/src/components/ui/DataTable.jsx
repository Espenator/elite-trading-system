import clsx from "clsx";

/**
 * Data table with optional row click. Styled for cyan/dark theme:
 * cyan header, dividers, hover and selected row highlight.
 */
export default function DataTable({
  columns = [],
  data = [],
  onRowClick,
  emptyMessage = "No data",
  loading = false,
  rowKey,
  className,
  headerClassName,
  bodyClassName,
  rowClassName,
}) {
  return (
    <div
      className={clsx(
        "overflow-x-auto rounded-xl border border-secondary/30 bg-surface",
        className,
      )}
    >
      <table className="w-full text-sm text-left">
        <thead
          className={clsx(
            "bg-surface border-b border-secondary/30",
            headerClassName,
          )}
        >
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  "px-4 py-3 text-left text-xs font-medium text-cyan-400 uppercase whitespace-nowrap",
                  col.headerClassName ?? col.className,
                )}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={clsx("divide-y divide-cyan-500/10", bodyClassName)}>
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={`skel-${i}`}>
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3">
                    <div className="h-4 bg-secondary/20 rounded animate-pulse" style={{ width: `${60 + Math.random() * 30}%` }} />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="px-4 py-8 text-center text-sm text-secondary"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr
                key={
                  typeof rowKey === "function"
                    ? rowKey(row, rowIndex)
                    : (row.key ?? rowIndex)
                }
                onClick={() => onRowClick?.(row, rowIndex)}
                onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onRowClick(row, rowIndex); } } : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? "button" : undefined}
                className={clsx(
                  "transition-colors",
                  onRowClick && "cursor-pointer hover:bg-cyan-500/10 focus:bg-cyan-500/10 focus:outline-none",
                  typeof rowClassName === "function"
                    ? rowClassName(row, rowIndex)
                    : rowClassName,
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      "px-4 py-3 text-sm",
                      col.cellClassName ?? col.className ?? "text-white/70",
                    )}
                  >
                    {typeof col.render === "function"
                      ? col.render(row[col.key], row, rowIndex)
                      : row[col.key]}
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
