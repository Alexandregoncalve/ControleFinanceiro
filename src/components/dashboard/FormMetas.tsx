"use client";

import { useState, useEffect } from "react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { LoadingBotao } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";

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

  useEffect(() => {
    setReceita(metaReceita);
    setDespesa(metaDespesa);
    setResultado(metaResultado);
  }, [metaReceita, metaDespesa, metaResultado, mes]);

  async function salvar() {
    setSalvando(true);
    const resultadoFetch = await apiFetch("/api/metas", {
      method: "POST",
      body: JSON.stringify({
        mes,
        metaReceita: receita,
        metaDespesa: despesa,
        metaResultado: resultado,
      }),
      mensagemSucesso: "Metas salvas!",
      mensagemErroPadrao: "Não foi possível salvar as metas.",
    });
    setSalvando(false);
    if (resultadoFetch.ok) onSalvo();
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-end gap-2">
        <InputMoeda label="Meta Receita" value={receita} onChange={setReceita} className="w-full sm:w-36" />
        <InputMoeda label="Meta Despesa" value={despesa} onChange={setDespesa} className="w-full sm:w-36" />
        <InputMoeda label="Meta Resultado" value={resultado} onChange={setResultado} className="w-full sm:w-36" />
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex h-[38px] items-center justify-center gap-2 rounded-lg bg-[#0C447C] px-5 text-xs font-semibold text-white transition hover:bg-[#042C53] disabled:opacity-60"
        >
          {salvando && <LoadingBotao size={14} />}
          SALVAR
        </button>
      </div>
      {metaCopiada && (
        <p className="text-[10px] italic text-[#3B6D11]">💡 Copiada automaticamente do mês anterior</p>
      )}
    </div>
  );
}
