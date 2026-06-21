"use client";

import { useState, useEffect, useCallback } from "react";
import { CreditCard, AlertTriangle } from "lucide-react";
import { SeletorMes } from "@/components/ui/SeletorMes";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingPagina } from "@/components/ui/Loading";
import { ComprasParceladas } from "@/components/cartao/ComprasParceladas";
import { fmt, fmtPct, mesAtual } from "@/lib/utils";

interface CompraCartao {
  descricao: string | null;
  valor: number;
  parcelaAtual: number;
  totalParcelas: number;
}

interface BlocoCartao {
  nome: string;
  tipo: string | null;
  bancoNome: string | null;
  limite: number;
  faturaAtual: number;
  parcelasFuturas: number;
  compras: CompraCartao[];
  temSubconta: boolean;
}

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
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <PageHeader
        titulo="Cartão de Crédito"
        icon={CreditCard}
        acoes={<SeletorMes mes={mes} onChange={setMes} />}
      />

      {carregando ? (
        <LoadingPagina />
      ) : cartoes.length === 0 ? (
        <div className="rounded-lg bg-[#FAEEDA] p-4">
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
                <span className="text-base font-bold text-[#0C447C]">{c.nome}</span>
                {c.tipo && (
                  <span className="rounded-full bg-[#0C447C] px-2 py-0.5 text-[10px] font-bold text-white">
                    {c.tipo}
                  </span>
                )}
                {c.bancoNome && <span className="text-xs text-gray-400">· {c.bancoNome}</span>}
              </div>

              <div className="flex flex-wrap gap-2.5">
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

              {c.limite > 0 && (
                <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">{fmt(c.faturaAtual)} usado</span>
                    <span className="font-bold" style={{ color: corUso }}>
                      {fmtPct(pctUso)} do limite
                    </span>
                  </div>
                  <div className="mt-1.5 h-2 rounded bg-[#F4F7FB]">
                    <div
                      className="h-2 rounded"
                      style={{ width: `${Math.min(100, pctUso)}%`, backgroundColor: corUso }}
                    />
                  </div>
                </div>
              )}

              {!c.temSubconta && (
                <div className="flex items-start gap-2 rounded-lg bg-[#FAEEDA] p-2.5">
                  <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-[#854F0B]" />
                  <p className="text-[11px] text-[#854F0B]">
                    Nenhuma subconta de lançamento encontrada para &quot;{c.nome}&quot;. Crie uma subconta
                    contendo o nome do cartão (ex: &quot;CARTAO {c.nome.toUpperCase()}&quot;) para que as
                    compras feitas no Avulso apareçam aqui.
                  </p>
                </div>
              )}

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5">
                <p className="mb-2 border-b-2 border-[#E6F1FB] pb-2 text-sm font-bold text-[#0C447C]">
                  Compras lançadas — {mes}
                </p>
                {c.compras.length === 0 ? (
                  <p className="text-xs italic text-gray-400">Nenhuma compra lançada neste mês.</p>
                ) : (
                  <div className="flex flex-col">
                    {c.compras.map((compra, idx) => {
                      const parcelado = compra.totalParcelas > 1;
                      return (
                        <div
                          key={idx}
                          className="flex items-center gap-2 border-b border-[#F4F7FB] py-1.5 last:border-0"
                        >
                          <span className="flex-1 truncate text-xs text-gray-700">
                            {compra.descricao || "(sem descrição)"}
                          </span>
                          <span className="w-24 flex-shrink-0 text-right text-xs font-bold text-[#A32D2D]">
                            {fmt(compra.valor)}
                          </span>
                          <span
                            className={`flex-shrink-0 rounded-full px-2 py-0.5 text-center text-[10px] font-bold ${
                              parcelado ? "bg-[#E6F1FB] text-[#0C447C]" : "bg-[#F4F7FB] text-gray-500"
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

              <div className="rounded-xl border border-[#E2E8F0] bg-white p-3.5">
                <p className="mb-2 border-b-2 border-[#E6F1FB] pb-2 text-sm font-bold text-[#0C447C]">
                  Parcelamentos em andamento
                </p>
                <ComprasParceladas filtrarPorConta={c.nome} />
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
