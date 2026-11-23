import { useEffect, useState } from "react";
import { AlertTriangle, Check, CheckCircle2, Circle, Copy, Eraser, Loader2, Play, ShieldAlert, Sparkles, XCircle } from "lucide-react";
import { api } from "../services/api";
import ResultsView from "./ResultsView";

const EXAMPLES = [
  "Show all tables in this database",
  "Count the rows in every table",
  "Create a table named employees with id, name and salary",
  "Show the structure of the employees table",
];

function Stages({ stages, busy }) {
  if (!stages.length && !busy) return null;
  return (
    <ol className="border border-slate-300 bg-white rounded-lg p-3 space-y-1.5 text-sm">
      {stages.map((s, i) => (
        <li key={i} className="flex items-start gap-2">
          {s.status === "done" && <CheckCircle2 size={16} className="text-teal-600 mt-0.5" />}
          {s.status === "failed" && <XCircle size={16} className="text-red-700 mt-0.5" />}
          {s.status === "waiting" && <Circle size={16} className="text-amber-600 mt-0.5" />}
          <span className="font-medium">{s.name}</span>
          <span className="text-slate-500 truncate">{s.detail}</span>
          <span className="ml-auto text-xs text-slate-500 font-mono">{s.ms} ms</span>
        </li>
      ))}
      {busy && <li className="flex items-center gap-2 text-slate-600"><Loader2 size={16} className="animate-spin" />{busy === "generating" ? "Working on your request" : "Running the query"}</li>}
    </ol>
  );
}

