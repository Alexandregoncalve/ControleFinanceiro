"use client";

import { useState, useEffect } from "react";
import { Layers } from "lucide-react";
import { LoadingPagina } from "@/components/ui/Loading";
import { fmt } from "@/lib/utils";

interface ParcelaResumo {
  descBase: string;
  conta: string;
  valorParcela: number;
  valorTotal: number;
  pagas: number;
  totalParcelas: number;
  proximaData: string | null;
  status: "quitado" | "nao_iniciado" | "em_andamento";
}

const STATUS_INFO: Record<ParcelaResumo["status"], { label: string; cor: string; bg: string }> = {
  quitado: { label: "Quitado", cor: "#3B6D11", bg: "#EAF3DE" },
  nao_iniciado: { label: "Não iniciado", cor: "#64748B", bg: "#F1F5F9" },
  em_andamento: { label: "Em andamento", cor: "#0C447C", bg: "#E6F1FB" },
};

interface ComprasParceladasProps {
  /** Se informado, mostra só as parcelas daquele cartão (filtra por nome da conta). */
  filtrarPorConta?: string;
}

/**
 * Lista compras parceladas com barra de progresso. Reaproveitável tanto na visão
 * geral (dentro de Cartão de Crédito) quanto filtrada por um cartão específico.
 */
export function ComprasParceladas({ filtrarPorConta }: ComprasParceladasProps) {
  const [parcelas, setParcelas] = useState<ParcelaResumo[]>([]);
  const [resumo, setResumo] = useState({ totalPago: 0, totalEmAberto: 0, totalGeral: 0 });
  const [carregando, setCarregando] = useState(true);

  useEffect(() => {
    fetch("/api/parcelas")
      .then((res) => res.json())
      .then((data) => {
        setParcelas(data.parcelas);
        setResumo(data.resumo);
      })
      .finally(() => setCarregando(false));
  }, []);

  const lista = filtrarPorConta
    ? parcelas.filter((p) => p.conta.toLowerCase().includes(filtrarPorConta.toLowerCase()))
    : parcelas;

  if (carregando) return <LoadingPagina />;

  if (lista.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
        <Layers size={28} />
        <p className="text-xs">Nenhuma compra parcelada encontrada.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {!filtrarPorConta && (
        <div className="flex gap-2">
          <div className="flex-1 rounded-lg bg-[#EAF3DE] p-2.5 text-center">
            <p className="text-[10px] font-bold text-[#3B6D11]">JÁ PAGO</p>
            <p className="text-sm font-bold text-[#3B6D11]">{fmt(resumo.totalPago)}</p>
          </div>
          <div className="flex-1 rounded-lg bg-[#FCEBEB] p-2.5 text-center">
            <p className="text-[10px] font-bold text-[#A32D2D]">EM ABERTO</p>
            <p className="text-sm font-bold text-[#A32D2D]">{fmt(resumo.totalEmAberto)}</p>
          </div>
          <div className="flex-1 rounded-lg bg-[#E6F1FB] p-2.5 text-center">
            <p className="text-[10px] font-bold text-[#0C447C]">TOTAL GERAL</p>
            <p className="text-sm font-bold text-[#0C447C]">{fmt(resumo.totalGeral)}</p>
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {lista.map((p, i) => {
          const info = STATUS_INFO[p.status];
          const pct = (p.pagas / p.totalParcelas) * 100;
          return (
            <div key={i} className="rounded-xl border border-[#E2E8F0] bg-white p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-gray-800">{p.descBase || "(sem descrição)"}</p>
                  {!filtrarPorConta && <p className="text-xs text-gray-500">{p.conta}</p>}
                </div>
                <span
                  className="flex-shrink-0 rounded-full px-2.5 py-1 text-[10px] font-bold"
                  style={{ backgroundColor: info.bg, color: info.cor }}
                >
                  {info.label}
                </span>
              </div>

              <div className="mt-2 flex items-center gap-2">
                <div className="h-2 flex-1 rounded bg-gray-100">
                  <div className="h-2 rounded" style={{ width: `${pct}%`, backgroundColor: info.cor }} />
                </div>
                <span className="flex-shrink-0 text-xs font-medium text-gray-500">
                  {p.pagas}/{p.totalParcelas}
                </span>
              </div>

              <div className="mt-2 flex items-center justify-between text-xs">
                <span className="text-gray-500">
                  {fmt(p.valorParcela)} por parcela · Total {fmt(p.valorTotal)}
                </span>
                {p.proximaData && <span className="font-medium text-[#0C447C]">Próxima: {p.proximaData}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
