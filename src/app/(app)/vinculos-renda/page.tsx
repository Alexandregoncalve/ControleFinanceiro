"use client";

import { useState, useEffect, useCallback } from "react";
import { Briefcase, Plus, Pencil, Trash2, Power, Building2, FileText, Landmark } from "lucide-react";
import { FormVinculoCLT } from "@/components/forms/FormVinculoCLT";
import { FormVinculoAutonomo } from "@/components/forms/FormVinculoAutonomo";
import { FormVinculoMEI } from "@/components/forms/FormVinculoMEI";
import { FormVinculoSimples } from "@/components/forms/FormVinculoSimples";
import { LoadingPagina } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";
import { fmt } from "@/lib/utils";
import { calcularDescontoValeTransporte } from "@/lib/calculos-clt";
import { calcularINSSAutonomo, calcularDASMEI, calcularDASSimplesNacional, calcularFatorR, anexoEfetivoComFatorR } from "@/lib/calculos-tributarios";
import {
  VinculoRendaDTO,
  TipoVinculo,
  DetalhesCLT,
  DetalhesAutonomo,
  DetalhesMEI,
  DetalhesSimplesNacional,
} from "@/types/vinculo-renda";

const TIPOS_INFO: Record<TipoVinculo, { label: string; icon: React.ElementType; cor: string }> = {
  CLT: { label: "CLT", icon: Briefcase, cor: "#1565C0" },
  AUTONOMO: { label: "Autônomo", icon: Landmark, cor: "#2E7D32" },
  MEI: { label: "MEI", icon: Building2, cor: "#E65100" },
  SIMPLES_NACIONAL: { label: "Simples Nacional", icon: FileText, cor: "#6A1B9A" },
};

