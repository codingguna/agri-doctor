"use client";
import { useEffect, useState } from "react";
import { fetchWeather, geocodePlace, type GeoPlace, type Weather } from "../lib/api";
import { useLang } from "../lib/LanguageContext";

type Saved = { lat: number; lon: number; label: string };

function loadSaved(): Saved | null {
  try {
    const s = localStorage.getItem("agri-weather");
    return s ? (JSON.parse(s) as Saved) : null;
  } catch { return null; }
}

export default function WeatherCard() {
  const { t } = useLang();
  const [w, setW] = useState<Weather | null>(null);
  const [loc, setLoc] = useState<Saved | null>(null);
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<GeoPlace[]>([]);
  const [latIn, setLatIn] = useState("");
  const [lonIn, setLonIn] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load(s: Saved) {
    setLoading(true); setErr(null);
    try {
      const r = await fetchWeather(s.lat, s.lon);
      setW(r); setLoc(s);
      localStorage.setItem("agri-weather", JSON.stringify(s));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Weather failed");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const s = loadSaved();
    if (s) load(s);
  }, []);

  function useMyLocation() {
    setErr(null);
    if (!navigator.geolocation) {
      setErr(t("w_nosupport"));
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (p) => load({ lat: +p.coords.latitude.toFixed(4), lon: +p.coords.longitude.toFixed(4), label: "GPS" }),
      () => { setLoading(false); setErr(t("w_denied")); },
      { timeout: 10000 }
    );
  }

  async function search() {
    if (q.trim().length < 2) return;
    setLoading(true); setErr(null);
    try {
      setOptions(await geocodePlace(q.trim()));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border bg-white p-4 text-sm shadow space-y-3">
      <p className="font-bold">🌤️ {t("w_t")} {w && <span className="text-xs font-normal text-gray-500">({w.source})</span>}</p>
      {loc && w ? (
        <div>
          <p className="text-xs text-gray-500">{t("w_for")} <b>{loc.label}</b> ({loc.lat}, {loc.lon}){w.place ? ` — ${w.place}` : ""}</p>
          <p className="mt-1">{w.temp_c}°C • {w.humidity}% humidity • {w.desc}</p>
          <p className="mt-1 text-green-800">Spray advisory: {w.spray_advisory}</p>
        </div>
      ) : (
        <p className="text-gray-600">{t("w_noloc")}</p>
      )}
      <div className="flex flex-wrap gap-2">
        <button onClick={useMyLocation} disabled={loading} className="rounded-lg bg-green-700 px-3 py-2 text-white disabled:opacity-50">
          📍 {t("w_use")}
        </button>
        <button onClick={() => { localStorage.removeItem("agri-weather"); setLoc(null); setW(null); setOptions([]); }}
          className="rounded-lg border px-3 py-2">{t("w_reset")}</button>
      </div>
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("w_search_ph")}
          className="flex-1 rounded-lg border p-2" onKeyDown={(e) => e.key === "Enter" && search()} />
        <button onClick={search} disabled={loading} className="rounded-lg bg-gray-900 px-3 py-2 text-white">{t("w_search")}</button>
      </div>
      {options.length > 0 && (
        <div className="space-y-1">
          {options.map((o, i) => (
            <button key={i} onClick={() => load({ lat: o.lat, lon: o.lon, label: `${o.name}${o.state ? ", " + o.state : ""} ${o.country}` })}
              className="w-full rounded-lg bg-green-50 px-3 py-2 text-left hover:bg-green-100">
              {o.name}{o.state ? `, ${o.state}` : ""} {o.country} <span className="text-xs text-gray-500">({o.lat}, {o.lon})</span>
            </button>
          ))}
        </div>
      )}
      <details>
        <summary className="cursor-pointer text-gray-600">{t("w_manual")}</summary>
        <div className="mt-2 flex gap-2">
          <input value={latIn} onChange={(e) => setLatIn(e.target.value)} placeholder="Lat" className="w-full rounded-lg border p-2" />
          <input value={lonIn} onChange={(e) => setLonIn(e.target.value)} placeholder="Lon" className="w-full rounded-lg border p-2" />
          <button onClick={() => {
            const la = parseFloat(latIn), lo = parseFloat(lonIn);
            if (Number.isFinite(la) && Number.isFinite(lo)) load({ lat: la, lon: lo, label: "Manual" });
            else setErr("Enter valid numbers for lat/lon.");
          }} className="rounded-lg border px-3 py-2">Set</button>
        </div>
      </details>
      {loading && <p className="text-gray-500">{t("w_loading")}</p>}
      {err && <p className="rounded bg-red-50 p-2 text-red-700">{err}</p>}
    </div>
  );
}
