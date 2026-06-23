"use client";

import { useState, useEffect, useCallback } from "react";
import { CheckSquare, Square, Loader2 } from "lucide-react";
import { SeletorMes } from "@/components/ui/SeletorMes";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { useBancos } from "@/hooks/useBancos";
import { fmt, mesAtual, formatarDataBR } from "@/lib/utils";

interface FixaPendente {
  id: number;
  nome: string;
  orcamento: number;
  diaVencimento: number | null;
}

interface ItemSelecionado {
  subcontaId: number;
  nome: string;
  valor: number;
  selecionado: boolean;
}

export default function FixasPage() {
  const { bancos } = useBancos();
  const [mes, setMes] = useState(mesAtual());
  const [pendentes, setPendentes] = useState<FixaPendente[]>([]);
  const [resumo, setResumo] = useState({ total: 0, lancadas: 0 });
  const [itens, setItens] = useState<ItemSelecionado[]>([]);
  const [bancoId, setBancoId] = useState<number | "">("");
  const [carregando, setCarregando] = useState(true);
  const [salvando, setSalvando] = useState(false);
  const [msg, setMsg] = useState<{ texto: string; cor: "red" | "green" } | null>(null);

  const carregar = useCallback(async (mesParam: string) => {
    setCarregando(true);
    try {
      const res = await fetch(`/api/fixas?mes=${encodeURIComponent(mesParam)}`);
      if (res.ok) {
        const data = await res.json();
        setPendentes(data.pendentes);
        setResumo({ total: data.total, lancadas: data.lancadas });
        setItens(
          data.pendentes.map((p: FixaPendente) => ({
            subcontaId: p.id,
            nome: p.nome,
            valor: p.orcamento || 0,
            selecionado: true,
          }))
        );
      }
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar(mes);
  }, [mes, carregar]);

  function toggleItem(id: number) {
    setItens((prev) => prev.map((i) => (i.subcontaId === id ? { ...i, selecionado: !i.selecionado } : i)));
  }

  function atualizarValor(id: number, valor: number) {
    setItens((prev) => prev.map((i) => (i.subcontaId === id ? { ...i, valor } : i)));
  }

  const selecionados = itens.filter((i) => i.selecionado);
  const totalSelecionado = selecionados.reduce((acc, i) => acc + i.valor, 0);

  async function baixarSelecionados() {
    setMsg(null);
    if (selecionados.length === 0) {
      setMsg({ texto: "⚠️ Selecione ao menos uma conta.", cor: "red" });
      return;
    }
    if (selecionados.some((i) => i.valor <= 0)) {
      setMsg({ texto: "⚠️ Todas as contas selecionadas precisam ter um valor.", cor: "red" });
      return;
    }

    setSalvando(true);
    try {
      const hoje = formatarDataBR(new Date());
      const res = await fetch("/api/fixas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          itens: selecionados.map((i) => ({
            subcontaId: i.subcontaId,
            valor: i.valor,
            descricao: i.nome,
            data: hoje,
          })),
          bancoId: bancoId || null,
        }),
      });

      if (res.ok) {
        setMsg({ texto: `✅ ${selecionados.length} conta(s) lançada(s)!`, cor: "green" });
        carregar(mes);
      } else {
        setMsg({ texto: "❌ Erro ao lançar contas.", cor: "red" });
      }
    } catch {
      setMsg({ texto: "❌ Erro de conexão.", cor: "red" });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 p-4 sm:p-6">
      <div className="flex items-end justify-between">
        <h1 className="text-xl font-bold text-[#0C447C] dark:text-blue-300">CONTAS FIXAS</h1>
        <SeletorMes mes={mes} onChange={setMes} />
      </div>

      <div className="flex gap-3">
        <div className="flex-1 rounded-lg bg-[#E6F1FB] dark:bg-blue-900/40 p-3 text-center">
          <p className="text-[10px] font-bold text-[#0C447C] dark:text-blue-300">TOTAL DE FIXAS</p>
          <p className="text-lg font-bold text-[#0C447C] dark:text-blue-300">{resumo.total}</p>
        </div>
        <div className="flex-1 rounded-lg bg-[#EAF3DE] dark:bg-green-900/40 p-3 text-center">
          <p className="text-[10px] font-bold text-[#3B6D11] dark:text-green-400">JÁ LANÇADAS</p>
          <p className="text-lg font-bold text-[#3B6D11] dark:text-green-400">{resumo.lancadas}</p>
        </div>
        <div className="flex-1 rounded-lg bg-[#FCEBEB] dark:bg-red-900/40 p-3 text-center">
          <p className="text-[10px] font-bold text-[#A32D2D]">PENDENTES</p>
          <p className="text-lg font-bold text-[#A32D2D]">{pendentes.length}</p>
        </div>
      </div>

      {carregando ? (
        <div className="flex justify-center py-8">
          <Loader2 className="animate-spin text-[#0C447C] dark:text-blue-300" size={24} />
        </div>
      ) : pendentes.length === 0 ? (
        <div className="rounded-lg bg-[#EAF3DE] dark:bg-green-900/40 p-6 text-center">
          <p className="text-sm font-medium text-[#3B6D11] dark:text-green-400">✅ Todas as contas fixas já foram lançadas neste mês!</p>
        </div>
      ) : (
        <>
          <label className="flex w-56 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">🏦 Banco para baixa</span>
            <select
              value={bancoId}
              onChange={(e) => setBancoId(e.target.value ? Number(e.target.value) : "")}
              className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
            >
              <option value="">— Selecione —</option>
              {bancos.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.nomeBanco}
                </option>
              ))}
            </select>
          </label>

          <div className="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white dark:bg-[#1E293B] p-3">
            {itens.map((item) => (
              <div
                key={item.subcontaId}
                className="flex items-center gap-3 border-b border-gray-100 dark:border-white/10 py-2 last:border-0"
              >
                <button onClick={() => toggleItem(item.subcontaId)} className="flex-shrink-0">
                  {item.selecionado ? (
                    <CheckSquare size={18} className="text-[#0C447C] dark:text-blue-300" />
                  ) : (
                    <Square size={18} className="text-gray-300" />
                  )}
                </button>
                <span className="flex-1 text-sm text-gray-700 dark:text-gray-200">{item.nome}</span>
                <InputMoeda
                  label=""
                  value={item.valor}
                  onChange={(v) => atualizarValor(item.subcontaId, v)}
                  className="w-32"
                />
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between rounded-lg bg-[#F4F7FB] dark:bg-[#0F172A] p-3">
            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
              {selecionados.length} conta(s) selecionada(s)
            </span>
            <span className="text-lg font-bold text-[#0C447C] dark:text-blue-300">{fmt(totalSelecionado)}</span>
          </div>

          {msg && (
            <p className={`text-sm font-medium ${msg.cor === "red" ? "text-red-600" : "text-green-600"}`}>
              {msg.texto}
            </p>
          )}

          <button
            onClick={baixarSelecionados}
            disabled={salvando || selecionados.length === 0}
            className="h-11 rounded-lg bg-[#0C447C] font-semibold text-white transition hover:bg-[#042C53] disabled:opacity-60"
          >
            {salvando ? "Lançando..." : `LANÇAR ${selecionados.length} CONTA(S)`}
          </button>
        </>
      )}
    </div>
  );
}
