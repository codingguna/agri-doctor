"use client";
import UploadForm from "../components/UploadForm";
import { useLang } from "../lib/LanguageContext";

export default function Home() {
  const { t } = useLang();
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <UploadForm />
      <div className="grid gap-4 md:grid-cols-3 text-sm">
        <div className="rounded-2xl bg-white p-4 shadow"><b>{t("step1t")}</b><p className="text-gray-600">{t("step1d")}</p></div>
        <div className="rounded-2xl bg-white p-4 shadow"><b>{t("step2t")}</b><p className="text-gray-600">{t("step2d")}</p></div>
        <div className="rounded-2xl bg-white p-4 shadow"><b>{t("step3t")}</b><p className="text-gray-600">{t("step3d")}</p></div>
      </div>
    </main>
  );
}
