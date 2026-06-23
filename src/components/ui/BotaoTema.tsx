"use client";

import { Sun, Moon } from "lucide-react";
import { useTema } from "@/components/providers/TemaProvider";

export function BotaoTema() {
  const { tema, alternarTema } = useTema();

  return (
    <button
      onClick={alternarTema}
      title={tema === "claro" ? "Ativar modo escuro" : "Ativar modo claro"}
      className="flex h-8 w-8 items-center justify-center rounded-lg text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 dark:text-gray-500 dark:hover:bg-white/10 dark:hover:text-gray-300"
    >
      {tema === "claro" ? <Moon size={16} /> : <Sun size={16} />}
    </button>
  );
}
