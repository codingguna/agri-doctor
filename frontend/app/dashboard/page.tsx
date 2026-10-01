"use client";
import { useEffect, useState } from "react";
import { fetchStats, type Stats } from "../../lib/api";
import { useLang } from "../../lib/LanguageContext";

export default function Dashboard() {
  const { t } = useLang();
  const [s, setS] = useState<Stats | null>(null);
  useEffect(() => { fetchStats().then(setS).catch(() => setS(null)); }, []);
  if (!s) return <main className="p-6 text-sm text-gray-500">{t("w_loading")}…</main>;
  const max = Math.max(1, ...s.by_disease.map((d) => d.count));
  return (
    <main className="mx-auto max-w-5xl space-y-4 p-6">
      <h1 className="text-xl font-bold">{t("dash_t")}</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[[t("k_total"), s.total], [t("k_dis"), s.diseased], [t("k_healthy"), s.healthy], [t("k_classes"), s.labels]].map(([k, v]) => (
          <div key={k as string} className="rounded-2xl bg-white p-4 shadow">
            <p className="text-xs text-gray-500">{k}</p><p className="text-2xl font-extrabold">{v}</p>
          </div>
        ))}
      </div>
      <div className="rounded-2xl bg-white p-4 shadow">
        <p className="mb-2 font-bold text-sm">{t("top")}</p>
        {s.by_disease.map((d) => (
          <div key={d.label} className="mb-2 text-sm">
            <div className="flex justify-between"><span className="font-mono text-xs">{d.label}</span><span>{d.count}</span></div>
            <div className="h-2 rounded bg-gray-100"><div className="h-2 rounded bg-green-600" style={{ width: `${(d.count / max) * 100}%` }} /></div>
          </div>
        ))}
        {s.by_disease.length === 0 && <p className="text-sm text-gray-500">{t("nodata")}</p>}
      </div>
    </main>
  );
}
