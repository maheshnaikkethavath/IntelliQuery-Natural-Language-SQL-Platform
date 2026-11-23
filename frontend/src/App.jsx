import { useCallback, useEffect, useState } from "react";
import { History, LayoutDashboard, Loader2, Terminal } from "lucide-react";
import { api } from "./services/api";
import Connect from "./components/Connect";
import Dashboard from "./components/Dashboard";
import Explorer from "./components/Explorer";
import HistoryList from "./components/HistoryList";
import Workspace from "./components/Workspace";

const TABS = [["workspace", "Workspace", Terminal], ["dashboard", "Dashboard", LayoutDashboard], ["history", "History", History]];

export default function App() {
  const [status, setStatus] = useState(null);
  const [tab, setTab] = useState("workspace");
  const [preset, setPreset] = useState(null);
  const [version, setVersion] = useState(0);

  const refresh = useCallback(async () => {
    try { setStatus(await api.status()); } catch { setStatus({ connected: false }); }
    setVersion((v) => v + 1);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  if (!status) return <div className="min-h-screen grid place-items-center"><Loader2 className="animate-spin text-teal-600" /></div>;
  if (!status.connected) return <Connect onConnected={refresh} />;

  const reopen = (item) => { setPreset({ ...item, key: Date.now() }); setTab("workspace"); };

  return (
    <div className="h-screen flex flex-col">
      <header className="bg-ink text-white px-4 h-12 flex items-center gap-6 shrink-0">
        <span className="font-semibold tracking-tight">AskDB</span>
        <nav className="flex gap-1">
          {TABS.map(([id, label, Icon]) => (
            <button key={id} onClick={() => setTab(id)} className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-sm ${tab === id ? "bg-white/15" : "hover:bg-white/10"}`}>
              <Icon size={15} />{label}
            </button>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-xs">
          <span className="font-mono">{status.info.user}@{status.info.host}{status.info.database ? ` / ${status.info.database}` : ""}</span>
          <span className="rounded bg-white/15 px-2 py-0.5">role: {status.role}</span>
        </div>
      </header>
      <div className="flex flex-1 min-h-0">
        <Explorer version={version} onChanged={refresh} />
        <main className="flex-1 overflow-y-auto p-6">
          {tab === "workspace" && <Workspace preset={preset} onSchemaChanged={refresh} onRan={() => setVersion((v) => v + 1)} />}
          {tab === "dashboard" && <Dashboard status={status} version={version} onReopen={reopen} />}
          {tab === "history" && <HistoryList limit={100} onReopen={reopen} version={version} />}
        </main>
      </div>
    </div>
  );
}
