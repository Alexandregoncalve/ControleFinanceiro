"use client";

import { useState, useEffect } from "react";

interface Banco {
  id: number;
  nomeBanco: string;
  saldoInicial: number;
  saldoAtual?: number;
  agencia: string | null;
  numeroConta: string | null;
  codigoBanco: string | null;
  dataCriacao: string | null;
}

export function useBancos() {
  const [bancos, setBancos] = useState<Banco[]>([]);
  const [carregando, setCarregando] = useState(true);

  async function recarregar() {
    setCarregando(true);
    try {
      const res = await fetch("/api/bancos");
      if (res.ok) {
        const data = await res.json();
        setBancos(data.bancos);
      }
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    recarregar();
  }, []);

  return { bancos, carregando, recarregar };
}
