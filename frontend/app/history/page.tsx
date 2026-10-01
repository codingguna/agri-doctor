"use client";
import { useEffect, useState } from "react";
import { clearHistory, fetchHistory, type HistoryItem } from "../../lib/api";
import { useLang } from "../../lib/LanguageContext";

export default function History() {
  const { t } = useLang();
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try { setItems(await fetchHistory(50)); setErr(null); }
    catch (e) { setErr(e instanceof Error ? e.message : "Failed"); }
  }
  useEffect(() => { load(); }, []);

  return (
    <main className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">{t("hist_t")}</h1>
        <button onClick={async () => { await clearHistory().catch(() => {}); load(); }}
          className="rounded-lg border px-3 py-2 text-sm">{t("clear")}</button>
      </div>
      {err && <p className="rounded bg-red-50 p-3 text-sm text-red-700">{err}</p>}
      <div className="space-y-2">
        {items.map((h) => (
          <div key={h.id} className="rounded-2xl bg-white p-4 text-sm shadow">
            <p className="font-mono text-xs text-gray-500">#{h.id} • {new Date(h.created_at).toLocaleString()}</p>
            <p className="font-bold">{h.top_label} — {(h.confidence * 100).toFixed(1)}%</p>
            {h.advisory_snapshot && <p className="text-gray-600">{h.advisory_snapshot.crop} • {h.advisory_snapshot.disease} • {h.advisory_snapshot.severity}</p>}
          </div>
        ))}
      </div>
      {items.length === 0 && !err && <p className="text-sm text-gray-500">{t("hist_empty")}</p>}
    </main>
  );
}
