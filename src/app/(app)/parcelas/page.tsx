"use client";

import { useState, useEffect } from "react";
import { Loader2, Layers } from "lucide-react";
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
  quitado: { label: "Quitado", cor: "#2E7D32", bg: "#E8F5E9" },
  nao_iniciado: { label: "Não iniciado", cor: "#888888", bg: "#F5F5F5" },
  em_andamento: { label: "Em andamento", cor: "#1565C0", bg: "#E3F2FD" },
};

export default function ParcelasPage() {
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

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-6">
      <h1 className="text-xl font-bold text-[#1565C0]">COMPRAS PARCELADAS</h1>

      <div className="flex gap-3">
        <div className="flex-1 rounded-lg bg-[#E8F5E9] p-3 text-center">
          <p className="text-[10px] font-bold text-[#2E7D32]">JÁ PAGO</p>
          <p className="text-base font-bold text-[#2E7D32]">{fmt(resumo.totalPago)}</p>
        </div>
        <div className="flex-1 rounded-lg bg-[#FFEBEE] p-3 text-center">
          <p className="text-[10px] font-bold text-[#C62828]">EM ABERTO</p>
          <p className="text-base font-bold text-[#C62828]">{fmt(resumo.totalEmAberto)}</p>
        </div>
        <div className="flex-1 rounded-lg bg-[#E3F2FD] p-3 text-center">
          <p className="text-[10px] font-bold text-[#1565C0]">TOTAL GERAL</p>
          <p className="text-base font-bold text-[#1565C0]">{fmt(resumo.totalGeral)}</p>
        </div>
      </div>

      {carregando ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin text-[#1565C0]" size={24} />
        </div>
      ) : parcelas.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-gray-400">
          <Layers size={32} />
          <p className="text-sm">Nenhuma compra parcelada encontrada.</p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {parcelas.map((p, i) => {
            const info = STATUS_INFO[p.status];
            const pct = (p.pagas / p.totalParcelas) * 100;
            return (
              <div key={i} className="rounded-xl border border-gray-200 bg-white p-3.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{p.descBase || "(sem descrição)"}</p>
                    <p className="text-xs text-gray-500">{p.conta}</p>
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
                    <div
                      className="h-2 rounded"
                      style={{ width: `${pct}%`, backgroundColor: info.cor }}
                    />
                  </div>
                  <span className="flex-shrink-0 text-xs font-medium text-gray-500">
                    {p.pagas}/{p.totalParcelas}
                  </span>
                </div>

                <div className="mt-2 flex items-center justify-between text-xs">
                  <span className="text-gray-500">
                    {fmt(p.valorParcela)} por parcela · Total {fmt(p.valorTotal)}
                  </span>
                  {p.proximaData && (
                    <span className="font-medium text-[#1565C0]">Próxima: {p.proximaData}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
