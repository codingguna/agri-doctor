"use client";
import { useEffect, useRef, useState } from "react";
import { useLang } from "../lib/LanguageContext";

export default function LiveCamera({ onCapture }: { onCapture: (f: File) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [on, setOn] = useState(false);
  const [ready, setReady] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const { t } = useLang();

  function stopTracks() {
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
    streamRef.current = null;
    if (video.current) video.current.srcObject = null;
  }

  // Always release camera on unmount / page leave — fixes "camera in use after close"
  useEffect(() => {
    return () => stopTracks();
  }, []);

  async function start() {
    setErr(null);
    setReady(false);
    stopTracks(); // release previous stream before asking again
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        setErr(t("cam_blocked"));
        return;
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      setOn(true); // mount visible <video> first, attach in effect below
      // Attach on next tick so single video element exists
      requestAnimationFrame(async () => {
        if (video.current) {
          video.current.srcObject = stream;
          video.current.muted = true;
          try {
            await video.current.play();
          } catch {
            // play() can reject if not yet ready; loadedmetadata handler retries
          }
        }
      });
    } catch {
      stopTracks();
      setOn(false);
      setErr(t("cam_blocked"));
    }
  }

  function stop() {
    stopTracks();
    setOn(false);
    setReady(false);
  }

  function snap() {
    const v = video.current;
    if (!v || !v.videoWidth) {
      setErr("Camera not ready yet — wait 1 sec and retry.");
      return;
    }
    const c = document.createElement("canvas");
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d")?.drawImage(v, 0, 0);
    c.toBlob((b) => { if (b) onCapture(new File([b], `live-${Date.now()}.jpg`, { type: "image/jpeg" })); }, "image/jpeg", 0.92);
  }

  return (
    <div className="rounded-2xl border bg-white p-4 text-sm shadow">
      <p className="font-bold">📷 {t("cam_t")} <span className="font-normal text-gray-500">— {t("cam_s")}</span></p>

      {/* Single video element always mounted — fixes black screen from dual-ref bug */}
      <video
        ref={video}
        playsInline
        muted
        autoPlay
        className={`mt-2 max-h-64 w-full rounded-lg bg-black ${on ? "" : "hidden"}`}
        onLoadedMetadata={() => {
          setReady(true);
          video.current?.play().catch(() => {});
        }}
      />

      {!on ? (
        <button onClick={start} className="mt-2 rounded-lg bg-gray-900 px-4 py-2 text-white">{t("cam_open")}</button>
      ) : (
        <div className="mt-2 flex gap-2">
          <button onClick={snap} disabled={!ready} className="rounded-lg bg-green-700 px-4 py-2 font-semibold text-white disabled:opacity-50">
            {t("cam_cap")}
          </button>
          <button onClick={stop} className="rounded-lg border px-4 py-2">{t("close")}</button>
        </div>
      )}
      {err && <p className="mt-2 text-red-700">{err}</p>}
    </div>
  );
}
