import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Key, Link2, RefreshCw, Table2, Eye } from "lucide-react";
import { api } from "../services/api";

export default function Explorer({ version, onChanged }) {
  const [dbs, setDbs] = useState({ databases: [], current: null });
  const [schema, setSchema] = useState(null);
  const [open, setOpen] = useState({});
  const [busy, setBusy] = useState(false);

  async function load(refresh = false) {
    setBusy(true);
    try { setDbs(await api.databases()); setSchema(await api.schema(refresh)); } finally { setBusy(false); }
  }
  useEffect(() => { load(); }, [version]);

  async function choose(name) { if (name) { await api.selectDb(name); onChanged(); } }

  return (
    <aside className="w-72 shrink-0 border-r border-slate-300 bg-white h-full overflow-y-auto">
      <div className="p-3 border-b border-slate-200 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Explorer</span>
          <button className="btn btn-ghost !px-2 !py-1" onClick={() => load(true)} title="Refresh schema">
            <RefreshCw size={14} className={busy ? "animate-spin" : ""} />
          </button>
        </div>
        <select className="input !py-1.5" value={dbs.current || ""} onChange={(e) => choose(e.target.value)}>
          <option value="" disabled>Choose a database</option>
          {dbs.databases.map((d) => <option key={d}>{d}</option>)}
        </select>
      </div>
      <ul className="p-2 text-sm">
        {schema?.tables.length === 0 && <li className="p-2 text-slate-500">No tables yet. Ask for one in the workspace.</li>}
        {schema?.tables.map((t) => (
          <li key={t.name}>
            <button className="w-full flex items-center gap-1.5 px-2 py-1 rounded hover:bg-slate-100 text-left"
              onClick={() => setOpen({ ...open, [t.name]: !open[t.name] })}>
              {open[t.name] ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {t.is_view ? <Eye size={14} className="text-slate-500" /> : <Table2 size={14} className="text-teal-600" />}
              <span className="font-medium truncate">{t.name}</span>
              {t.rows != null && <span className="ml-auto text-xs text-slate-500">~{t.rows}</span>}
            </button>
            {open[t.name] && (
              <ul className="ml-6 mb-1 border-l border-slate-200 pl-2">
                {t.columns.map((c) => (
                  <li key={c.name} className="flex items-center gap-1.5 py-0.5 text-xs">
                    {c.pk && <Key size={11} className="text-amber-600" />}
                    {c.fk && <Link2 size={11} className="text-teal-600" title={`-> ${c.fk}`} />}
                    <span className="font-mono">{c.name}</span>
                    <span className="ml-auto text-slate-500 font-mono truncate max-w-[90px]">{c.type}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </aside>
  );
}
