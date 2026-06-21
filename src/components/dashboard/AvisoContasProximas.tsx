"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AlertCircle, X, ArrowRight } from "lucide-react";
import { fmt } from "@/lib/utils";

interface ContaProxima {
  id: number;
  nome: string;
  diaVencimento: number | null;
  orcamento: number | null;
}

/**
 * Modal exibido uma vez por sessão de login, avisando sobre contas fixas
 * vencendo nos próximos dias que ainda não foram lançadas no mês.
 * Oferece ir direto para Contas Fixas ou dispensar o aviso.
 */
export function AvisoContasProximas() {
  const router = useRouter();
  const [contas, setContas] = useState<ContaProxima[]>([]);
  const [aberto, setAberto] = useState(false);

  useEffect(() => {
    // Evita mostrar de novo se o usuário já dispensou nesta mesma aba/sessão
    const jaExibido = sessionStorage.getItem("aviso_contas_proximas_exibido");
    if (jaExibido) return;

    fetch("/api/fixas/proximas?dias=1")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.proximas?.length > 0) {
          setContas(data.proximas);
          setAberto(true);
        }
        sessionStorage.setItem("aviso_contas_proximas_exibido", "1");
      })
      .catch(() => {});
  }, []);

  if (!aberto) return null;

  const total = contas.reduce((acc, c) => acc + (c.orcamento ?? 0), 0);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle size={20} className="text-[#F57F17]" />
            <h2 className="text-sm font-bold text-gray-800">Contas vencendo em breve</h2>
          </div>
          <button onClick={() => setAberto(false)} className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>

        <div className="max-h-72 overflow-y-auto p-4">
          <p className="mb-3 text-xs text-gray-500">
            {contas.length === 1
              ? "Você tem 1 conta fixa vencendo amanhã que ainda não foi lançada:"
              : `Você tem ${contas.length} contas fixas vencendo amanhã que ainda não foram lançadas:`}
          </p>
          <div className="flex flex-col gap-2">
            {contas.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-lg bg-[#FFF8E1] px-3 py-2"
              >
                <span className="text-xs font-medium text-gray-700">{c.nome}</span>
                <div className="flex items-center gap-2">
                  {c.diaVencimento && (
                    <span className="text-[10px] font-bold text-[#F57F17]">Dia {c.diaVencimento}</span>
                  )}
                  {c.orcamento ? (
                    <span className="text-xs font-bold text-gray-600">{fmt(c.orcamento)}</span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
          {total > 0 && (
            <div className="mt-3 flex items-center justify-between border-t border-gray-100 pt-3">
              <span className="text-xs text-gray-500">Total estimado</span>
              <span className="text-sm font-bold text-[#1565C0]">{fmt(total)}</span>
            </div>
          )}
        </div>

        <div className="flex gap-2 border-t border-gray-100 p-4">
          <button
            onClick={() => setAberto(false)}
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-xs font-medium text-gray-600"
          >
            Agora não
          </button>
          <button
            onClick={() => {
              setAberto(false);
              router.push("/fixas");
            }}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#1565C0] px-4 py-2.5 text-xs font-semibold text-white"
          >
            Ir pagar agora <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
