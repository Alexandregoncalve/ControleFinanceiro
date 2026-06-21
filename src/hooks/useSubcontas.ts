"use client";

import { useState, useEffect } from "react";

interface Subconta {
  id: number;
  categoriaId: number;
  nome: string;
  fixa: number;
  orcamento: number;
  diaVencimento: number | null;
  categoriaNome?: string;
  categoriaTipo?: "Receita" | "Despesa";
}

export function useSubcontas() {
  const [subcontas, setSubcontas] = useState<Subconta[]>([]);
  const [carregando, setCarregando] = useState(true);

  async function recarregar() {
    setCarregando(true);
    try {
      const res = await fetch("/api/subcontas");
      if (res.ok) {
        const data = await res.json();
        setSubcontas(data.subcontas);
      }
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    recarregar();
  }, []);

  return { subcontas, carregando, recarregar };
}
