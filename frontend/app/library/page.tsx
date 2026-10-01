"use client";
import { useCallback, useEffect, useState } from "react";
import { fetchDiseases, type Advisory } from "../../lib/api";
import { useLang } from "../../lib/LanguageContext";

const CROPS = ["All", "Tomato", "Potato", "Maize", "Rice", "Cotton", "Wheat"];

export default function Library() {
  const { t } = useLang();
  const [items, setItems] = useState<Advisory[]>([]);
  const [q, setQ] = useState("");
  const [crop, setCrop] = useState("All");
  const [sel, setSel] = useState<Advisory | null>(null);

  const load = useCallback(async () => {
    setItems(await fetchDiseases(crop === "All" ? undefined : crop, q || undefined).catch(() => []));
  }, [crop, q]);

  useEffect(() => { void load(); }, [load]);

  return (
    <main className="mx-auto max-w-5xl space-y-4 p-6">
      <h1 className="text-xl font-bold">{t("lib_t")}</h1>
      <div className="flex flex-wrap gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("lib_ph")}
          className="min-w-60 flex-1 rounded-lg border p-2 text-sm" />
        <select value={crop} onChange={(e) => setCrop(e.target.value)} className="rounded-lg border p-2 text-sm">
          {CROPS.map((c) => <option key={c}>{c}</option>)}
        </select>
        <button onClick={load} className="rounded-lg bg-green-700 px-4 text-sm font-semibold text-white">{t("w_search")}</button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((d) => (
          <button key={d.label} onClick={() => setSel(d)} className="rounded-2xl bg-white p-4 text-left shadow hover:ring">
            <p className="font-mono text-xs text-gray-500">{d.label}</p>
            <p className="font-bold">{d.crop} — {d.disease}</p>
            <p className="text-sm text-gray-600">{t("severity")}: {d.severity} • {d.symptoms.slice(0, 80)}…</p>
          </button>
        ))}
      </div>
      {items.length === 0 && <p className="text-sm text-gray-500">{t("lib_empty")}</p>}
      {sel && (
        <div className="fixed inset-0 grid place-items-center bg-black/40 p-4" onClick={() => setSel(null)}>
          <div className="max-w-lg rounded-2xl bg-white p-6 text-sm space-y-2" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold">{sel.crop} — {sel.disease}</h2>
            <p><b>{t("symptoms")}:</b> {sel.symptoms}</p>
            <p><b>{t("organic")}:</b> {sel.organic_treatment}</p>
            <p><b>{t("chemical")}:</b> {sel.chemical_treatment}</p>
            <p><b>{t("prevention")}:</b> {sel.prevention}</p>
            <button onClick={() => setSel(null)} className="rounded bg-gray-900 px-4 py-2 text-white">{t("close")}</button>
          </div>
        </div>
      )}
    </main>
  );
}
