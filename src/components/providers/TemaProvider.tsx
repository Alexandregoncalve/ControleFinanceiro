"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Tema = "claro" | "escuro";

interface TemaContextValue {
  tema: Tema;
  alternarTema: () => void;
}

const TemaContext = createContext<TemaContextValue | null>(null);

const CHAVE_STORAGE = "financa_simples_tema";

export function TemaProvider({ children }: { children: ReactNode }) {
  const [tema, setTema] = useState<Tema>("claro");
  const [montado, setMontado] = useState(false);

  // Lê a preferência salva (ou do sistema, na primeira vez) só no cliente,
  // para evitar mismatch de hidratação entre servidor e navegador.
  useEffect(() => {
    const salvo = localStorage.getItem(CHAVE_STORAGE) as Tema | null;
    if (salvo === "claro" || salvo === "escuro") {
      setTema(salvo);
    } else {
      const prefereEscuro = window.matchMedia("(prefers-color-scheme: dark)").matches;
      setTema(prefereEscuro ? "escuro" : "claro");
    }
    setMontado(true);
  }, []);

  useEffect(() => {
    if (!montado) return;
    document.documentElement.classList.toggle("dark", tema === "escuro");
    localStorage.setItem(CHAVE_STORAGE, tema);
  }, [tema, montado]);

  function alternarTema() {
    setTema((prev) => (prev === "claro" ? "escuro" : "claro"));
  }

  return <TemaContext.Provider value={{ tema, alternarTema }}>{children}</TemaContext.Provider>;
}

export function useTema() {
  const ctx = useContext(TemaContext);
  if (!ctx) throw new Error("useTema precisa estar dentro de um TemaProvider");
  return ctx;
}
