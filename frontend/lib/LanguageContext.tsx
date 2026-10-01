"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { getString, type Lang } from "./i18n";

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: (k: string) => string }>({
  lang: "en", setLang: () => {}, t: (k) => k,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    const s = localStorage.getItem("agri-lang") as Lang | null;
    if (s === "en" || s === "hi" || s === "mr" || s === "ta") setLangState(s);
  }, []);
  function setLang(l: Lang) {
    setLangState(l);
    localStorage.setItem("agri-lang", l);
    document.documentElement.lang = l;
  }
  return <Ctx.Provider value={{ lang, setLang, t: (k) => getString(lang, k) }}>{children}</Ctx.Provider>;
}

export function useLang() {
  return useContext(Ctx);
}