export default function VinculosRendaPage() {
  const [vinculos, setVinculos] = useState<VinculoRendaDTO[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [criandoTipo, setCriandoTipo] = useState<TipoVinculo | null>(null);
  const [escolhendoTipo, setEscolhendoTipo] = useState(false);
  const [editandoId, setEditandoId] = useState<number | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    const resultado = await apiFetch<{ vinculos: VinculoRendaDTO[] }>("/api/vinculos-renda");
    if (resultado.ok && resultado.data) setVinculos(resultado.data.vinculos);
    setCarregando(false);
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  async function excluir(id: number, apelido: string) {
    if (
      !confirm(
        `Excluir o vínculo "${apelido}"? As contas fixas geradas por ele serão desativadas, mas o histórico de transações é preservado.`
      )
    ) {
      return;
    }
    const resultado = await apiFetch(`/api/vinculos-renda/${id}`, {
      method: "DELETE",
      mensagemSucesso: "Vínculo excluído.",
    });
    if (resultado.ok) carregar();
  }

  async function alternarAtivo(v: VinculoRendaDTO) {
    const resultado = await apiFetch(`/api/vinculos-renda/${v.id}`, {
      method: "PUT",
      body: JSON.stringify({ tipo: v.tipo, apelido: v.apelido, ativo: !v.ativo, detalhes: v.detalhes }),
      mensagemSucesso: v.ativo ? "Vínculo desativado." : "Vínculo reativado.",
    });
    if (resultado.ok) carregar();
  }

  const editando = vinculos.find((v) => v.id === editandoId);

  function fecharFormularios() {
    setCriandoTipo(null);
    setEscolhendoTipo(false);
    setEditandoId(null);
  }

  function resumoFinanceiro(v: VinculoRendaDTO): { label: string; valor: number; cor: string }[] {
    if (v.tipo === "CLT") {
      const d = v.detalhes as DetalhesCLT;
      const itens = [{ label: "Salário bruto", valor: d.salarioBruto, cor: "#2E7D32" }];
      if (d.recebeValeTransporte) {
        itens.push({ label: "Vale-transporte", valor: -calcularDescontoValeTransporte(d.salarioBruto), cor: "#C62828" });
      }
      if (d.recebeValeAlimentacao) {
        itens.push({ label: "Vale-alimentação", valor: d.valorValeAlimentacao, cor: "#2E7D32" });
      }
      if (d.recebeAdiantamento) {
        itens.push({
          label: `Adiantamento (${d.percentualAdiantamento}%)`,
          valor: Math.round(((d.salarioBruto * d.percentualAdiantamento) / 100) * 100) / 100,
          cor: "#1565C0",
        });
      }
      return itens;
    }
    if (v.tipo === "AUTONOMO") {
      const d = v.detalhes as DetalhesAutonomo;
      return [
        { label: "Renda média", valor: d.rendaMediaMensal, cor: "#2E7D32" },
        { label: "INSS estimado", valor: -calcularINSSAutonomo(d.planoINSS, d.rendaMediaMensal), cor: "#C62828" },
      ];
    }
    if (v.tipo === "MEI") {
      const d = v.detalhes as DetalhesMEI;
      return [
        { label: "Faturamento médio", valor: d.faturamentoMedioMensal, cor: "#2E7D32" },
        { label: "DAS MEI", valor: -calcularDASMEI(d.atividade), cor: "#C62828" },
      ];
    }
    if (v.tipo === "SIMPLES_NACIONAL") {
      const d = v.detalhes as DetalhesSimplesNacional;
      const fatorR = calcularFatorR(d.folhaPagamento12meses, d.faturamento12meses);
      const anexoEf = anexoEfetivoComFatorR(d.anexo, fatorR);
      return [
        { label: "Faturamento médio", valor: d.faturamentoMedioMensal, cor: "#2E7D32" },
        {
          label: "DAS estimado",
          valor: -calcularDASSimplesNacional(anexoEf, d.faturamento12meses, d.faturamentoMedioMensal),
          cor: "#C62828",
        },
      ];
    }
    return [];
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-5 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Briefcase className="text-[#1565C0]" size={26} />
          <h1 className="text-xl font-bold text-[#1565C0]">VÍNCULOS DE RENDA</h1>
        </div>
        {!criandoTipo && !escolhendoTipo && !editandoId && (
          <button
            onClick={() => setEscolhendoTipo(true)}
            className="flex items-center gap-1.5 rounded-lg bg-[#1565C0] px-4 py-2 text-xs font-semibold text-white"
          >
            <Plus size={14} /> NOVO VÍNCULO
          </button>
        )}
      </div>

      <p className="text-xs text-gray-500">
        Você pode ter mais de um vínculo ao mesmo tempo (ex: CLT + MEI). Vínculos com valor fixo (CLT, MEI,
        Simples Nacional) geram automaticamente contas fixas em <strong>Contas Fixas</strong>. Renda
        autônoma é lançada manualmente em <strong>Avulso</strong>, por ser variável.
      </p>

      {escolhendoTipo && (
        <div className="grid grid-cols-2 gap-3 rounded-xl border border-gray-200 bg-white p-4 sm:grid-cols-4">
          {(Object.keys(TIPOS_INFO) as TipoVinculo[]).map((tipo) => {
            const info = TIPOS_INFO[tipo];
            const Icon = info.icon;
            return (
              <button
                key={tipo}
                onClick={() => {
                  setEscolhendoTipo(false);
                  setCriandoTipo(tipo);
                }}
                className="flex flex-col items-center gap-2 rounded-lg border border-gray-200 p-4 hover:border-gray-300 hover:bg-gray-50"
              >
                <Icon size={24} style={{ color: info.cor }} />
                <span className="text-xs font-semibold text-gray-700">{info.label}</span>
              </button>
            );
          })}
        </div>
      )}

      {criandoTipo === "CLT" && <FormVinculoCLT onSalvo={() => { fecharFormularios(); carregar(); }} onCancelar={fecharFormularios} />}
      {criandoTipo === "AUTONOMO" && <FormVinculoAutonomo onSalvo={() => { fecharFormularios(); carregar(); }} onCancelar={fecharFormularios} />}
      {criandoTipo === "MEI" && <FormVinculoMEI onSalvo={() => { fecharFormularios(); carregar(); }} onCancelar={fecharFormularios} />}
      {criandoTipo === "SIMPLES_NACIONAL" && <FormVinculoSimples onSalvo={() => { fecharFormularios(); carregar(); }} onCancelar={fecharFormularios} />}

      {editando?.tipo === "CLT" && (
        <FormVinculoCLT
          vinculoId={editando.id}
          apelidoInicial={editando.apelido}
          ativoInicial={editando.ativo}
          detalhesIniciais={editando.detalhes as DetalhesCLT}
          onSalvo={() => { fecharFormularios(); carregar(); }}
          onCancelar={fecharFormularios}
        />
      )}
      {editando?.tipo === "AUTONOMO" && (
        <FormVinculoAutonomo
          vinculoId={editando.id}
          apelidoInicial={editando.apelido}
          ativoInicial={editando.ativo}
          detalhesIniciais={editando.detalhes as DetalhesAutonomo}
          onSalvo={() => { fecharFormularios(); carregar(); }}
          onCancelar={fecharFormularios}
        />
      )}
      {editando?.tipo === "MEI" && (
        <FormVinculoMEI
          vinculoId={editando.id}
          apelidoInicial={editando.apelido}
          ativoInicial={editando.ativo}
          detalhesIniciais={editando.detalhes as DetalhesMEI}
          onSalvo={() => { fecharFormularios(); carregar(); }}
          onCancelar={fecharFormularios}
        />
      )}
      {editando?.tipo === "SIMPLES_NACIONAL" && (
        <FormVinculoSimples
          vinculoId={editando.id}
          apelidoInicial={editando.apelido}
          ativoInicial={editando.ativo}
          detalhesIniciais={editando.detalhes as DetalhesSimplesNacional}
          onSalvo={() => { fecharFormularios(); carregar(); }}
          onCancelar={fecharFormularios}
        />
      )}

      {carregando ? (
        <LoadingPagina />
      ) : vinculos.length === 0 && !criandoTipo && !escolhendoTipo ? (
        <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-gray-300 py-12 text-gray-400">
          <Briefcase size={32} />
          <p className="text-sm">Nenhum vínculo de renda cadastrado ainda.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {vinculos
            .filter((v) => v.id !== editandoId)
            .map((v) => {
              const info = TIPOS_INFO[v.tipo];
              const Icon = info.icon;
              return (
                <div
                  key={v.id}
                  className={`rounded-xl border p-4 ${
                    v.ativo ? "border-gray-200 bg-white" : "border-gray-200 bg-gray-50 opacity-60"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <Icon size={16} style={{ color: info.cor }} />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-gray-800">{v.apelido}</span>
                          <span
                            className="rounded-full px-2 py-0.5 text-[10px] font-bold text-white"
                            style={{ backgroundColor: info.cor }}
                          >
                            {info.label}
                          </span>
                          {!v.ativo && (
                            <span className="rounded-full bg-gray-200 px-2 py-0.5 text-[10px] font-bold text-gray-500">
                              INATIVO
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => setEditandoId(v.id)} title="Editar">
                        <Pencil size={15} className="text-[#1565C0]" />
                      </button>
                      <button onClick={() => alternarAtivo(v)} title={v.ativo ? "Desativar" : "Reativar"}>
                        <Power size={15} className={v.ativo ? "text-[#F57F17]" : "text-[#2E7D32]"} />
                      </button>
                      <button onClick={() => excluir(v.id, v.apelido)} title="Excluir">
                        <Trash2 size={15} className="text-red-500" />
                      </button>
                    </div>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-4 text-xs">
                    {resumoFinanceiro(v).map((item, i) => (
                      <div key={i}>
                        <span className="text-gray-400">{item.label}</span>
                        <p className="font-bold" style={{ color: item.cor }}>
                          {item.valor < 0 ? "-" : ""}
                          {fmt(Math.abs(item.valor))}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
