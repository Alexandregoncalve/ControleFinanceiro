"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, AlertTriangle } from "lucide-react";
import { SeletorMes } from "@/components/ui/SeletorMes";
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

const TIPO_CORES: Record<string, string> = {
  Crédito: "#1565C0",
  Débito: "#2E7D32",
  Ambos: "#6A1B9A",
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
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-bold text-[#1565C0]">Cartão de Crédito</h1>
          <div className="mt-1 h-[3px] w-44 rounded bg-[#2E7D32]" />
        </div>
        <SeletorMes mes={mes} onChange={setMes} />
      </div>

      {carregando ? (
        <div className="flex justify-center py-12">
          <Loader2 className="animate-spin text-[#1565C0]" size={24} />
        </div>
      ) : cartoes.length === 0 ? (
        <div className="rounded-lg bg-[#FFF8E1] p-4">
          <p className="text-sm text-[#F57F17]">
            Nenhum cartão encontrado. Cadastre um cartão em Bancos {">"} Cartões, e crie uma subconta com
            &quot;CARTAO&quot; ou &quot;CARTÃO&quot; no nome (Cadastro de Contas) para lançar as compras pelo
            Avulso.
          </p>
        </div>
      ) : (
        cartoes.map((c) => {
          const disponivel = Math.max(0, c.limite - c.faturaAtual);
          const pctUso = c.limite > 0 ? (c.faturaAtual / c.limite) * 100 : 0;
          const corUso = pctUso >= 100 ? "#C62828" : pctUso >= 80 ? "#F57F17" : "#1565C0";
          const tipoCor = TIPO_CORES[c.tipo ?? ""] ?? "#37474F";

          return (
            <div key={c.nome} className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <span className="text-base font-bold text-[#1565C0]">💳 {c.nome}</span>
                {c.tipo && (
                  <span
                    className="rounded-full px-2 py-0.5 text-[10px] font-bold text-white"
                    style={{ backgroundColor: tipoCor }}
                  >
                    {c.tipo}
                  </span>
                )}
                {c.bancoNome && <span className="text-xs text-gray-400">· {c.bancoNome}</span>}
              </div>

              <div className="flex flex-wrap gap-2.5">
                <div className="min-w-[150px] flex-1 rounded-xl p-3.5" style={{ backgroundColor: tipoCor }}>
                  <p className="text-[10px] font-bold text-white/90">FATURA DO MÊS</p>
                  <p className="text-xl font-bold text-white">{fmt(c.faturaAtual)}</p>
                  <p className="text-[10px] text-white/80">{c.compras.length} compra(s) lançada(s)</p>
                </div>
                <div className="min-w-[150px] flex-1 rounded-xl bg-[#2E7D32] p-3.5">
                  <p className="text-[10px] font-bold text-white/90">LIMITE DISPONÍVEL</p>
                  <p className="text-xl font-bold text-white">{c.limite > 0 ? fmt(disponivel) : "—"}</p>
                  <p className="text-[10px] text-white/80">
                    {c.limite > 0 ? `de ${fmt(c.limite)}` : "Limite não definido"}
                  </p>
                </div>
                <div className="min-w-[150px] flex-1 rounded-xl bg-[#C62828] p-3.5">
                  <p className="text-[10px] font-bold text-white/90">PARCELAS FUTURAS</p>
                  <p className="text-xl font-bold text-white">{fmt(c.parcelasFuturas)}</p>
                  <p className="text-[10px] text-white/80">comprometido em meses futuros</p>
                </div>
              </div>

              {c.limite > 0 && (
                <div className="rounded-xl border border-[#E8EEF7] bg-white p-3.5">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600">{fmt(c.faturaAtual)} usado</span>
                    <span className="font-bold" style={{ color: corUso }}>
                      {fmtPct(pctUso)} do limite
                    </span>
                  </div>
                  <div className="mt-1.5 h-2 rounded bg-[#F0F4FA]">
                    <div
                      className="h-2 rounded"
                      style={{ width: `${Math.min(100, pctUso)}%`, backgroundColor: corUso }}
                    />
                  </div>
                </div>
              )}

              {!c.temSubconta && (
                <div className="flex items-start gap-2 rounded-lg bg-[#FFF8E1] p-2.5">
                  <AlertTriangle size={14} className="mt-0.5 flex-shrink-0 text-[#F57F17]" />
                  <p className="text-[11px] text-[#F57F17]">
                    Nenhuma subconta de lançamento encontrada para &quot;{c.nome}&quot;. Crie uma subconta
                    contendo o nome do cartão (ex: &quot;CARTAO {c.nome.toUpperCase()}&quot;) para que as
                    compras feitas no Avulso apareçam aqui.
                  </p>
                </div>
              )}

              <div className="rounded-xl border border-[#E8EEF7] bg-white p-3.5">
                <p className="mb-2 border-b-2 border-[#E3F2FD] pb-2 text-sm font-bold text-[#1565C0]">
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
                          className="flex items-center gap-2 border-b border-[#F0F4FA] py-1.5 last:border-0"
                        >
                          <span className="flex-1 truncate text-xs text-gray-700">
                            {compra.descricao || "(sem descrição)"}
                          </span>
                          <span className="w-24 flex-shrink-0 text-right text-xs font-bold text-[#C62828]">
                            {fmt(compra.valor)}
                          </span>
                          <span
                            className={`flex-shrink-0 rounded-full px-2 py-0.5 text-center text-[10px] font-bold ${
                              parcelado ? "bg-[#E3F2FD] text-[#1565C0]" : "bg-[#F0F4FA] text-gray-500"
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
            </div>
          );
        })
      )}
    </div>
  );
}
