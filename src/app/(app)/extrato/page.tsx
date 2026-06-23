"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, Pencil, Trash2, Loader2, List } from "lucide-react";
import { SeletorMes } from "@/components/ui/SeletorMes";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { useSubcontas } from "@/hooks/useSubcontas";
import { useBancos } from "@/hooks/useBancos";
import { fmt, mesAtual } from "@/lib/utils";

interface Transacao {
  id: number;
  data: string;
  valor: number;
  descricao: string | null;
  subcontaId: number;
  subcontaNome: string;
  tipo: "Receita" | "Despesa";
  parcelaAtual: number;
  totalParcelas: number;
  categoriaRealNome: string | null;
  bancoId: number | null;
  bancoNome: string | null;
}

export default function ExtratoPage() {
  const { subcontas } = useSubcontas();
  const { bancos } = useBancos();

  const [mes, setMes] = useState(mesAtual());
  const [tipo, setTipo] = useState<"" | "Receita" | "Despesa">("");
  const [busca, setBusca] = useState("");
  const [transacoes, setTransacoes] = useState<Transacao[]>([]);
  const [carregando, setCarregando] = useState(true);

  const [editando, setEditando] = useState<Transacao | null>(null);
  const [editValor, setEditValor] = useState(0);
  const [editData, setEditData] = useState("");
  const [editDescricao, setEditDescricao] = useState("");
  const [editSubcontaId, setEditSubcontaId] = useState<number | "">("");
  const [editBancoId, setEditBancoId] = useState<number | "">("");

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const params = new URLSearchParams({ mes });
      if (tipo) params.set("tipo", tipo);
      if (busca.trim()) params.set("busca", busca.trim());

      const res = await fetch(`/api/transacoes?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setTransacoes(data.transacoes);
      }
    } finally {
      setCarregando(false);
    }
  }, [mes, tipo, busca]);

  useEffect(() => {
    const timer = setTimeout(carregar, 300); // debounce na busca
    return () => clearTimeout(timer);
  }, [carregar]);

  function iniciarEdicao(t: Transacao) {
    setEditando(t);
    setEditValor(t.valor);
    setEditData(t.data);
    setEditDescricao(t.descricao || "");
    setEditSubcontaId(t.subcontaId);
    setEditBancoId(t.bancoId || "");
  }

  async function salvarEdicao() {
    if (!editando) return;
    const res = await fetch(`/api/transacoes/${editando.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        data: editData,
        valor: editValor,
        descricao: editDescricao.trim(),
        subcontaId: Number(editSubcontaId),
        bancoId: editBancoId || null,
      }),
    });
    if (res.ok) {
      setEditando(null);
      carregar();
    }
  }

  async function excluir(id: number) {
    if (!confirm("Excluir esta transação?")) return;
    await fetch(`/api/transacoes/${id}`, { method: "DELETE" });
    carregar();
  }

  const totalReceitas = transacoes.filter((t) => t.tipo === "Receita").reduce((a, t) => a + t.valor, 0);
  const totalDespesas = transacoes.filter((t) => t.tipo === "Despesa").reduce((a, t) => a + t.valor, 0);

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6">
      <div className="flex items-end justify-between">
        <div className="flex items-center gap-2">
          <List className="text-[#0C447C] dark:text-blue-300" size={24} />
          <h1 className="text-xl font-bold text-[#0C447C] dark:text-blue-300">EXTRATO</h1>
        </div>
        <SeletorMes mes={mes} onChange={setMes} />
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por descrição..."
            className="w-full rounded-lg border border-gray-300 dark:border-white/15 py-2 pl-8 pr-3 text-sm outline-none focus:border-[#0C447C]"
          />
        </div>
        <select
          value={tipo}
          onChange={(e) => setTipo(e.target.value as "" | "Receita" | "Despesa")}
          className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
        >
          <option value="">Todos os tipos</option>
          <option value="Receita">Receitas</option>
          <option value="Despesa">Despesas</option>
        </select>
      </div>

      <div className="flex gap-3">
        <div className="flex-1 rounded-lg bg-[#EAF3DE] dark:bg-green-900/40 p-3 text-center">
          <p className="text-[10px] font-bold text-[#3B6D11] dark:text-green-400">RECEITAS</p>
          <p className="text-base font-bold text-[#3B6D11] dark:text-green-400">{fmt(totalReceitas)}</p>
        </div>
        <div className="flex-1 rounded-lg bg-[#FCEBEB] dark:bg-red-900/40 p-3 text-center">
          <p className="text-[10px] font-bold text-[#A32D2D]">DESPESAS</p>
          <p className="text-base font-bold text-[#A32D2D]">{fmt(totalDespesas)}</p>
        </div>
        <div className="flex-1 rounded-lg bg-[#E6F1FB] dark:bg-blue-900/40 p-3 text-center">
          <p className="text-[10px] font-bold text-[#0C447C] dark:text-blue-300">SALDO</p>
          <p className="text-base font-bold text-[#0C447C] dark:text-blue-300">{fmt(totalReceitas - totalDespesas)}</p>
        </div>
      </div>

      {carregando ? (
        <div className="flex justify-center py-10">
          <Loader2 className="animate-spin text-[#0C447C] dark:text-blue-300" size={24} />
        </div>
      ) : transacoes.length === 0 ? (
        <p className="py-8 text-center text-sm italic text-gray-400 dark:text-gray-500">Nenhuma transação encontrada.</p>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white dark:border-white/10 dark:bg-[#1E293B]">
          {/* Tabela — só visível em telas médias ou maiores */}
          <table className="hidden w-full text-xs sm:table">
            <thead className="bg-gray-50 text-gray-500 dark:bg-[#0F172A] dark:text-gray-400">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Data</th>
                <th className="px-3 py-2 text-left font-medium">Descrição</th>
                <th className="px-3 py-2 text-left font-medium">Conta</th>
                <th className="px-3 py-2 text-left font-medium">Banco</th>
                <th className="px-3 py-2 text-right font-medium">Valor</th>
                <th className="px-3 py-2 text-center font-medium">Ações</th>
              </tr>
            </thead>
            <tbody>
              {transacoes.map((t) => (
                <tr key={t.id} className="border-t border-gray-100 dark:border-white/10">
                  <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{t.data}</td>
                  <td className="px-3 py-2 text-gray-700 dark:text-gray-200">
                    {t.descricao || "—"}
                    {t.totalParcelas > 1 && (
                      <span className="ml-1.5 rounded bg-[#E6F1FB] px-1.5 py-0.5 text-[9px] font-bold text-[#0C447C] dark:bg-blue-900/40 dark:text-blue-300">
                        {t.parcelaAtual}/{t.totalParcelas}x
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{t.subcontaNome}</td>
                  <td className="px-3 py-2 text-gray-500 dark:text-gray-400">{t.bancoNome || "—"}</td>
                  <td className={`px-3 py-2 text-right font-bold ${t.tipo === "Receita" ? "text-[#3B6D11] dark:text-green-400" : "text-[#A32D2D]"}`}>
                    {t.tipo === "Despesa" && "-"}{fmt(t.valor)}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex justify-center gap-2">
                      <button onClick={() => iniciarEdicao(t)}><Pencil size={13} className="text-[#0C447C] dark:text-blue-300" /></button>
                      <button onClick={() => excluir(t.id)}><Trash2 size={13} className="text-red-500" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Cards empilhados — só visíveis em mobile */}
          <div className="flex flex-col divide-y divide-gray-100 sm:hidden dark:divide-white/10">
            {transacoes.map((t) => (
              <div key={t.id} className="flex items-start justify-between gap-2 p-3">
                <div className="flex flex-col gap-0.5 flex-1 min-w-0">
                  <span className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">
                    {t.descricao || "—"}
                    {t.totalParcelas > 1 && (
                      <span className="ml-1.5 rounded bg-[#E6F1FB] px-1.5 py-0.5 text-[9px] font-bold text-[#0C447C] dark:bg-blue-900/40 dark:text-blue-300">
                        {t.parcelaAtual}/{t.totalParcelas}x
                      </span>
                    )}
                  </span>
                  <span className="text-[10px] text-gray-500 dark:text-gray-400">
                    {t.subcontaNome} · {t.bancoNome || "—"} · {t.data}
                  </span>
                </div>
                <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                  <span className={`text-sm font-bold ${t.tipo === "Receita" ? "text-[#3B6D11] dark:text-green-400" : "text-[#A32D2D]"}`}>
                    {t.tipo === "Despesa" && "-"}{fmt(t.valor)}
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => iniciarEdicao(t)}><Pencil size={13} className="text-[#0C447C] dark:text-blue-300" /></button>
                    <button onClick={() => excluir(t.id)}><Trash2 size={13} className="text-red-500" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal de edição simples */}
      {editando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-5">
            <p className="mb-3 text-sm font-bold text-[#0C447C] dark:text-blue-300">Editar transação</p>
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Data</span>
                <input
                  type="text"
                  value={editData}
                  onChange={(e) => setEditData(e.target.value)}
                  className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none"
                />
              </label>
              <InputMoeda label="Valor" value={editValor} onChange={setEditValor} />
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Descrição</span>
                <input
                  type="text"
                  value={editDescricao}
                  onChange={(e) => setEditDescricao(e.target.value)}
                  className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Conta</span>
                <select
                  value={editSubcontaId}
                  onChange={(e) => setEditSubcontaId(e.target.value ? Number(e.target.value) : "")}
                  className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none"
                >
                  {subcontas.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nome}
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Banco</span>
                <select
                  value={editBancoId}
                  onChange={(e) => setEditBancoId(e.target.value ? Number(e.target.value) : "")}
                  className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none"
                >
                  <option value="">— Sem banco —</option>
                  {bancos.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.nomeBanco}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setEditando(null)}
                className="rounded-lg border border-gray-300 dark:border-white/15 px-4 py-2 text-xs font-medium text-gray-600 dark:text-gray-300"
              >
                Cancelar
              </button>
              <button
                onClick={salvarEdicao}
                className="rounded-lg bg-[#0C447C] px-4 py-2 text-xs font-semibold text-white"
              >
                Salvar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
