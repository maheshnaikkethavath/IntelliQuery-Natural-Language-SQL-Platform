import { useState } from "react";
import { Database, Loader2 } from "lucide-react";
import { api } from "../services/api";

export default function Connect({ onConnected }) {
  const [f, setF] = useState({ host: "localhost", port: 3306, user: "", password: "", database: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await api.connect({ ...f, port: Number(f.port), database: f.database || null });
      onConnected();
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen grid place-items-center p-6">
      <form onSubmit={submit} className="w-full max-w-md bg-white border border-slate-300 rounded-lg p-6 space-y-4">
        <div className="flex items-center gap-2"><Database className="text-teal-600" /><h1 className="text-xl font-semibold">Connect to MySQL</h1></div>
        <p className="text-sm text-slate-600">Use your own MySQL server. Credentials stay on the backend and are never sent to the AI.</p>
        <div className="grid grid-cols-3 gap-3">
          <label className="col-span-2 text-sm">Host<input className="input mt-1" value={f.host} onChange={set("host")} required /></label>
          <label className="text-sm">Port<input className="input mt-1" type="number" value={f.port} onChange={set("port")} required /></label>
        </div>
        <label className="block text-sm">Username<input className="input mt-1" value={f.user} onChange={set("user")} required /></label>
        <label className="block text-sm">Password<input className="input mt-1" type="password" value={f.password} onChange={set("password")} /></label>
        <label className="block text-sm">Database (optional)<input className="input mt-1" value={f.database} onChange={set("database")} placeholder="Pick one later in the explorer" /></label>
        {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">{error}</p>}
        <button className="btn btn-primary w-full justify-center" disabled={busy}>{busy && <Loader2 size={16} className="animate-spin" />}Connect</button>
      </form>
    </div>
  );
}
