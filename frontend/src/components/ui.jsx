import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, CheckCircle2, Clock, Inbox, Info, MinusCircle, Search, XCircle } from "lucide-react";
import { titleCase } from "../utils/format.js";

export const Loading = ({ label = "Loading…" }) => (
  <div className="loading" role="status">
    <span className="spinner" aria-hidden="true" />
    {label}
  </div>
);

export const EmptyState = ({ icon: Icon = Inbox, title, hint, children }) => (
  <div className="empty">
    <span className="empty-icon" aria-hidden="true"><Icon size={26} /></span>
    <strong>{title}</strong>
    {hint && <p>{hint}</p>}
    {children}
  </div>
);

export const ErrorNotice = ({ message, onRetry }) =>
  message ? (
    <div className="notice notice-error" role="alert">
      <span className="notice-text"><AlertTriangle size={18} aria-hidden="true" />{message}</span>
      {onRetry && (
        <button className="btn btn-small" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  ) : null;

const BADGES = {
  active: ["good", CheckCircle2], available: ["good", CheckCircle2], paid: ["good", CheckCircle2], present: ["good", CheckCircle2],
  pending: ["warn", Clock], partial: ["warn", Clock], leave: ["warn", Clock],
  inactive: ["muted", MinusCircle], closed: ["muted", MinusCircle], left: ["muted", MinusCircle],
  overdue: ["bad", AlertTriangle], full: ["bad", XCircle], absent: ["bad", XCircle],
};
export const StatusBadge = ({ value }) => {
  const [tone, Icon] = BADGES[value] || ["muted", MinusCircle];
  return (
    <span className={`badge badge-${tone}`}>
      <Icon size={13} aria-hidden="true" />
      {titleCase(value)}
    </span>
  );
};

/** A number with an icon tile. `tone` picks the colour family; `to` makes the whole card a link. */
export const StatCard = ({ label, value, hint, tone = "blue", icon: Icon, to }) => {
  const body = (
    <>
      {Icon && <span className={`tile tile-${tone}`} aria-hidden="true"><Icon size={22} /></span>}
      <div className="stat-text">
        <div className="stat-value">{value ?? "–"}</div>
        <div className="stat-label">{label}</div>
        {hint && <div className="stat-hint">{hint}</div>}
      </div>
    </>
  );
  return to ? <Link to={to} className={`stat stat-link stat-${tone}`}>{body}</Link> : <div className={`stat stat-${tone}`}>{body}</div>;
};

export const PageHeader = ({ icon: Icon, title, subtitle, actions }) => (
  <header className="page-header">
    <div className="page-title">
      {Icon && <span className="page-icon" aria-hidden="true"><Icon size={24} /></span>}
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="subtitle">{subtitle}</p>}
      </div>
    </div>
    {actions && <div className="actions">{actions}</div>}
  </header>
);

/** A short, always-visible explanation of what the page is for and the rules behind it. */
export const InfoBox = ({ title = "About this page", children, open = true }) => (
  <details className="infobox" open={open}>
    <summary><Info size={17} aria-hidden="true" />{title}</summary>
    <div className="infobox-body">{children}</div>
  </details>
);

/** Label + input + inline error. Pass `as="select"` or `as="textarea"` for other controls. */
export function Field({ label, error, hint, as: Tag = "input", children, ...props }) {
  const id = props.id || `f-${props.name}`;
  return (
    <div className={`field ${error ? "field-error" : ""}`}>
      <label htmlFor={id}>{label}</label>
      <Tag id={id} aria-invalid={!!error} aria-describedby={error ? `${id}-err` : undefined} {...props}>
        {children}
      </Tag>
      {hint && !error && <small className="hint">{hint}</small>}
      {error && (
        <small id={`${id}-err`} className="error-text">
          {error}
        </small>
      )}
    </div>
  );
}

export function SearchInput({ value, onChange, placeholder = "Search…", label = "Search" }) {
  const [text, setText] = useState(value || "");
  useEffect(() => {
    const t = setTimeout(() => text !== (value || "") && onChange(text), 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text]);
  return (
    <span className="search-wrap">
      <Search size={16} aria-hidden="true" />
      <input type="search" className="search" aria-label={label} placeholder={placeholder} value={text} onChange={(e) => setText(e.target.value)} />
    </span>
  );
}

/** One square per bed: filled when occupied. The same picture a warden draws on a whiteboard. */
export function BedStrip({ occupied, capacity, closed }) {
  return (
    <span className={`beds ${closed ? "beds-closed" : ""}`} title={`${occupied} of ${capacity} beds occupied`}>
      {Array.from({ length: capacity }, (_, i) => (
        <i key={i} className={i < occupied ? "bed bed-on" : "bed"} />
      ))}
    </span>
  );
}

const initials = (name) => (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join("");
export const Avatar = ({ name, size = 36 }) => (
  <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.38 }} aria-hidden="true">{initials(name)}</span>
);
