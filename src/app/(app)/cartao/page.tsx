"use client";

import { useState, useEffect, useCallback } from "react";
import { CreditCard, AlertTriangle, Layers } from "lucide-react";
import { SeletorMes } from "@/components/ui/SeletorMes";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingPagina } from "@/components/ui/Loading";
import { fmt, fmtPct } from "@/lib/utils";
import { mesAtual } from "@/lib/utils";

interface CompraCartao {
  descricao: string | null;
  valor: number;
  parcelaAtual: number;
  totalParcelas: number;
  data: string;
}

interface Provisionamento {
  mes: string;
  valor: number;
}

interface Parcelamento {
  descBase: string;
  valorParcela: number;
  valorTotal: number;
  pagas: number;
  totalParcelas: number;
  proximaData: string | null;
  status: "quitado" | "nao_iniciado" | "em_andamento";
}

interface BlocoCartao {
  nome: string;
  tipo: string | null;
  bancoNome: string | null;
  limite: number;
  faturaAtual: number;
  proximaFatura: Provisionamento | null;
  parcelasFuturas: number;
  provisionamento: Provisionamento[];
  compras: CompraCartao[];
  parcelamentos: Parcelamento[];
  temSubconta: boolean;
}

const STATUS_INFO: Record<Parcelamento["status"], { label: string; cor: string; bg: string }> = {
  quitado: { label: "Quitado", cor: "#3B6D11", bg: "#EAF3DE" },
  nao_iniciado: { label: "Não iniciado", cor: "#64748B", bg: "#F1F5F9" },
  em_andamento: { label: "Em andamento", cor: "#0C447C", bg: "#E6F1FB" },
};

