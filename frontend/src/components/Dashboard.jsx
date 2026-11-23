import { useEffect, useState } from "react";
import { api } from "../services/api";
import HistoryList from "./HistoryList";

function Stat({ label, value, tone = "" }) {
  return (
    <div className="border border-slate-300 bg-white rounded-lg p-4">
      <div className={`text-3xl font-semibold ${tone}`}>{value ?? "-"}</div>
      <div className="text-sm text-slate-600">{label}</div>
    </div>
  );
}

export default function Dashboard({ status, version, onReopen }) {
  const [stats, setStats] = useState(null);
  useEffect(() => { api.stats().then(setStats).catch(() => {}); }, [version]);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Stat label="Databases" value={status.database_count} />
        <Stat label="Tables in current database" value={status.table_count} />
        <Stat label="Records (approximate)" value={status.total_rows?.toLocaleString()} />
        <Stat label={`Connected as ${status.info.user}@${status.info.host}`} value="Online" tone="text-teal-600" />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Stat label="Queries run" value={stats?.total} />
        <Stat label="Succeeded" value={stats?.success} tone="text-teal-600" />
        <Stat label="Failed or rejected" value={stats ? stats.failed + stats.rejected : null} tone="text-red-700" />
      </div>
      <section>
        <h2 className="font-semibold mb-2">Recent queries</h2>
        <HistoryList limit={5} onReopen={onReopen} version={version} />
      </section>
    </div>
  );
}
