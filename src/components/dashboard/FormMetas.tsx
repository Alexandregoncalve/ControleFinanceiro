"use client";

import { useState, useEffect } from "react";
import { InputMoeda } from "@/components/ui/InputMoeda";

interface FormMetasProps {
  mes: string;
  metaReceita: number;
  metaDespesa: number;
  metaResultado: number;
  metaCopiada: boolean;
  onSalvo: () => void;
}

/** Traduz o formulário "Definir metas do mês" de views/dashboard.py */
export function FormMetas({
  mes,
  metaReceita,
  metaDespesa,
  metaResultado,
  metaCopiada,
  onSalvo,
}: FormMetasProps) {
  const [receita, setReceita] = useState(metaReceita);
  const [despesa, setDespesa] = useState(metaDespesa);
  const [resultado, setResultado] = useState(metaResultado);
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setReceita(metaReceita);
    setDespesa(metaDespesa);
    setResultado(metaResultado);
  }, [metaReceita, metaDespesa, metaResultado, mes]);

  async function salvar() {
    setSalvando(true);
    setMsg("");
    try {
      const res = await fetch("/api/metas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mes,
          metaReceita: receita,
          metaDespesa: despesa,
          metaResultado: resultado,
        }),
      });
      if (res.ok) {
        setMsg("✅ Metas salvas!");
        onSalvo();
      } else {
        setMsg("❌ Erro ao salvar.");
      }
    } catch {
      setMsg("❌ Erro de conexão.");
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-end gap-2">
        <InputMoeda label="Meta Receita" value={receita} onChange={setReceita} className="w-36" />
        <InputMoeda label="Meta Despesa" value={despesa} onChange={setDespesa} className="w-36" />
        <InputMoeda label="Meta Resultado" value={resultado} onChange={setResultado} className="w-36" />
        <button
          onClick={salvar}
          disabled={salvando}
          className="h-[38px] rounded-lg bg-[#1565C0] px-5 text-xs font-semibold text-white transition hover:bg-[#1257A8] disabled:opacity-60"
        >
          SALVAR
        </button>
      </div>
      {msg && <p className="text-xs text-gray-600">{msg}</p>}
      {metaCopiada && !msg && (
        <p className="text-[10px] italic text-[#2E7D32]">💡 Copiada automaticamente do mês anterior</p>
      )}
    </div>
  );
}
