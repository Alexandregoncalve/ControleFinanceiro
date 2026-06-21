"use client";

import { useState, useMemo } from "react";
import { Info, AlertTriangle, TrendingDown } from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { LoadingBotao } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";
import { fmt, fmtPct } from "@/lib/utils";
import {
  calcularAliquotaEfetivaSimples,
  calcularDASSimplesNacional,
  calcularFatorR,
  anexoEfetivoComFatorR,
  DESCRICAO_ANEXO,
  LIMITE_FATURAMENTO_SIMPLES_ANUAL,
  AnexoSimples,
} from "@/lib/calculos-tributarios";
import { DetalhesSimplesNacional, DETALHES_SIMPLES_VAZIO } from "@/types/vinculo-renda";

interface FormVinculoSimplesProps {
  vinculoId?: number;
  apelidoInicial?: string;
  ativoInicial?: boolean;
  detalhesIniciais?: DetalhesSimplesNacional;
  onSalvo: () => void;
  onCancelar: () => void;
}

const ANEXOS: AnexoSimples[] = ["I", "II", "III", "IV", "V"];

export function FormVinculoSimples({
  vinculoId,
  apelidoInicial = "",
  ativoInicial = true,
  detalhesIniciais,
  onSalvo,
  onCancelar,
}: FormVinculoSimplesProps) {
  const [apelido, setApelido] = useState(apelidoInicial);
  const [ativo, setAtivo] = useState(ativoInicial);
  const [d, setD] = useState<DetalhesSimplesNacional>(detalhesIniciais ?? DETALHES_SIMPLES_VAZIO);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState("");

  function set<K extends keyof DetalhesSimplesNacional>(campo: K, valor: DetalhesSimplesNacional[K]) {
    setD((prev) => ({ ...prev, [campo]: valor }));
  }

  const fatorR = useMemo(
    () => calcularFatorR(d.folhaPagamento12meses, d.faturamento12meses),
    [d.folhaPagamento12meses, d.faturamento12meses]
  );
  const anexoEfetivo = useMemo(() => anexoEfetivoComFatorR(d.anexo, fatorR), [d.anexo, fatorR]);
  const beneficiadoPeloFatorR = d.anexo === "V" && anexoEfetivo === "III";

  const aliquotaEfetiva = useMemo(
    () => calcularAliquotaEfetivaSimples(anexoEfetivo, d.faturamento12meses),
    [anexoEfetivo, d.faturamento12meses]
  );
  const dasEstimado = useMemo(
    () => calcularDASSimplesNacional(anexoEfetivo, d.faturamento12meses, d.faturamentoMedioMensal),
    [anexoEfetivo, d.faturamento12meses, d.faturamentoMedioMensal]
  );

  const pctLimite = (d.faturamento12meses / LIMITE_FATURAMENTO_SIMPLES_ANUAL) * 100;
  const proximoDoLimite = pctLimite >= 80;

  async function salvar() {
    setErro("");
    if (!apelido.trim()) {
      setErro("Dê um apelido para este vínculo (ex: Minha Empresa LTDA).");
      return;
    }

    setSalvando(true);
    const payload = { tipo: "SIMPLES_NACIONAL" as const, apelido: apelido.trim(), ativo, detalhes: d };

    const resultado = vinculoId
      ? await apiFetch(`/api/vinculos-renda/${vinculoId}`, {
          method: "PUT",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo atualizado! DAS sincronizado automaticamente.",
        })
      : await apiFetch("/api/vinculos-renda", {
          method: "POST",
          body: JSON.stringify(payload),
          mensagemSucesso: "Vínculo Simples Nacional criado! Conta fixa do DAS gerada automaticamente.",
        });

    setSalvando(false);
    if (resultado.ok) onSalvo();
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-[#CE93D8] bg-[#F3E5F5] p-4">
      <div className="flex flex-wrap gap-3">
        <label className="flex w-56 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Apelido deste vínculo</span>
          <input
            type="text"
            placeholder="Ex: Minha Empresa LTDA"
            value={apelido}
            onChange={(e) => setApelido(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#6A1B9A]"
          />
        </label>
        <label className="flex w-56 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Razão social</span>
          <input
            type="text"
            value={d.razaoSocial}
            onChange={(e) => set("razaoSocial", e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#6A1B9A]"
          />
        </label>
        <label className="flex w-44 flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">CNPJ</span>
          <input
            type="text"
            placeholder="00.000.000/0001-00"
            value={d.cnpj}
            onChange={(e) => set("cnpj", e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#6A1B9A]"
          />
        </label>
      </div>

      <div>
        <p className="mb-2 text-xs font-medium text-gray-600">Anexo (definido pela atividade/CNAE)</p>
        <div className="flex flex-wrap gap-2">
          {ANEXOS.map((a) => (
            <button
              key={a}
              onClick={() => set("anexo", a)}
              title={DESCRICAO_ANEXO[a]}
              className={`rounded-lg border px-3 py-2 text-xs font-medium ${
                d.anexo === a ? "border-[#6A1B9A] bg-white text-[#6A1B9A]" : "border-gray-300 bg-white text-gray-500"
              }`}
            >
              Anexo {a}
            </button>
          ))}
        </div>
        <p className="mt-1 text-[10px] text-gray-500">{DESCRICAO_ANEXO[d.anexo]}</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <InputMoeda
          label="Faturamento últimos 12 meses (RBT12)"
          value={d.faturamento12meses}
          onChange={(v) => set("faturamento12meses", v)}
          className="w-60"
        />
        <InputMoeda
          label="Faturamento médio mensal"
          value={d.faturamentoMedioMensal}
          onChange={(v) => set("faturamentoMedioMensal", v)}
          className="w-56"
        />
      </div>

      {d.anexo === "V" && (
        <div className="rounded-lg bg-white p-3">
          <p className="mb-2 text-xs font-medium text-gray-600">
            Fator R (folha de pagamento ÷ faturamento dos últimos 12 meses)
          </p>
          <InputMoeda
            label="Folha de pagamento últimos 12 meses"
            value={d.folhaPagamento12meses}
            onChange={(v) => set("folhaPagamento12meses", v)}
            className="w-60"
          />
          {d.faturamento12meses > 0 && (
            <div
              className={`mt-2 flex items-start gap-2 rounded-md p-2.5 ${
                beneficiadoPeloFatorR ? "bg-[#E8F5E9]" : "bg-[#F5F5F5]"
              }`}
            >
              {beneficiadoPeloFatorR && <TrendingDown size={14} className="mt-0.5 flex-shrink-0 text-[#2E7D32]" />}
              <p className={`text-xs ${beneficiadoPeloFatorR ? "text-[#2E7D32]" : "text-gray-600"}`}>
                Fator R: <strong>{fmtPct(fatorR * 100)}</strong>
                {beneficiadoPeloFatorR
                  ? " — acima de 28%! Sua empresa será tributada pelo Anexo III (alíquotas menores)."
                  : " — abaixo de 28%, mantém tributação pelo Anexo V."}
              </p>
            </div>
          )}
        </div>
      )}

      {d.faturamento12meses > 0 && (
        <div className="rounded-md bg-white p-3">
          <div className="flex items-center gap-2">
            <Info size={14} className="text-[#1565C0]" />
            <p className="text-xs text-gray-600">
              Alíquota efetiva: <strong className="text-[#1565C0]">{fmtPct(aliquotaEfetiva * 100)}</strong> ·
              DAS estimado do mês: <strong className="text-[#1565C0]">{fmt(dasEstimado)}</strong>
            </p>
          </div>
        </div>
      )}

      {d.faturamento12meses > 0 && (
        <div
          className={`flex items-start gap-2 rounded-md p-2.5 ${proximoDoLimite ? "bg-[#FFEBEE]" : "bg-[#E8F5E9]"}`}
        >
          {proximoDoLimite ? (
            <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-[#C62828]" />
          ) : (
            <Info size={14} className="mt-0.5 flex-shrink-0 text-[#2E7D32]" />
          )}
          <p className={`text-xs ${proximoDoLimite ? "text-[#C62828]" : "text-[#2E7D32]"}`}>
            {pctLimite.toFixed(0)}% do limite anual do Simples ({fmt(LIMITE_FATURAMENTO_SIMPLES_ANUAL)}).
            {proximoDoLimite && " Você está próximo do limite — considere planejamento tributário."}
          </p>
        </div>
      )}

      {erro && <p className="text-sm font-medium text-red-600">{erro}</p>}

      <div className="flex items-center gap-3">
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex h-10 items-center gap-2 rounded-lg bg-[#6A1B9A] px-5 text-xs font-semibold text-white disabled:opacity-60"
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
