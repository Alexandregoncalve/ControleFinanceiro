"use client";

import { useState, useMemo } from "react";
import { Info, AlertTriangle } from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { LoadingBotao } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";
import { fmt } from "@/lib/utils";
import { calcularDASMEI, LIMITE_FATURAMENTO_MEI_ANUAL, AtividadeMEI } from "@/lib/calculos-tributarios";
import { DetalhesMEI, DETALHES_MEI_VAZIO } from "@/types/vinculo-renda";

interface FormVinculoMEIProps {
  vinculoId?: number;
  apelidoInicial?: string;
  ativoInicial?: boolean;
  detalhesIniciais?: DetalhesMEI;
  onSalvo: () => void;
  onCancelar: () => void;
}

const OPCOES_ATIVIDADE: { value: AtividadeMEI; label: string }[] = [
  { value: "comercio", label: "Comércio / Indústria" },
  { value: "servico", label: "Serviços" },
  { value: "ambos", label: "Comércio + Serviços" },
];

export function FormVinculoMEI({
  vinculoId,
  apelidoInicial = "",
  ativoInicial = true,
  detalhesIniciais,
  onSalvo,
  onCancelar,
}: FormVinculoMEIProps) {
  const [apelido, setApelido] = useState(apelidoInicial);
  const [ativo, setAtivo] = useState(ativoInicial);
  const [d, setD] = useState<DetalhesMEI>(detalhesIniciais ?? DETALHES_MEI_VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  function set<K extends keyof DetalhesMEI>(campo: K, valor: DetalhesMEI[K]) {
    setD((prev) => ({ ...prev, [campo]: valor }));
  }

  const dasValor = useMemo(() => calcularDASMEI(d.atividade), [d.atividade]);
  const faturamentoAnualProjetado = d.faturamentoMedioMensal * 12;
  const pctLimite = (faturamentoAnualProjetado / LIMITE_FATURAMENTO_MEI_ANUAL) * 100;
  const proximoDoLimite = pctLimite >= 80;

  async function salvar() {
    setErro("");
    if (!apelido.trim()) {
      setErro("Dê um apelido para este vínculo (ex: Minha Loja MEI).");
      return;
    }

    setSalvando(true);
    const payload = { tipo: "MEI" as const, apelido: apelido.trim(), ativo, detalhes: d };

    const resultado = vinculoId
      ? await apiFetch(`/api/vinculos-renda/${vinculoId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo atualizado! DAS sincronizado automaticamente.",
        })
      : await apiFetch("/api/vinculos-renda", {
          method: "POST",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo MEI criado! Conta fixa do DAS gerada automaticamente.",
        });

    setSalvando(false);
    if (resultado.ok) onSalvo();
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-[#FAC775] bg-[#FAEEDA] dark:bg-yellow-900/40 p-4">
      <div className="flex flex-wrap gap-2 sm:gap-3">
        <label className="flex w-56 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Apelido deste vínculo</span>
          <input
            type="text"
            placeholder="Ex: Minha Loja MEI"
            value={apelido}
            onChange={(e) => setApelido(e.target.value)}
            className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#854F0B]"
          />
        </label>
        <label className="flex w-56 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Nome fantasia</span>
          <input
            type="text"
            value={d.nomeFantasia}
            onChange={(e) => set("nomeFantasia", e.target.value)}
            className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#854F0B]"
          />
        </label>
        <label className="flex w-44 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">CNPJ</span>
          <input
            type="text"
            placeholder="00.000.000/0001-00"
            value={d.cnpj}
            onChange={(e) => set("cnpj", e.target.value)}
            className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#854F0B]"
          />
        </label>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium text-gray-600 dark:text-gray-300">Atividade principal</p>
        <div className="flex gap-2">
          {OPCOES_ATIVIDADE.map((o) => (
            <button
              key={o.value}
              onClick={() => set("atividade", o.value)}
              className={`rounded-lg border px-3 py-2 text-xs font-medium ${
                d.atividade === o.value
                  ? "border-[#854F0B] bg-white dark:bg-[#1E293B] text-[#854F0B]"
                  : "border-gray-300 dark:border-white/15 bg-white dark:bg-[#1E293B] text-gray-500 dark:text-gray-400 dark:text-gray-500"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-md bg-white dark:bg-[#1E293B] p-3">
        <div className="flex items-center gap-2">
          <Info size={14} className="text-[#0C447C] dark:text-blue-300" />
          <p className="text-xs text-gray-600 dark:text-gray-300">
            DAS calculado automaticamente: <strong className="text-[#0C447C] dark:text-blue-300">{fmt(dasValor)}</strong>/mês
            (INSS + {d.atividade === "comercio" ? "ICMS" : d.atividade === "servico" ? "ISS" : "ICMS + ISS"}),
            vencimento dia <strong>{d.diaVencimentoDAS}</strong>.
          </p>
        </div>
      </div>

      <InputMoeda
        label="Faturamento médio mensal"
        value={d.faturamentoMedioMensal}
        onChange={(v) => set("faturamentoMedioMensal", v)}
        className="w-full sm:w-56"
      />

      {d.faturamentoMedioMensal > 0 && (
        <div
          className={`flex items-start gap-2 rounded-md p-2.5 ${
            proximoDoLimite ? "bg-[#FCEBEB] dark:bg-red-900/40" : "bg-[#EAF3DE] dark:bg-green-900/40"
          }`}
        >
          {proximoDoLimite ? (
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-[#A32D2D]" />
          ) : (
            <Info size={14} className="mt-0.5 flex-shrink-0 text-[#3B6D11] dark:text-green-400" />
          )}
          <p className={`text-xs ${proximoDoLimite ? "text-[#A32D2D]" : "text-[#3B6D11] dark:text-green-400"}`}>
            Projeção anual: <strong>{fmt(faturamentoAnualProjetado)}</strong> ({pctLimite.toFixed(0)}% do
            limite de {fmt(LIMITE_FATURAMENTO_MEI_ANUAL)}/ano).
            {proximoDoLimite && " Você está perto do limite do MEI — considere migrar para Simples Nacional."}
          </p>
        </div>
      )}

      {erro && <p className="text-sm font-medium text-red-600">{erro}</p>}

      <div className="flex items-center gap-3">
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex h-10 items-center gap-2 rounded-lg bg-[#854F0B] px-5 text-xs font-semibold text-white disabled:opacity-60"
        >
          {salvando && <LoadingBotao size={14} />}
          {vinculoId ? "ATUALIZAR VÍNCULO" : "SALVAR VÍNCULO"}
        </button>
        <button onClick={onCancelar} className="text-xs text-gray-500 underline">
          Cancelar
        </button>
      </div>
    </div>
  );
}
