import { EmptyState, ErrorNotice, Loading } from "./ui.jsx";

/**
 * columns: [{ header, render: (row) => node, className? }]
 * Shows loading, error and empty states so every list page behaves the same.
 */
export default function DataTable({ columns, rows, loading, error, onRetry, empty, rowKey = "id" }) {
  if (error) return <ErrorNotice message={error} onRetry={onRetry} />;
  if (loading && !rows) return <Loading />;
  if (!rows || rows.length === 0) {
    return loading ? <Loading /> : <EmptyState icon={empty?.icon} title={empty?.title || "Nothing here yet"} hint={empty?.hint}>{empty?.action}</EmptyState>;
  }
  return (
    <div className={`table-wrap ${loading ? "is-loading" : ""}`}>
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.header} className={c.className}>
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row[rowKey]}>
              {columns.map((c) => (
                <td key={c.header} className={c.className} data-label={c.header}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
