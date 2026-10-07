import { ChevronLeft, ChevronRight } from "lucide-react";

function pageWindow(page, pageCount) {
  const pages = [];
  const start = Math.max(1, page - 2);
  const end = Math.min(pageCount, page + 2);
  for (let index = start; index <= end; index += 1) pages.push(index);
  return pages;
}

export default function Pagination({
  page,
  pageCount,
  pageSize,
  onPageChange,
  onPageSizeChange,
  total,
  start,
  end
}) {
  if (!total) return null;
  const pages = pageWindow(page, pageCount);

  return (
    <nav className="pagination" aria-label="团队分页">
      <div className="page-summary">
        显示 {start}-{end}，共 {total} 条
      </div>
      <div className="page-controls">
        <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)} aria-label="上一页">
          <ChevronLeft size={16} aria-hidden="true" />
        </button>
        {pages[0] > 1 && <span className="page-ellipsis">...</span>}
        {pages.map((item) => (
          <button
            type="button"
            className={item === page ? "active" : ""}
            onClick={() => onPageChange(item)}
            key={item}
          >
            {item}
          </button>
        ))}
        {pages.at(-1) < pageCount && <span className="page-ellipsis">...</span>}
        <button type="button" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)} aria-label="下一页">
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>
      <label className="page-size">
        每页
        <select value={pageSize} onChange={(event) => onPageSizeChange(Number(event.target.value))}>
          <option value={12}>12</option>
          <option value={18}>18</option>
          <option value={24}>24</option>
          <option value={36}>36</option>
        </select>
      </label>
    </nav>
  );
}
