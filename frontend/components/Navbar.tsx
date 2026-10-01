"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LANGS } from "../lib/i18n";
import { useLang } from "../lib/LanguageContext";

export default function Navbar() {
  const path = usePathname();
  const { lang, setLang, t } = useLang();
  const links = [
    { href: "/", label: t("nav_detect") },
    { href: "/library", label: t("nav_library") },
    { href: "/history", label: t("nav_history") },
    { href: "/dashboard", label: t("nav_dashboard") },
  ];
  return (
    <header className="sticky top-0 z-10 border-b bg-white/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between p-3">
        <Link href="/" className="text-lg font-extrabold text-green-800">🌱 {t("title")}</Link>
        <nav className="flex items-center gap-1 text-sm">
          {links.map((l) => (
            <Link key={l.href} href={l.href}
              className={`rounded-lg px-3 py-2 ${path === l.href ? "bg-green-700 text-white" : "hover:bg-green-100"}`}>
              {l.label}
            </Link>
          ))}
          <select value={lang} onChange={(e) => setLang(e.target.value as typeof lang)}
            className="ml-2 rounded border p-2 text-sm" aria-label="Language">
            {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </nav>
      </div>
    </header>
  );
}
