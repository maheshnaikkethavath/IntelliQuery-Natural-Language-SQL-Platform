import { useEffect, useState } from "react";
import { CheckCircle2, ShieldAlert, XCircle } from "lucide-react";
import { api } from "../services/api";

const ICON = { success: <CheckCircle2 size={16} className="text-teal-600" />, error: <XCircle size={16} className="text-red-700" />, rejected: <ShieldAlert size={16} className="text-amber-600" /> };

export default function HistoryList({ limit = 50, onReopen, version }) {
  const [items, setItems] = useState([]);
  useEffect(() => { api.history(limit).then(setItems).catch(() => {}); }, [limit, version]);
  if (!items.length) return <p className="text-sm text-slate-500">No queries yet. Run one in the workspace.</p>;
  return (
    <ul className="divide-y divide-slate-200 border border-slate-300 rounded-lg bg-white">
      {items.map((q) => (
        <li key={q.id}>
          <button className="w-full text-left p-3 hover:bg-slate-50 flex gap-3" onClick={() => onReopen({ request: q.request || "", sql: q.sql })}>
            <span className="mt-0.5">{ICON[q.status]}</span>
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-medium truncate">{q.request || "SQL run directly"}</span>
              <span className="block font-mono text-xs text-slate-600 truncate">{q.sql}</span>
              <span className="block text-xs text-slate-500 mt-0.5">
                {q.database || "no database"} · {new Date(q.executed_at).toLocaleString()}
                {q.duration_ms != null && ` · ${q.duration_ms} ms`}
                {q.affected_rows ? ` · ${q.affected_rows} rows affected` : ""}
              </span>
              {q.error && <span className="block text-xs text-red-700 truncate">{q.error}</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
