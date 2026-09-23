export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Prediction = { label: string; confidence: number };
export type Advisory = {
  label: string; crop: string; disease: string; severity: string;
  symptoms: string; organic_treatment: string; chemical_treatment: string; prevention: string;
};
export type PredictResponse = {
  predictions: Prediction[]; advisory: Advisory | null; inference_ms: number; mode: string;
};

export async function predictImage(file: File): Promise<PredictResponse> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_URL}/predict`, { method: "POST", body: fd });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || "Prediction failed");
  }
  return res.json();
}

export async function fetchDiseases(): Promise<Advisory[]> {
  const res = await fetch(`${API_URL}/diseases`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load diseases");
  return res.json();
}
