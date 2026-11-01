import { useApp } from "../context/AppContext";

export const fmtTime = (iso) => {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
};

export function Icon({ d, className = "w-6 h-6" }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}
export const ICONS = {
  home: "M3 11l9-8 9 8M5 10v10h14V10",
  cloud: "M7 18a4 4 0 010-8 5 5 0 019.6-1A4.5 4.5 0 0117 18H7z",
  price: "M12 3v18M17 7H9.5a2.5 2.5 0 000 5h5a2.5 2.5 0 010 5H7",
  leaf: "M12 21v-9M12 12c0-4 3-7 8-7 0 5-3 8-8 8M12 14c0-3-2-5-6-5 0 4 2 6 6 6",
  chat: "M21 12a8 8 0 01-11.5 7.2L4 20l1-4.5A8 8 0 1121 12z",
  pin: "M12 21s7-6.2 7-11a7 7 0 10-14 0c0 4.8 7 11 7 11zM12 12a2 2 0 100-4 2 2 0 000 4z",
};

export function Card({ title, action, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="flex items-center justify-between gap-2 mb-3">
          {title && <h2 className="text-lg font-bold">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/** Live / Cached / Sample / Unavailable badge. Sample data is always amber and never looks live. */
export function StatusBadge({ status }) {
  const { t } = useApp();
  const map = {
    live: ["bg-leaf-light text-leaf", t("live")], cached: ["bg-blue-100 text-blue-800", t("cached")],
    sample: ["bg-amber-light text-amber-900 border border-amber", t("sample_badge")],
    unavailable: ["bg-red-100 text-red-800", t("unavailable")], empty: ["bg-gray-100 text-gray-700", "—"],
  };
  const [cls, label] = map[status] || map.empty;
  return <span className={`badge ${cls}`}>{label}</span>;
}

export function Skeleton({ rows = 3 }) {
  return <div aria-busy="true" className="space-y-2">{Array.from({ length: rows }).map((_, i) => <div key={i} className="skeleton h-5" style={{ width: `${95 - i * 12}%` }} />)}</div>;
}

export function Empty({ children }) {
  return <p className="text-gray-600 py-2">{children}</p>;
}

export function ErrorBox({ message, onRetry, onSample }) {
  const { t } = useApp();
  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3">
      <p className="text-red-800 font-semibold mb-2">{message}</p>
      <div className="flex flex-wrap gap-2">
        {onRetry && <button className="btn-ghost" onClick={onRetry}>{t("retry")}</button>}
        {onSample && <button className="btn-ghost" onClick={onSample}>{t("view_sample")}</button>}
      </div>
    </div>
  );
}

export function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-black/40 p-0 sm:p-4" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label={title} className="bg-white w-full sm:max-w-lg rounded-t-2xl sm:rounded-2xl p-4 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-3">{title}</h2>
        {children}
      </div>
    </div>
  );
}

/** Missing values show "Not available" — never zero. */
export function Val({ v, unit = "" }) {
  const { t } = useApp();
  return v === null || v === undefined || v === "" ? <span className="text-gray-500">{t("not_available")}</span> : <span>{v}{unit && ` ${unit}`}</span>;
}
