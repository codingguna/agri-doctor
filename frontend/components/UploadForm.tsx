"use client";
import { useState } from "react";
import { predictImage, type PredictResponse } from "../lib/api";

const STRINGS: Record<string, Record<string, string>> = {
  en: { title: "AgriDoctor", sub: "Upload a leaf photo to detect disease", btn: "Detect disease", drag: "Choose leaf image (JPG/PNG, max 8MB)" },
  hi: { title: "एग्रीडॉक्टर", sub: "रोग पहचान के लिए पत्ती की फोटो अपलोड करें", btn: "रोग पहचानें", drag: "पत्ती की तस्वीर चुनें" },
  mr: { title: "ॲग्रीडॉक्टर", sub: "रोग ओळखण्यासाठी पानाचा फोटो अपलोड करा", btn: "रोग ओळखा", drag: "पानाचा फोटो निवडा" }
};

export default function UploadForm() {
  const [lang, setLang] = useState("en");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const t = STRINGS[lang];

  function onFile(f: File | undefined) {
    if (!f) return;
    setFile(f); setResult(null); setError(null);
    setPreview(URL.createObjectURL(f));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true); setError(null);
    try {
      const r = await predictImage(file);
      setResult(r);
      const hist = JSON.parse(localStorage.getItem("agri-history") || "[]");
      hist.unshift({ at: new Date().toISOString(), top: r.predictions[0], advisory: r.advisory });
      localStorage.setItem("agri-history", JSON.stringify(hist.slice(0, 20)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl rounded-2xl bg-white p-6 shadow">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-green-800">{t.title} — SIH26131</h1>
          <p className="text-sm text-gray-600">{t.sub}</p>
        </div>
        <select value={lang} onChange={(e) => setLang(e.target.value)} className="rounded border p-2 text-sm">
          <option value="en">English</option>
          <option value="hi">हिंदी</option>
          <option value="mr">मराठी</option>
        </select>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        <label className="block cursor-pointer rounded-xl border-2 border-dashed border-green-300 p-6 text-center hover:bg-green-50">
          <span className="text-sm text-gray-600">{t.drag}</span>
          <input type="file" accept="image/*" className="hidden"
            onChange={(e) => onFile(e.target.files?.[0])} />
          {preview && <img src={preview} alt="preview" className="mx-auto mt-4 max-h-64 rounded-lg" />}
        </label>
        <button disabled={!file || loading} className="w-full rounded-xl bg-green-700 py-3 font-semibold text-white disabled:opacity-50">
          {loading ? "Analyzing…" : t.btn}
        </button>
      </form>

      {error && <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {result && (
        <div className="mt-6 space-y-4">
          <p className="text-xs text-gray-500">Mode: {result.mode} • {result.inference_ms} ms</p>
          {result.predictions.map((p) => (
            <div key={p.label} className="flex justify-between rounded bg-green-50 px-3 py-2 text-sm">
              <span className="font-mono">{p.label}</span>
              <span className="font-bold">{(p.confidence * 100).toFixed(1)}%</span>
            </div>
          ))}
          {result.advisory && (
            <div className="rounded-xl border p-4 text-sm space-y-2">
              <h2 className="text-lg font-bold">{result.advisory.crop} — {result.advisory.disease}</h2>
              <p><b>Severity:</b> {result.advisory.severity}</p>
              <p><b>Symptoms:</b> {result.advisory.symptoms}</p>
              <p><b>Organic:</b> {result.advisory.organic_treatment}</p>
              <p><b>Chemical:</b> {result.advisory.chemical_treatment}</p>
              <p><b>Prevention:</b> {result.advisory.prevention}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
