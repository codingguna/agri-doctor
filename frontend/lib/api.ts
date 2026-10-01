export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Prediction = { label: string; confidence: number };
export type Advisory = {
  label: string; crop: string; plant: string; disease: string; condition: string; category: string;
  severity: string; symptoms: string; organic_treatment: string; chemical_treatment: string;
  prevention: string; village_advice?: string;
};
export type PredictResponse = {
  predictions: Prediction[]; advisory: Advisory | null; plant: string; category: string;
  unknown: boolean; unknown_threshold: number; retake_guide: string | null;
  inference_ms: number; mode: string; record_id?: number | null;
};
export type HistoryItem = {
  id: number; top_label: string; confidence: number; all_predictions: Prediction[];
  advisory_snapshot: Advisory | null; created_at: string;
};
export type Stats = { total: number; healthy: number; diseased: number; by_disease: { label: string; count: number }[]; labels: number };
export type Weather = { temp_c: number; humidity: number; desc: string; source: string; spray_advisory: string; place?: string; lat?: number; lon?: number; warning?: string };
export type GeoPlace = { name: string; state: string; country: string; lat: number; lon: number };

async function j<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export async function predictImage(file: File): Promise<PredictResponse> {
  const fd = new FormData();
  fd.append("file", file);
  return j(await fetch(`${API_URL}/predict`, { method: "POST", body: fd }));
}
export async function fetchDiseases(crop?: string, q?: string): Promise<Advisory[]> {
  const u = new URL(`${API_URL}/diseases`);
  if (crop) u.searchParams.set("crop", crop);
  if (q) u.searchParams.set("q", q);
  return j(await fetch(u.toString(), { cache: "no-store" }));
}
export async function fetchHistory(limit = 20): Promise<HistoryItem[]> {
  return j(await fetch(`${API_URL}/history?limit=${limit}`, { cache: "no-store" }));
}
export async function clearHistory(): Promise<void> {
  const r = await fetch(`${API_URL}/history`, { method: "DELETE" });
  await j(r);
}
export async function fetchStats(): Promise<Stats> {
  return j(await fetch(`${API_URL}/stats`, { cache: "no-store" }));
}
export async function fetchWeather(lat = 19.07, lon = 72.87): Promise<Weather> {
  return j(await fetch(`${API_URL}/weather?lat=${lat}&lon=${lon}`, { cache: "no-store" }));
}
export async function geocodePlace(q: string): Promise<GeoPlace[]> {
  return j(await fetch(`${API_URL}/geocode?q=${encodeURIComponent(q)}`, { cache: "no-store" }));
}
