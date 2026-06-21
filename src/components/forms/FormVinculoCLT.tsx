"use client";

import { useState, useEffect, useMemo } from "react";
import { Info } from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { LoadingBotao } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";
import { fmt } from "@/lib/utils";
import { calcularDescontoValeTransporte, calcularAdiantamentoSugerido } from "@/lib/calculos-clt";
import { DetalhesCLT, DETALHES_CLT_VAZIO } from "@/types/vinculo-renda";

interface FormVinculoCLTProps {
  vinculoId?: number; // se informado, é edição
  apelidoInicial?: string;
  ativoInicial?: boolean;
  detalhesIniciais?: DetalhesCLT;
  onSalvo: () => void;
  onCancelar: () => void;
}

/** Formulário de vínculo CLT com cálculo automático de VT (6% legal) e adiantamento (sugestão 40%) */
export function FormVinculoCLT({
  vinculoId,
  apelidoInicial = "",
  ativoInicial = true,
  detalhesIniciais,
  onSalvo,
  onCancelar,
}: FormVinculoCLTProps) {
  const [apelido, setApelido] = useState(apelidoInicial);
  const [ativo, setAtivo] = useState(ativoInicial);
  const [d, setD] = useState<DetalhesCLT>(detalhesIniciais ?? DETALHES_CLT_VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  // Quando o usuário liga o adiantamento pela primeira vez, sugere 40% automaticamente
  useEffect(() => {
    if (d.recebeAdiantamento && d.percentualAdiantamento === 0) {
      setD((prev) => ({ ...prev, percentualAdiantamento: 40 }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [d.recebeAdiantamento]);

  const descontoVT = useMemo(() => calcularDescontoValeTransporte(d.salarioBruto), [d.salarioBruto]);
  const valorAdiantamento = useMemo(
    () => Math.round(((d.salarioBruto * d.percentualAdiantamento) / 100) * 100) / 100,
    [d.salarioBruto, d.percentualAdiantamento]
  );

  function set<K extends keyof DetalhesCLT>(campo: K, valor: DetalhesCLT[K]) {
    setD((prev) => ({ ...prev, [campo]: valor }));
  }

  async function salvar() {
    setErro("");
    if (!apelido.trim()) {
      setErro("Dê um apelido para este vínculo (ex: Emprego Principal).");
      return;
    }
    if (d.salarioBruto <= 0) {
      setErro("Informe o salário bruto.");
      return;
    }

    setSalvando(true);
    const payload = { tipo: "CLT" as const, apelido: apelido.trim(), ativo, detalhes: d };

    const resultado = vinculoId
      ? await apiFetch(`/api/vinculos-renda/${vinculoId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo atualizado! Contas fixas sincronizadas automaticamente.",
        })
      : await apiFetch("/api/vinculos-renda", {
          method: "POST",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo criado! Contas fixas geradas automaticamente.",
        });

    setSalvando(false);
    if (resultado.ok) onSalvo();
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-[#85B7EB] bg-[#E6F1FB] p-4">
      <div className="flex flex-wrap gap-3">
        <label className="flex w-60 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Apelido deste vínculo</span>
          <input
            type="text"
            placeholder="Ex: Emprego Principal"
            value={apelido}
            onChange={(e) => setApelido(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
          />
        </label>
        <label className="flex w-56 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Empresa</span>
          <input
            type="text"
            value={d.empresa}
            onChange={(e) => set("empresa", e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
          />
        </label>
        <label className="flex w-44 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Cargo</span>
          <input
            type="text"
            value={d.cargo}
            onChange={(e) => set("cargo", e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
          />
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        <InputMoeda
          label="Salário Bruto"
          value={d.salarioBruto}
          onChange={(v) => set("salarioBruto", v)}
          className="w-44"
        />
        <label className="flex w-44 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Dia de pagamento (opcional)</span>
          <input
            type="number"
            min={1}
            max={31}
            placeholder="Auto (5º dia útil)"
            value={d.diaPagamento ?? ""}
            onChange={(e) => set("diaPagamento", e.target.value ? parseInt(e.target.value) : null)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
          />
          <span className="text-[10px] text-gray-400">
            Em branco, considera o prazo legal: até o 5º dia útil (CLT art. 459).
          </span>
        </label>
      </div>

      {/* Vale-transporte — checkbox liga cálculo automático */}
      <div className="rounded-lg bg-white p-3">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={d.recebeValeTransporte}
            onChange={(e) => set("recebeValeTransporte", e.target.checked)}
            className="h-4 w-4"
          />
          <span className="text-sm font-medium text-gray-700">Recebo vale-transporte</span>
        </label>
        {d.recebeValeTransporte && (
          <div className="mt-2 flex items-start gap-2 rounded-md bg-[#EAF3DE] p-2.5">
            <Info size={14} className="mt-0.5 flex-shrink-0 text-[#3B6D11]" />
            <p className="text-xs text-[#3B6D11]">
              Desconto calculado automaticamente: <strong>{fmt(descontoVT)}</strong> (6% do salário bruto,
              teto máximo conforme Lei 7.418/85).
            </p>
          </div>
        )}
      </div>

      {/* Vale-alimentação — checkbox liga campo de valor livre */}
      <div className="rounded-lg bg-white p-3">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={d.recebeValeAlimentacao}
            onChange={(e) => set("recebeValeAlimentacao", e.target.checked)}
            className="h-4 w-4"
          />
          <span className="text-sm font-medium text-gray-700">Recebo vale-alimentação/refeição</span>
        </label>
        {d.recebeValeAlimentacao && (
          <div className="mt-2">
            <InputMoeda
              label="Valor mensal (não há % fixo em lei, varia por empresa)"
              value={d.valorValeAlimentacao}
              onChange={(v) => set("valorValeAlimentacao", v)}
              className="w-52"
            />
          </div>
        )}
      </div>

      {/* Adiantamento — checkbox liga cálculo com sugestão editável */}
      <div className="rounded-lg bg-white p-3">
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={d.recebeAdiantamento}
            onChange={(e) => set("recebeAdiantamento", e.target.checked)}
            className="h-4 w-4"
          />
          <span className="text-sm font-medium text-gray-700">Recebo adiantamento salarial</span>
        </label>
        {d.recebeAdiantamento && (
          <div className="mt-2 flex flex-wrap items-end gap-3">
            <label className="flex w-32 flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">% do salário</span>
              <input
                type="number"
                min={0}
                max={100}
                value={d.percentualAdiantamento}
                onChange={(e) => set("percentualAdiantamento", Number(e.target.value))}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
              />
            </label>
            <label className="flex w-36 flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">Dia do adiantamento</span>
              <input
                type="number"
                min={1}
                max={31}
                value={d.diaAdiantamento ?? ""}
                onChange={(e) => set("diaAdiantamento", e.target.value ? parseInt(e.target.value) : null)}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
              />
            </label>
            <p className="pb-2 text-xs text-gray-500">
              Valor estimado: <strong className="text-[#0C447C]">{fmt(valorAdiantamento)}</strong>
              <span className="block text-[10px] text-gray-400">(sugestão de mercado, não é definido em lei)</span>
            </p>
          </div>
        )}
      </div>

      {erro && <p className="text-sm font-medium text-red-600">{erro}</p>}

      <div className="flex items-center gap-3">
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex h-10 items-center gap-2 rounded-lg bg-[#0C447C] px-5 text-xs font-semibold text-white disabled:opacity-60"
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
