import { useMemo, useState } from "react";
import { Download, ChevronLeft, ChevronRight } from "lucide-react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const COLORS = ["#0d7f74", "#b7791f", "#3b5b92", "#a23b5d", "#6b8e23", "#7a4fa3", "#c4622d", "#2f7f9f"];

export default function ResultsView({ result }) {
  const { columns, rows, truncated, duration_ms } = result;
  const [q, setQ] = useState("");
  const [sort, setSort] = useState(null);
  const [page, setPage] = useState(0);
  const [size, setSize] = useState(10);

  const filtered = useMemo(() => {
    const s = q.toLowerCase();
    let r = s ? rows.filter((row) => row.some((v) => String(v ?? "").toLowerCase().includes(s))) : rows;
    if (sort) {
      const { i, dir } = sort;
      r = [...r].sort((a, b) => {
        const x = a[i], y = b[i];
        if (x == null) return 1;
        if (y == null) return -1;
        return (typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y))) * dir;
      });
    }
    return r;
  }, [rows, q, sort]);

  const pages = Math.max(1, Math.ceil(filtered.length / size));
  const view = filtered.slice(page * size, page * size + size);

  const numeric = columns.map((_, i) => i).filter((i) => rows.some((r) => typeof r[i] === "number") && rows.slice(0, 50).every((r) => r[i] == null || typeof r[i] === "number"));
  const labelIdx = columns.findIndex((_, i) => !numeric.includes(i));
  const canChart = numeric.length > 0 && labelIdx >= 0 && rows.length > 1 && rows.length <= 500;
  const suggested = /date|month|year|day|time/i.test(columns[labelIdx] || "") ? "line" : rows.length <= 8 && numeric.length === 1 ? "pie" : "bar";
  const [kind, setKind] = useState(null);
  const chart = kind || suggested;
  const data = canChart ? rows.slice(0, 50).map((r) => ({ name: String(r[labelIdx]), ...Object.fromEntries(numeric.map((i) => [columns[i], r[i]])) })) : [];

  function exportCsv() {
    const esc = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [columns, ...filtered].map((r) => r.map(esc).join(",")).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "askdb-results.csv";
    a.click();
  }

  const stat = (i) => {
    const v = rows.map((r) => r[i]).filter((x) => typeof x === "number");
    const sum = v.reduce((a, b) => a + b, 0);
    return { name: columns[i], sum, avg: sum / v.length, min: Math.min(...v), max: Math.max(...v) };
  };
  const fmt = (n) => Number(n.toFixed(2)).toLocaleString();

  const ChartBody = () => {
    const keys = numeric.map((i) => columns[i]);
    if (chart === "pie") return <PieChart><Pie data={data.slice(0, 12)} dataKey={keys[0]} nameKey="name" outerRadius={100} label>{data.slice(0, 12).map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart>;
    const common = <><CartesianGrid strokeDasharray="3 3" stroke="#d5dbe1" /><XAxis dataKey="name" /><YAxis /><Tooltip /><Legend /></>;
    if (chart === "line") return <LineChart data={data}>{common}{keys.map((k, i) => <Line key={k} dataKey={k} stroke={COLORS[i % COLORS.length]} strokeWidth={2} />)}</LineChart>;
    if (chart === "area") return <AreaChart data={data}>{common}{keys.map((k, i) => <Area key={k} dataKey={k} stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.25} />)}</AreaChart>;
    return <BarChart data={data}>{common}{keys.map((k, i) => <Bar key={k} dataKey={k} fill={COLORS[i % COLORS.length]} />)}</BarChart>;
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <input className="input !w-64" placeholder="Search results" value={q} onChange={(e) => { setQ(e.target.value); setPage(0); }} />
        <span className="text-sm text-slate-600">{filtered.length} rows · {duration_ms} ms{truncated && " · capped by the row limit"}</span>
        <button className="btn btn-ghost ml-auto" onClick={exportCsv}><Download size={14} />Export CSV</button>
      </div>
      <div className="overflow-x-auto border border-slate-300 rounded-lg bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>{columns.map((c, i) => (
              <th key={i} className="px-3 py-2 font-semibold whitespace-nowrap cursor-pointer select-none" onClick={() => setSort(sort?.i === i ? { i, dir: -sort.dir } : { i, dir: 1 })}>
                {c}{sort?.i === i && (sort.dir === 1 ? " ▲" : " ▼")}
              </th>))}
            </tr>
          </thead>
          <tbody>
            {view.map((r, ri) => (
              <tr key={ri} className="border-t border-slate-200 odd:bg-white even:bg-slate-50">
                {r.map((v, ci) => <td key={ci} className="px-3 py-1.5 font-mono text-xs whitespace-nowrap">{v === null ? <span className="text-slate-400">NULL</span> : String(v)}</td>)}
              </tr>
            ))}
            {!view.length && <tr><td className="px-3 py-4 text-slate-500" colSpan={columns.length}>No rows match.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <button className="btn btn-ghost !px-2" disabled={page === 0} onClick={() => setPage(page - 1)}><ChevronLeft size={14} /></button>
        <span>Page {page + 1} of {pages}</span>
        <button className="btn btn-ghost !px-2" disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}><ChevronRight size={14} /></button>
        <select className="input !w-auto !py-1" value={size} onChange={(e) => { setSize(Number(e.target.value)); setPage(0); }}>
          {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n} per page</option>)}
        </select>
      </div>

      {numeric.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {numeric.slice(0, 4).map((i) => { const s = stat(i); return (
            <div key={i} className="border border-slate-300 bg-white rounded-lg p-3 text-xs">
              <div className="font-semibold text-sm mb-1 truncate">{s.name}</div>
              <div>Sum {fmt(s.sum)}</div><div>Average {fmt(s.avg)}</div><div>Min {fmt(s.min)} · Max {fmt(s.max)}</div>
            </div>); })}
        </div>
      )}

      {canChart && (
        <div className="border border-slate-300 bg-white rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-sm font-semibold">Suggested chart</span>
            {["bar", "line", "area", "pie"].map((k) => (
              <button key={k} className={`btn !py-1 ${chart === k ? "btn-primary" : "btn-ghost"}`} onClick={() => setKind(k)}>{k}</button>
            ))}
          </div>
          <div style={{ height: 300 }}><ResponsiveContainer>{ChartBody()}</ResponsiveContainer></div>
        </div>
      )}
    </div>
  );
}
