"use client";

import { useState, useEffect, useCallback } from "react";
import { fmt } from "@/lib/utils";
import { LoadingPagina } from "@/components/ui/Loading";

interface ValorMes {
  mes: string;
  valor: number | null;
}

interface ContaComparativo {
  nome: string;
  valores: ValorMes[];
}

/** Gera os últimos N meses no formato MM/AAAA, mais antigo primeiro */
function gerarMesesAtras(qtd: number): string[] {
  const hoje = new Date();
  const lista: string[] = [];
  let m = hoje.getMonth() + 1;
  let a = hoje.getFullYear();
  for (let i = 0; i < qtd; i++) {
    lista.unshift(`${String(m).padStart(2, "0")}/${a}`);
    m -= 1;
    if (m === 0) {
      m = 12;
      a -= 1;
    }
  }
  return lista;
}

function gerarOpcoesMeses(): string[] {
  const hoje = new Date();
  const opcoes: string[] = [];
  let m = hoje.getMonth() + 1;
  let a = hoje.getFullYear();
  for (let i = 0; i < 24; i++) {
    opcoes.push(`${String(m).padStart(2, "0")}/${a}`);
    m -= 1;
    if (m === 0) {
      m = 12;
      a -= 1;
    }
  }
  return opcoes;
}

/** Traduz a seção "📅 Comparativo mensal" de views/dashboard.py */
export function ComparativoMensal() {
  const opcoesMeses = gerarOpcoesMeses();
  const ultimos6 = gerarMesesAtras(6);

  const [inicio, setInicio] = useState(ultimos6[0]);
  const [fim, setFim] = useState(ultimos6[ultimos6.length - 1]);
  const [contas, setContas] = useState<ContaComparativo[]>([]);
  const [meses, setMeses] = useState<string[]>([]);
  const [mensagem, setMensagem] = useState("");
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async (ini: string, fimParam: string) => {
    setCarregando(true);
    try {
      const res = await fetch(
        `/api/dashboard/comparativo?inicio=${encodeURIComponent(ini)}&fim=${encodeURIComponent(fimParam)}`
      );
      if (res.ok) {
        const data = await res.json();
        setContas(data.contas);
        setMeses(data.meses);
        setMensagem(data.mensagem || "");
      }
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar(inicio, fim);
  }, [inicio, fim, carregar]);

  /** Cor da célula: vermelho se aumentou vs mês anterior com dado, verde se diminuiu, azul se não há comparação */
  function corCelula(conta: ContaComparativo, idx: number): string {
    const atual = conta.valores[idx].valor;
    if (atual === null) return "#9CA3AF";
    if (idx === 0) return "#0C447C";
    const anterior = conta.valores[idx - 1].valor;
    if (anterior === null || anterior === 0) return "#0C447C";
    return atual > anterior ? "#A32D2D" : "#3B6D11";
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">De</span>
          <select
            value={inicio}
            onChange={(e) => setInicio(e.target.value)}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs outline-none focus:border-[#0C447C]"
          >
            {opcoesMeses
              .slice()
              .reverse()
              .map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Até</span>
          <select
            value={fim}
            onChange={(e) => setFim(e.target.value)}
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-xs outline-none focus:border-[#0C447C]"
          >
            {opcoesMeses
              .slice()
              .reverse()
              .map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
          </select>
        </label>
        {mensagem && <span className="pb-1.5 text-[11px] italic text-gray-400">{mensagem}</span>}
      </div>

      <div className="flex items-center gap-2 text-[10px] text-gray-500">
        <span className="inline-flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-[#3B6D11]" /> diminuiu
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-[#A32D2D]" /> aumentou em relação ao mês anterior
        </span>
      </div>

      {carregando ? (
        <LoadingPagina />
      ) : contas.length === 0 ? (
        <p className="text-sm italic text-gray-400">Sem dados no período selecionado.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <table className="w-full text-xs">
            <thead className="bg-gray-50">
              <tr>
                <th className="whitespace-nowrap px-3 py-2 text-left font-bold text-gray-600">Conta</th>
                {meses.map((m) => (
                  <th key={m} className="whitespace-nowrap px-3 py-2 text-right font-bold text-gray-600">
                    {m}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contas.map((conta) => (
                <tr key={conta.nome} className="border-t border-gray-100">
                  <td className="whitespace-nowrap px-3 py-2 text-gray-700">{conta.nome}</td>
                  {conta.valores.map((v, idx) => (
                    <td
                      key={v.mes}
                      className="whitespace-nowrap px-3 py-2 text-right font-medium"
                      style={{ color: corCelula(conta, idx) }}
                    >
                      {v.valor === null ? "—" : fmt(v.valor)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
