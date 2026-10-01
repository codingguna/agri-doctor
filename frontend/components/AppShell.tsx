"use client";
import Navbar from "./Navbar";
import { LanguageProvider, useLang } from "../lib/LanguageContext";

function Footer() {
  const { t } = useLang();
  return (
    <footer className="mx-auto max-w-5xl p-6 text-center text-xs text-gray-500">
      {t("footer")} • Demo: backend mock mode until model trained
    </footer>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      <Navbar />
      <div>{children}</div>
      <Footer />
    </LanguageProvider>
  );
}
