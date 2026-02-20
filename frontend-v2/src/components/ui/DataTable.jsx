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
  rowKey,
  className,
  headerClassName,
  bodyClassName,
  rowClassName,
}) {
  return (
    <div
      className={clsx(
        "overflow-x-auto rounded-xl border border-cyan-500/20 bg-secondary/10",
        className
      )}
    >
      <table className="w-full text-sm text-left">
        <thead
          className={clsx(
            "bg-secondary/20 border-b border-cyan-500/10",
            headerClassName
          )}
        >
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={clsx(
                  "px-4 py-3 text-left text-xs font-medium text-cyan-400 uppercase whitespace-nowrap",
                  col.headerClassName ?? col.className
                )}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className={clsx("divide-y divide-cyan-500/10", bodyClassName)}>
          {data.length === 0 ? (
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
                key={typeof rowKey === "function" ? rowKey(row, rowIndex) : row.key ?? rowIndex}
                onClick={() => onRowClick?.(row, rowIndex)}
                className={clsx(
                  "transition-colors",
                  onRowClick && "cursor-pointer hover:bg-cyan-500/10",
                  typeof rowClassName === "function"
                    ? rowClassName(row, rowIndex)
                    : rowClassName
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={clsx(
                      "px-4 py-3 text-sm",
                      col.cellClassName ?? col.className ?? "text-secondary"
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