export default function Workspace({ preset, onSchemaChanged, onRan }) {
  const [prompt, setPrompt] = useState("");
  const [sql, setSql] = useState("");
  const [explanation, setExplanation] = useState("");
  const [validation, setValidation] = useState(null);
  const [genStages, setGenStages] = useState([]);
  const [execStages, setExecStages] = useState([]);
  const [outcome, setOutcome] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [preview, setPreview] = useState(null);
  const [copied, setCopied] = useState(false);

  function reset() {
    setSql(""); setExplanation(""); setValidation(null); setGenStages([]); setExecStages([]);
    setOutcome(null); setError(""); setConfirmed(false); setConfirmText(""); setPreview(null);
  }

  useEffect(() => {
    if (preset) { reset(); setPrompt(preset.request || ""); setSql(preset.sql || ""); }
  }, [preset]);

  useEffect(() => {
    if (!sql.trim()) { setValidation(null); return; }
    const h = setTimeout(() => api.validate(sql).then(setValidation).catch(() => {}), 400);
    return () => clearTimeout(h);
  }, [sql]);

  async function run(text, conf, confText, req) {
    setBusy("executing"); setError("");
    try {
      const res = await api.execute({ sql: text, confirmed: conf, confirm_text: confText, request: req || null, auto_correct: true });
      setExecStages(res.stages || []);
      setOutcome(res);
      if (res.status === "success") {
        if (res.sql !== text) setSql(res.sql);
        if (res.validation?.category === "ddl") onSchemaChanged();
        setConfirmed(false); setConfirmText("");
      }
      onRan();
    } catch (e) { setError(e.message); } finally { setBusy(""); }
  }

  async function generate() {
    if (!prompt.trim()) return;
    reset(); setBusy("generating");
    try {
      const g = await api.generate(prompt);
      setGenStages(g.stages); setSql(g.sql); setExplanation(g.explanation);
      if (g.sql && g.validation?.valid && !g.validation.requires_confirmation) await run(g.sql, true, "", prompt);
    } catch (e) { setError(e.message); } finally { setBusy(""); }
  }

  async function showPreview() {
    try { setPreview(await api.preview(sql)); } catch (e) { setError(e.message); }
  }

  const v = validation;
  const needsConfirm = v?.valid && v.requires_confirmation;
  const canRun = v?.valid && !busy && (!needsConfirm || (confirmed && (!v.destructive || confirmText.trim().toUpperCase() === "CONFIRM")));
  const res = outcome?.status === "success" ? outcome.result : null;

  return (
    <div className="space-y-4 max-w-5xl">
      <section className="space-y-2">
        <textarea className="input min-h-[96px] text-base" placeholder="Describe what you want in plain English, for example: show customers from Hyderabad"
          value={prompt} onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) generate(); }} />
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn btn-primary" onClick={generate} disabled={!!busy || !prompt.trim()}>
            {busy === "generating" ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}Generate SQL
          </button>
          <button className="btn btn-ghost" onClick={() => { setPrompt(""); reset(); }}><Eraser size={16} />Clear</button>
          <span className="text-xs text-slate-500">Ctrl + Enter to submit</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((e) => <button key={e} className="text-xs border border-slate-300 bg-white rounded-full px-3 py-1 hover:bg-teal-50" onClick={() => setPrompt(e)}>{e}</button>)}
        </div>
      </section>

      {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">{error}</p>}
      <Stages stages={[...genStages, ...execStages]} busy={busy} />
      {explanation && <p className="text-sm text-slate-700">{explanation}</p>}

      {(sql || genStages.length > 0) && (
        <section className="space-y-2">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold">SQL</h2>
            {v?.operation && <span className="text-xs font-mono bg-slate-200 rounded px-2 py-0.5">{v.operation}{v.target ? ` · ${v.target}` : ""}</span>}
            {v && (v.valid ? <span className="text-xs text-teal-700 flex items-center gap-1"><Check size={12} />Allowed</span> : <span className="text-xs text-red-700 flex items-center gap-1"><ShieldAlert size={12} />Blocked</span>)}
            <button className="btn btn-ghost ml-auto !py-1" onClick={() => { navigator.clipboard.writeText(sql); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
              <Copy size={14} />{copied ? "Copied" : "Copy"}
            </button>
          </div>
          <textarea spellCheck={false} className="input font-mono text-sm min-h-[120px] bg-ink !text-teal-50 !border-ink" value={sql} onChange={(e) => { setSql(e.target.value); setOutcome(null); setConfirmed(false); setPreview(null); }} />
          {v?.errors.map((m, i) => <p key={i} className="text-sm text-red-700">{m}</p>)}
          {v?.warnings.map((m, i) => <p key={i} className="text-sm text-amber-700 flex items-center gap-1"><AlertTriangle size={14} />{m}</p>)}

          {needsConfirm && (
            <div className={`border rounded-lg p-3 space-y-2 text-sm ${v.destructive ? "border-red-300 bg-red-50" : "border-amber-300 bg-amber-50"}`}>
              <p className="font-medium">This will change your database: {v.operation} on <span className="font-mono">{v.target || "unknown target"}</span></p>
              {["UPDATE", "DELETE"].includes(v.operation) && <button className="btn btn-ghost" onClick={showPreview}>Preview affected rows</button>}
              {preview && (preview.available
                ? <div className="space-y-1"><p>{preview.affected_estimate} row(s) match.</p>{preview.rows.length > 0 && <ResultsView result={{ columns: preview.columns, rows: preview.rows, duration_ms: 0 }} />}</div>
                : <p className="text-slate-600">{preview.message}</p>)}
              <label className="flex items-center gap-2"><input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />I understand and want to run this</label>
              {v.destructive && <input className="input !w-64" placeholder="Type CONFIRM to enable" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} />}
            </div>
          )}
          <button className={`btn ${v?.destructive ? "btn-danger" : "btn-primary"}`} disabled={!canRun} onClick={() => run(sql, confirmed, confirmText, prompt)}>
            {busy === "executing" ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}Run SQL
          </button>
        </section>
      )}

      {outcome && outcome.status !== "success" && outcome.status !== "confirmation_required" && (
        <div className="border border-red-200 bg-red-50 rounded-lg p-3 space-y-2 text-sm">
          <p className="font-medium text-red-800">{outcome.error}</p>
          {outcome.detail && <p className="font-mono text-xs text-red-700">{outcome.detail}</p>}
          {outcome.suggested_sql && (
            <div className="space-y-1">
              <p>The AI suggests this fix. Review it, then run it:</p>
              <pre className="font-mono text-xs bg-white border border-red-200 rounded p-2 whitespace-pre-wrap">{outcome.suggested_sql}</pre>
              <button className="btn btn-ghost" onClick={() => { setSql(outcome.suggested_sql); setOutcome(null); setConfirmed(false); }}>Use suggested SQL</button>
            </div>
          )}
        </div>
      )}

      {outcome?.corrections?.length > 0 && <p className="text-sm text-amber-700">The AI fixed an error and re-ran a read query automatically ({outcome.corrections.length} correction).</p>}
      {res && res.columns.length > 0 && <ResultsView key={outcome.sql + res.duration_ms} result={res} />}
      {res && res.columns.length === 0 && (
        <p className="border border-teal-200 bg-teal-50 rounded-lg p-3 text-sm">Done. {res.affected_rows} row(s) affected in {res.duration_ms} ms.</p>
      )}
    </div>
  );
}
