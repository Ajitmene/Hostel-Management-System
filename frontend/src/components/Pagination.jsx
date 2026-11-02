import { ChevronLeft, ChevronRight } from "lucide-react";

export default function Pagination({ data, onPage }) {
  if (!data || data.pages <= 1) {
    return data ? <div className="pager"><span>{data.total} result{data.total === 1 ? "" : "s"}</span></div> : null;
  }
  const from = (data.page - 1) * data.page_size + 1;
  const to = Math.min(data.page * data.page_size, data.total);
  return (
    <nav className="pager" aria-label="Pagination">
      <span>
        {from}–{to} of {data.total}
      </span>
      <div>
        <button className="btn btn-small" disabled={data.page <= 1} onClick={() => onPage(data.page - 1)}>
          <ChevronLeft aria-hidden="true" />Previous
        </button>
        <span className="pager-page">
          Page {data.page} of {data.pages}
        </span>
        <button className="btn btn-small" disabled={data.page >= data.pages} onClick={() => onPage(data.page + 1)}>
          Next<ChevronRight aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
