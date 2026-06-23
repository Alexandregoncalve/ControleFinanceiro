"use client";

import { useState, useEffect, useCallback } from "react";
import { ArrowUpRight, ArrowDownRight, Wallet, Repeat, LayoutDashboard } from "lucide-react";
import { SeletorMes } from "@/components/ui/SeletorMes";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardResumo } from "@/components/dashboard/CardResumo";
import { CardSaude } from "@/components/dashboard/CardSaude";
import { CardsBancos } from "@/components/dashboard/CardsBancos";
import { FormMetas } from "@/components/dashboard/FormMetas";
import { Secao } from "@/components/dashboard/Secao";
import { ComoEstaOMes } from "@/components/dashboard/ComoEstaOMes";
import { TopGastos } from "@/components/dashboard/TopGastos";
import { OrcamentoMensal } from "@/components/dashboard/OrcamentoMensal";
import { ComparativoMensal } from "@/components/dashboard/ComparativoMensal";
import { SkeletonCardsResumo, Skeleton } from "@/components/ui/Loading";
import { apiFetch } from "@/lib/api-fetch";
import { fmt, fmtPct, mesAtual } from "@/lib/utils";
import { DashboardData } from "@/types/dashboard";

function tendTxt(atual: number, anterior: number): string {
  if (anterior === 0) return "";
  const diff = ((atual - anterior) / anterior) * 100;
  const sinal = diff > 0 ? "▲" : "▼";
  return `${sinal} ${Math.abs(diff).toFixed(1)}% vs mês anterior`;
}

export default function DashboardPage() {
  const [mes, setMes] = useState(mesAtual());
  const [dados, setDados] = useState<DashboardData | null>(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async (mesParam: string) => {
    setCarregando(true);
    const resultado = await apiFetch<DashboardData>(
      `/api/dashboard?mes=${encodeURIComponent(mesParam)}`,
      { mensagemErroPadrao: "Não foi possível carregar o dashboard.", toastErro: !!dados }
    );
    if (resultado.ok && resultado.data) setDados(resultado.data);
    setCarregando(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    carregar(mes);
  }, [mes, carregar]);

  if (carregando && !dados) {
    return (
      <div className="flex flex-col gap-3 p-4">
        <div>
          <Skeleton className="h-6 w-56" />
          <Skeleton className="mt-2 h-[3px] w-44" />
        </div>
        <SkeletonCardsResumo />
        <div className="flex flex-col gap-2.5 lg:flex-row">
          <Skeleton className="h-32 flex-1" />
          <Skeleton className="h-32 flex-1" />
        </div>
      </div>
    );
  }

  if (!dados) return null;

  const { resumo, saldoAcumulado, bancos, cartao, fixas, saude, gastos, orcamentos } = dados;
  const positivo = resumo.resultado >= 0;

  return (
    <div className="flex flex-col gap-3 p-4">
      <PageHeader titulo="Dashboard financeiro" icon={LayoutDashboard} acoes={<SeletorMes mes={mes} onChange={setMes} />} />

      {/* LINHA 1: cards de resumo */}
      <div className="flex flex-wrap gap-2 sm:gap-2.5">
        <CardResumo
          titulo="RECEITAS DO MÊS"
          icon={ArrowUpRight}
          valor={resumo.receitas}
          corBorda="#3B6D11"
          variacaoTexto={tendTxt(resumo.receitas, resumo.receitasAnterior)}
          metaTexto={resumo.metaReceita > 0 ? `Meta: ${fmt(resumo.metaReceita)}` : "Sem meta definida"}
        />
        <CardResumo
          titulo="DESPESAS DO MÊS"
          icon={ArrowDownRight}
          valor={resumo.despesas}
          corBorda="#A32D2D"
          variacaoTexto={tendTxt(resumo.despesas, resumo.despesasAnterior)}
          metaTexto={resumo.metaDespesa > 0 ? `Meta: ${fmt(resumo.metaDespesa)}` : "Sem meta definida"}
        />
        <CardResumo
          titulo="RESULTADO"
          icon={Wallet}
          valor={resumo.resultado}
          corBorda={positivo ? "#3B6D11" : "#A32D2D"}
          destaque={{
            texto: positivo ? `✅ Sobrou ${fmt(resumo.resultado)} este mês` : `❌ Gastou ${fmt(Math.abs(resumo.resultado))} a mais`,
            cor: positivo ? "verde" : "vermelho",
          }}
          metaTexto={resumo.metaResultado > 0 ? `Meta: ${fmt(resumo.metaResultado)}` : "Sem meta definida"}
        />
        <CardResumo
          titulo="DESPESAS FIXAS"
          icon={Repeat}
          valor={fixas.valor}
          corBorda="#0C447C"
          variacaoTexto={`${fmtPct(fixas.percentualDespesas)} das despesas do mês`}
          metaTexto={
            fixas.pendentes > 0
              ? `⚠ ${fixas.pendentes} pendente(s) — ${fixas.lancadas} de ${fixas.totalContas} lançadas`
              : `✅ todas lançadas (${fixas.totalContas}/${fixas.totalContas})`
          }
        />
        <CardSaude saude={saude} />
      </div>

      {/* LINHA 2: Bancos + Metas */}
      <div className="flex flex-col gap-2.5 lg:flex-row">
        <div className="lg:w-[60%]">
          <CardsBancos bancos={bancos} />
          {saldoAcumulado !== 0 && (
            <p className="mt-2 text-[11px] text-gray-500">
              Saldo total acumulado: <span className="font-bold text-[#0C447C]">{fmt(saldoAcumulado)}</span>
            </p>
          )}
        </div>
        <div className="flex-1">
          <Secao titulo="🎯 Metas do mês" subtitulo="Copiada automaticamente do mês anterior">
            <FormMetas
              mes={mes}
              metaReceita={resumo.metaReceita}
              metaDespesa={resumo.metaDespesa}
              metaResultado={resumo.metaResultado}
              metaCopiada={resumo.metaCopiada}
              onSalvo={() => carregar(mes)}
            />
          </Secao>
        </div>
      </div>

      {/* LINHA 3: Como está o mês + Top gastos */}
      <div className="flex flex-col gap-2.5 lg:flex-row">
        <div className="flex-1">
          <Secao titulo="📊 Como está o mês" subtitulo="Receita vs despesa e histórico">
            <ComoEstaOMes resumo={resumo} historico={dados.historico} />
          </Secao>
        </div>
        <div className="flex-1">
          <Secao titulo="💸 Onde está indo o dinheiro" subtitulo="Maiores gastos do mês">
            <div className="max-h-80 overflow-y-auto">
              <TopGastos gastos={gastos} totalDespesas={resumo.despesas} />
            </div>
          </Secao>
        </div>
      </div>

      {/* LINHA 4: Orçamento mensal */}
      <Secao titulo="🎯 Orçamento mensal" subtitulo="Alertas e categorias monitoradas">
        <OrcamentoMensal orcamentos={orcamentos} />
      </Secao>

      {cartao.total > 0 && (
        <p className="text-[11px] text-gray-500">
          💳 Cartão de crédito: <span className="font-bold text-[#0C447C]">{fmt(cartao.total)}</span> (
          {fmtPct(cartao.percentualDespesas)} das despesas)
        </p>
      )}

      {/* LINHA 5: Comparativo mensal */}
      <Secao titulo="📅 Comparativo mensal" subtitulo="Evolução de gastos por conta, mês a mês">
        <ComparativoMensal />
      </Secao>
    </div>
  );
}
