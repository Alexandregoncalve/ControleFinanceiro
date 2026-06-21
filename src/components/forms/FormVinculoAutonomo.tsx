"use client";

import { useState, useMemo } from "react";
import { Info } from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { LoadingBotao } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";
import { fmt } from "@/lib/utils";
import { calcularINSSAutonomo, PLANOS_INSS, PlanoINSS } from "@/lib/calculos-tributarios";
import { DetalhesAutonomo, DETALHES_AUTONOMO_VAZIO } from "@/types/vinculo-renda";

interface FormVinculoAutonomoProps {
  vinculoId?: number;
  apelidoInicial?: string;
  ativoInicial?: boolean;
  detalhesIniciais?: DetalhesAutonomo;
  onSalvo: () => void;
  onCancelar: () => void;
}

export function FormVinculoAutonomo({
  vinculoId,
  apelidoInicial = "",
  ativoInicial = true,
  detalhesIniciais,
  onSalvo,
  onCancelar,
}: FormVinculoAutonomoProps) {
  const [apelido, setApelido] = useState(apelidoInicial);
  const [ativo, setAtivo] = useState(ativoInicial);
  const [d, setD] = useState<DetalhesAutonomo>(detalhesIniciais ?? DETALHES_AUTONOMO_VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  function set<K extends keyof DetalhesAutonomo>(campo: K, valor: DetalhesAutonomo[K]) {
    setD((prev) => ({ ...prev, [campo]: valor }));
  }

  const inssEstimado = useMemo(
    () => calcularINSSAutonomo(d.planoINSS, d.rendaMediaMensal),
    [d.planoINSS, d.rendaMediaMensal]
  );

  async function salvar() {
    setErro("");
    if (!apelido.trim()) {
      setErro("Dê um apelido para este vínculo (ex: Freelas de Design).");
      return;
    }

    setSalvando(true);
    const payload = { tipo: "AUTONOMO" as const, apelido: apelido.trim(), ativo, detalhes: d };

    const resultado = vinculoId
      ? await apiFetch(`/api/vinculos-renda/${vinculoId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo atualizado!",
        })
      : await apiFetch("/api/vinculos-renda", {
          method: "POST",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo de renda autônoma criado!",
        });

    setSalvando(false);
    if (resultado.ok) onSalvo();
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-[#97C459] bg-[#EAF3DE] p-4">
      <div className="flex items-start gap-2 rounded-md bg-white p-2.5">
        <Info size={14} className="mt-0.5 flex-shrink-0 text-[#3B6D11]" />
        <p className="text-xs text-[#3B6D11]">
          Renda autônoma é variável — não criamos uma conta fixa de salário. Lance cada recebimento
          normalmente em <strong>Avulso</strong>. Aqui você só guarda os dados para referência e para os
          futuros módulos de Imposto de Renda.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className="flex w-60 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Apelido deste vínculo</span>
          <input
            type="text"
            placeholder="Ex: Freelas de Design"
            value={apelido}
            onChange={(e) => setApelido(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#3B6D11]"
          />
        </label>
        <label className="flex w-60 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Atividade</span>
          <input
            type="text"
            placeholder="Ex: Designer, Consultor, Motorista"
            value={d.atividade}
            onChange={(e) => set("atividade", e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#3B6D11]"
          />
        </label>
      </div>

      <InputMoeda
        label="Renda média mensal (estimativa, apenas referência)"
        value={d.rendaMediaMensal}
        onChange={(v) => set("rendaMediaMensal", v)}
        className="w-64"
      />

      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={d.prestaServicoPJ}
          onChange={(e) => set("prestaServicoPJ", e.target.checked)}
          className="h-4 w-4"
        />
        <span className="text-sm text-gray-700">Presto serviço para empresas (Pessoa Jurídica)</span>
      </label>

      <div className="rounded-lg bg-white p-3">
        <p className="mb-2 text-sm font-medium text-gray-700">Como você contribui para o INSS?</p>
        <div className="flex flex-col gap-2">
          {(Object.keys(PLANOS_INSS) as PlanoINSS[]).map((plano) => (
            <label key={plano} className="flex items-start gap-2 rounded-md p-2 hover:bg-gray-50">
              <input
                type="radio"
                checked={d.planoINSS === plano}
                onChange={() => set("planoINSS", plano)}
                className="mt-0.5 h-4 w-4"
              />
              <div>
                <p className="text-xs font-semibold text-gray-700">{PLANOS_INSS[plano].label}</p>
                <p className="text-[10px] text-gray-500">{PLANOS_INSS[plano].descricao}</p>
              </div>
            </label>
          ))}
        </div>
        {d.rendaMediaMensal > 0 && (
          <div className="mt-2 flex items-center gap-2 rounded-md bg-[#EAF3DE] px-3 py-2">
            <span className="text-xs text-[#3B6D11]">INSS estimado por mês:</span>
            <strong className="text-sm text-[#3B6D11]">{fmt(inssEstimado)}</strong>
          </div>
        )}
      </div>

      {erro && <p className="text-sm font-medium text-red-600">{erro}</p>}

      <div className="flex items-center gap-3">
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex h-10 items-center gap-2 rounded-lg bg-[#3B6D11] px-5 text-xs font-semibold text-white disabled:opacity-60"
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
