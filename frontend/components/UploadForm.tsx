"use client";
import { useState } from "react";
import { predictImage, type PredictResponse } from "../lib/api";
import { useLang } from "../lib/LanguageContext";
import WeatherCard from "./WeatherCard";
import LiveCamera from "./LiveCamera";

export default function UploadForm() {
  const { t } = useLang();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  function onFile(f: File | undefined | null) {
    if (!f) return;
    setFile(f); setResult(null); setError(null);
    setPreview(URL.createObjectURL(f));
  }

  async function run(f: File) {
    setLoading(true); setError(null);
    try {
      setResult(await predictImage(f));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (file) await run(file);
  }

  return (
    <div className="space-y-4">
      <div className="mx-auto max-w-2xl rounded-2xl bg-white p-6 shadow">
        <div className="mb-4">
          <h1 className="text-2xl font-bold text-green-800">{t("title")}</h1>
          <p className="text-sm text-gray-600">{t("tagline")}</p>
          <p className="text-sm text-gray-600">{t("sub")}</p>
        </div>
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block cursor-pointer rounded-xl border-2 border-dashed border-green-300 p-6 text-center hover:bg-green-50">
            <span className="text-sm text-gray-600">{t("choose")}</span>
            <input type="file" accept="image/*" capture="environment" className="hidden"
              onChange={(e) => onFile(e.target.files?.[0])} />
            {preview && <img src={preview} alt="preview" className="mx-auto mt-4 max-h-64 rounded-lg" />}
          </label>
          <button disabled={!file || loading} className="w-full rounded-xl bg-green-700 py-3 font-semibold text-white disabled:opacity-50">
            {loading ? t("analyzing") : t("detect")}
          </button>
        </form>
        {error && <p className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        {result && (
          <div className="mt-6 space-y-4">
            <p className="text-xs text-gray-500">Mode: {result.mode} • {result.inference_ms} ms {result.record_id ? `• saved #${result.record_id}` : ""}</p>
            <div className="rounded-xl bg-green-800 p-4 text-white">
              <p className="text-xs uppercase opacity-80">{t("plant_type")}</p>
              <p className="text-xl font-extrabold">🌿 {result.plant} — {result.category}</p>
              {result.unknown && <p className="mt-1 text-sm">⚠️ {result.retake_guide}</p>}
            </div>
            {result.predictions.map((p) => (
              <div key={p.label} className="flex justify-between rounded bg-green-50 px-3 py-2 text-sm">
                <span className="font-mono">{p.label}</span>
                <span className="font-bold">{(p.confidence * 100).toFixed(1)}%</span>
              </div>
            ))}
            {result.advisory && !result.unknown && (
              <div className="rounded-xl border p-4 text-sm space-y-2">
                <h2 className="text-lg font-bold">{result.advisory.plant} — {result.advisory.condition}</h2>
                <p><b>{t("type")}:</b> {result.advisory.category} • <b>{t("severity")}:</b> {result.advisory.severity}</p>
                <p className="rounded bg-yellow-50 p-2"><b>{t("village")}:</b> {result.advisory.village_advice}</p>
                <p><b>{t("symptoms")}:</b> {result.advisory.symptoms}</p>
                <p><b>{t("organic")}:</b> {result.advisory.organic_treatment}</p>
                <p><b>{t("chemical")}:</b> {result.advisory.chemical_treatment}</p>
                <p><b>{t("prevention")}:</b> {result.advisory.prevention}</p>
              </div>
            )}
          </div>
        )}
      </div>
      <div className="mx-auto max-w-2xl"><LiveCamera onCapture={(f) => { onFile(f); run(f); }} /></div>
      <div className="mx-auto max-w-2xl"><WeatherCard /></div>
    </div>
  );
}