export default function CartaoPage() {
  const [mes, setMes] = useState(mesAtual());
  const [cartoes, setCartoes] = useState<BlocoCartao[]>([]);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async (mesParam: string) => {
    setCarregando(true);
    try {
      const res = await fetch(`/api/cartao-fatura?mes=${encodeURIComponent(mesParam)}`);
      if (res.ok) {
        const data = await res.json();
        setCartoes(data.cartoes);
      }
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar(mes);
  }, [mes, carregar]);

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-4 sm:p-6">
      <PageHeader
        titulo="Cartão de Crédito"
        icon={CreditCard}
        acoes={<SeletorMes mes={mes} onChange={setMes} />}
      />

      {carregando ? (
        <LoadingPagina />
      ) : cartoes.length === 0 ? (
        <div className="rounded-lg bg-[#FAEEDA] dark:bg-yellow-900/40 p-4">
          <p className="text-sm text-[#854F0B]">
            Nenhum cartão encontrado. Cadastre um cartão em Bancos {">"} Cartões, e crie uma subconta com
            &quot;CARTAO&quot; ou &quot;CARTÃO&quot; no nome (Cadastro de Contas) para lançar as compras pelo
            Avulso.
          </p>
        </div>
      ) : (
        cartoes.map((c) => {
          const disponivel = Math.max(0, c.limite - c.faturaAtual);
          const pctUso = c.limite > 0 ? (c.faturaAtual / c.limite) * 100 : 0;
          const corUso = pctUso >= 100 ? "#A32D2D" : pctUso >= 80 ? "#854F0B" : "#0C447C";

          return (
            <div key={c.nome} className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-[#0C447C] dark:text-blue-300">{c.nome}</span>
                {c.tipo && (
                  <span className="rounded-full bg-[#0C447C] px-2 py-0.5 text-[10px] font-bold text-white">
                    {c.tipo}
                  </span>
                )}
                {c.bancoNome && <span className="text-xs text-gray-400 dark:text-gray-500">· {c.bancoNome}</span>}
              </div>

              <div className="flex flex-wrap gap-2 sm:gap-2.5">
                <div className="min-w-[150px] flex-1 rounded-xl bg-[#0C447C] p-3.5">
                  <p className="text-[10px] font-bold text-white/90">FATURA DO MÊS</p>
                  <p className="text-xl font-bold text-white">{fmt(c.faturaAtual)}</p>
                  <p className="text-[10px] text-white/80">{c.compras.length} compra(s) lançada(s)</p>
                </div>
                <div className="min-w-[150px] flex-1 rounded-xl bg-[#3B6D11] p-3.5">
                  <p className="text-[10px] font-bold text-white/90">LIMITE DISPONÍVEL</p>
                  <p className="text-xl font-bold text-white">{c.limite > 0 ? fmt(disponivel) : "—"}</p>
                  <p className="text-[10px] text-white/80">
                    {c.limite > 0 ? `de ${fmt(c.limite)}` : "Limite não definido"}
                  </p>
                </div>
                <div className="min-w-[150px] flex-1 rounded-xl bg-[#185FA5] p-3.5">
                  <p className="text-[10px] font-bold text-white/90">PARCELAS FUTURAS</p>
                  <p className="text-xl font-bold text-white">{fmt(c.parcelasFuturas)}</p>
                  <p className="text-[10px] text-white/80">comprometido em meses futuros</p>
                </div>
              </div>

              {/* Próxima fatura a vencer — substitui o antigo (e equivocado) "pago vs em aberto" */}
              {c.proximaFatura && (
                <div className="flex items-center gap-2 rounded-lg bg-[#E6F1FB] dark:bg-blue-900/40 p-2.5">
                  <span className="text-[11px] font-bold text-[#0C447C] dark:text-blue-300">PRÓXIMA FATURA</span>
                  <span className="text-xs text-[#0C447C] dark:text-blue-300">
                    {fmt(c.proximaFatura.valor)} em {c.proximaFatura.mes}
                  </span>
                </div>
              )}

              {c.limite > 0 && (
                <div className="rounded-xl border border-[#E2E8F0] dark:border-white/10 bg-white dark:bg-[#1E293B] p-3.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-300">{fmt(c.faturaAtual)} usado</span>
                    <span className="font-bold" style={{ color: corUso }}>
                      {fmtPct(pctUso)} do limite
                    </span>
                  </div>
                  <div className="mt-1.5 h-2 rounded bg-[#F4F7FB] dark:bg-[#0F172A]">
                    <div
                      className="h-2 rounded"
                      style={{ width: `${Math.min(100, pctUso)}%`, backgroundColor: corUso }}
                    />
                  </div>
                </div>
              )}

              {!c.temSubconta && (
                <div className="flex items-start gap-2 rounded-lg bg-[#FAEEDA] dark:bg-yellow-900/40 p-2.5">
                  <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-[#854F0B]" />
                  <p className="text-[11px] text-[#854F0B]">
                    Nenhuma subconta de lançamento encontrada para &quot;{c.nome}&quot;. Crie uma subconta
                    contendo o nome do cartão (ex: &quot;CARTAO {c.nome.toUpperCase()}&quot;) para que as
                    compras feitas no Avulso apareçam aqui.
                  </p>
                </div>
              )}

              <div className="rounded-xl border border-[#E2E8F0] dark:border-white/10 bg-white dark:bg-[#1E293B] p-3.5">
                <p className="mb-2 border-b-2 border-[#E6F1FB] pb-2 text-sm font-bold text-[#0C447C] dark:text-blue-300">
                  Compras lançadas — {mes}
                </p>
                {c.compras.length === 0 ? (
                  <p className="text-xs italic text-gray-400 dark:text-gray-500">Nenhuma compra lançada neste mês.</p>
                ) : (
                  <div className="flex flex-col">
                    {c.compras.map((compra, idx) => {
                      const parcelado = compra.totalParcelas > 1;
                      return (
                        <div
                          key={idx}
                          className="flex items-center gap-2 border-b border-[#F4F7FB] py-1.5 last:border-0"
                        >
                          <span className="flex-1 truncate text-xs text-gray-700 dark:text-gray-200">
                            {compra.descricao || "(sem descrição)"}
                          </span>
                          <span className="w-20 flex-shrink-0 text-[10px] text-gray-400 dark:text-gray-500">{compra.data}</span>
                          <span className="w-24 flex-shrink-0 text-right text-xs font-bold text-[#A32D2D]">
                            {fmt(compra.valor)}
                          </span>
                          <span
                            className={`flex-shrink-0 rounded-full px-2 py-0.5 text-center text-[10px] font-bold ${
                              parcelado ? "bg-[#E6F1FB] dark:bg-blue-900/40 text-[#0C447C] dark:text-blue-300" : "bg-[#F4F7FB] dark:bg-[#0F172A] text-gray-500 dark:text-gray-400 dark:text-gray-500"
                            }`}
                          >
                            {parcelado ? `${compra.parcelaAtual}/${compra.totalParcelas}x` : "à vista"}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Provisionamento — quanto vai cair na fatura nos próximos meses */}
              {c.provisionamento.length > 0 && (
                <div className="rounded-xl border border-[#E2E8F0] dark:border-white/10 bg-white dark:bg-[#1E293B] p-3.5">
                  <p className="mb-2 border-b-2 border-[#E6F1FB] pb-2 text-sm font-bold text-[#0C447C] dark:text-blue-300">
                    Provisionamento — próximos meses
                  </p>
                  <div className="flex flex-col">
                    {c.provisionamento.map((p) => (
                      <div
                        key={p.mes}
                        className="flex items-center justify-between border-b border-[#F4F7FB] py-1.5 text-xs last:border-0"
                      >
                        <span className="font-medium text-gray-600 dark:text-gray-300">{p.mes}</span>
                        <span className="font-bold text-[#A32D2D]">{fmt(p.valor)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Parcelamentos em andamento — agora filtrado pela própria subconta, não por texto */}
              <div className="rounded-xl border border-[#E2E8F0] dark:border-white/10 bg-white dark:bg-[#1E293B] p-3.5">
                <p className="mb-2 border-b-2 border-[#E6F1FB] pb-2 text-sm font-bold text-[#0C447C] dark:text-blue-300">
                  Parcelamentos em andamento
                </p>
                {c.parcelamentos.length === 0 ? (
                  <div className="flex flex-col items-center gap-2 py-6 text-gray-400 dark:text-gray-500">
                    <Layers size={24} />
                    <p className="text-xs">Nenhuma compra parcelada encontrada.</p>
                  </div>
                ) : (
                  <div className="flex flex-col gap-2">
                    {c.parcelamentos.map((p, i) => {
                      const info = STATUS_INFO[p.status];
                      const pct = (p.pagas / p.totalParcelas) * 100;
                      return (
                        <div key={i} className="rounded-lg border border-[#F4F7FB] p-2.5">
                          <div className="flex items-start justify-between gap-2">
                            <p className="text-xs font-semibold text-gray-800 dark:text-gray-100">{p.descBase}</p>
                            <span
                              className="flex-shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold"
                              style={{ backgroundColor: info.bg, color: info.cor }}
                            >
                              {info.label}
                            </span>
                          </div>
                          <div className="mt-1.5 flex items-center gap-2">
                            <div className="h-1.5 flex-1 rounded bg-gray-100 dark:bg-white/10">
                              <div
                                className="h-1.5 rounded"
                                style={{ width: `${pct}%`, backgroundColor: info.cor }}
                              />
                            </div>
                            <span className="flex-shrink-0 text-[10px] font-medium text-gray-500 dark:text-gray-400 dark:text-gray-500">
                              {p.pagas}/{p.totalParcelas}
                            </span>
                          </div>
                          <div className="mt-1.5 flex items-center justify-between text-[10px]">
                            <span className="text-gray-500 dark:text-gray-400 dark:text-gray-500">
                              {fmt(p.valorParcela)}/parcela · Total {fmt(p.valorTotal)}
                            </span>
                            {p.proximaData && (
                              <span className="font-medium text-[#0C447C] dark:text-blue-300">Próxima: {p.proximaData}</span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
