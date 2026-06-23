"use client";

import { useState, useEffect } from "react";
import { Wallet, Pencil, Trash2, Plus } from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";

interface Categoria {
  id: number;
  nome: string;
  tipo: "Receita" | "Despesa";
}

interface Subconta {
  id: number;
  categoriaId: number;
  nome: string;
  fixa: number;
  orcamento: number;
  diaVencimento: number | null;
  categoriaNome?: string;
  categoriaTipo?: "Receita" | "Despesa";
}

export default function ContasPage() {
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [subcontas, setSubcontas] = useState<Subconta[]>([]);

  // Form categoria
  const [nomeCategoria, setNomeCategoria] = useState("");
  const [tipoCategoria, setTipoCategoria] = useState<"Receita" | "Despesa">("Despesa");
  const [msgCategoria, setMsgCategoria] = useState("");

  // Form subconta
  const [editandoSubconta, setEditandoSubconta] = useState<number | null>(null);
  const [categoriaIdSel, setCategoriaIdSel] = useState<number | "">("");
  const [nomeSubconta, setNomeSubconta] = useState("");
  const [fixa, setFixa] = useState(false);
  const [orcamento, setOrcamento] = useState(0);
  const [diaVenc, setDiaVenc] = useState<number | "">("");
  const [msgSubconta, setMsgSubconta] = useState("");

  async function carregarCategorias() {
    const res = await fetch("/api/categorias");
    if (res.ok) setCategorias((await res.json()).categorias);
  }

  async function carregarSubcontas() {
    const res = await fetch("/api/subcontas");
    if (res.ok) setSubcontas((await res.json()).subcontas);
  }

  useEffect(() => {
    carregarCategorias();
    carregarSubcontas();
  }, []);

  async function salvarCategoria() {
    if (!nomeCategoria.trim()) {
      setMsgCategoria("⚠️ Informe o nome.");
      return;
    }
    const res = await fetch("/api/categorias", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nome: nomeCategoria.trim(), tipo: tipoCategoria }),
    });
    if (res.ok) {
      setMsgCategoria("✅ Conta pai criada!");
      setNomeCategoria("");
      carregarCategorias();
    } else {
      setMsgCategoria("❌ Erro ao salvar.");
    }
  }

  function limparFormSubconta() {
    setEditandoSubconta(null);
    setCategoriaIdSel("");
    setNomeSubconta("");
    setFixa(false);
    setOrcamento(0);
    setDiaVenc("");
  }

  function prepararEdicaoSubconta(s: Subconta) {
    setEditandoSubconta(s.id);
    setCategoriaIdSel(s.categoriaId);
    setNomeSubconta(s.nome);
    setFixa(s.fixa === 1);
    setOrcamento(s.orcamento);
    setDiaVenc(s.diaVencimento ?? "");
  }

  async function salvarSubconta() {
    if (!categoriaIdSel) {
      setMsgSubconta("⚠️ Selecione a conta pai.");
      return;
    }
    if (!nomeSubconta.trim()) {
      setMsgSubconta("⚠️ Preencha o nome da subconta.");
      return;
    }

    const payload = {
      categoriaId: Number(categoriaIdSel),
      nome: nomeSubconta.trim(),
      fixa,
      orcamento,
      diaVencimento: diaVenc === "" ? null : Number(diaVenc),
    };

    const res = editandoSubconta
      ? await fetch(`/api/subcontas/${editandoSubconta}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      : await fetch("/api/subcontas", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

    if (res.ok) {
      setMsgSubconta("✅ Subconta salva!");
      limparFormSubconta();
      carregarSubcontas();
    } else {
      setMsgSubconta("❌ Erro ao salvar subconta.");
    }
  }

  async function excluirSubconta(id: number) {
    if (!confirm("Excluir esta subconta? Lançamentos vinculados a ela podem ser afetados.")) return;
    await fetch(`/api/subcontas/${id}`, { method: "DELETE" });
    carregarSubcontas();
  }

  const subcontasPorCategoria = categorias.map((c) => ({
    categoria: c,
    itens: subcontas.filter((s) => s.categoriaId === c.id),
  }));

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5 p-4 sm:p-6">
      <div className="flex items-center gap-2">
        <Wallet className="text-[#0C447C] dark:text-blue-300" size={26} />
        <h1 className="text-xl font-bold text-[#0C447C] dark:text-blue-300">CADASTRO DE CONTAS</h1>
      </div>

      {/* Conta pai (categoria) */}
      <div className="rounded-xl border-2 border-[#85B7EB] bg-[#E6F1FB] dark:bg-blue-900/40 p-4">
        <p className="mb-3 text-sm font-bold text-[#0C447C] dark:text-blue-300">Nova conta pai (categoria)</p>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex w-56 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Nome</span>
            <input
              type="text"
              value={nomeCategoria}
              onChange={(e) => setNomeCategoria(e.target.value)}
              className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
            />
          </label>
          <label className="flex w-36 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Tipo</span>
            <select
              value={tipoCategoria}
              onChange={(e) => setTipoCategoria(e.target.value as "Receita" | "Despesa")}
              className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#0C447C]"
            >
              <option value="Receita">Receita</option>
              <option value="Despesa">Despesa</option>
            </select>
          </label>
          <button
            onClick={salvarCategoria}
            className="flex h-10 items-center gap-1.5 rounded-lg bg-[#0C447C] px-4 text-xs font-semibold text-white"
          >
            <Plus size={14} /> Criar
          </button>
          {msgCategoria && <span className="text-xs">{msgCategoria}</span>}
        </div>
      </div>

      {/* Subconta */}
      <div className="rounded-xl border-2 border-[#97C459] bg-[#EAF3DE] dark:bg-green-900/40 p-4">
        <p className="mb-3 text-sm font-bold text-[#3B6D11] dark:text-green-400">
          {editandoSubconta ? "Editar subconta" : "Nova subconta"}
        </p>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <label className="flex w-56 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Conta pai</span>
            <select
              value={categoriaIdSel}
              onChange={(e) => setCategoriaIdSel(e.target.value ? Number(e.target.value) : "")}
              className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#3B6D11]"
            >
              <option value="">— Selecione —</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome} ({c.tipo})
                </option>
              ))}
            </select>
          </label>
          <label className="flex w-56 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Nome da subconta</span>
            <input
              type="text"
              value={nomeSubconta}
              onChange={(e) => setNomeSubconta(e.target.value)}
              className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#3B6D11]"
            />
          </label>
        </div>
        <div className="mt-2.5 flex flex-wrap items-end gap-3">
          <InputMoeda label="Orçamento mensal (opcional)" value={orcamento} onChange={setOrcamento} className="w-full sm:w-48" />
          <label className="flex w-32 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Dia vencimento</span>
            <input
              type="number"
              min={1}
              max={31}
              placeholder="1 a 31"
              value={diaVenc}
              onChange={(e) => {
                const v = e.target.value;
                if (v === "") {
                  setDiaVenc("");
                  return;
                }
                const n = Number(v);
                if (Number.isInteger(n) && n >= 1 && n <= 31) {
                  setDiaVenc(n);
                }
                // valores fora de 1-31 (ou com mais dígitos) são ignorados silenciosamente,
                // o campo simplesmente não atualiza além do último valor válido
              }}
              className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#3B6D11]"
            />
          </label>
          <label className="flex items-center gap-2 pb-2">
            <input type="checkbox" checked={fixa} onChange={(e) => setFixa(e.target.checked)} className="h-4 w-4" />
            <span className="text-xs text-gray-600 dark:text-gray-300">É uma conta fixa (recorrente todo mês)</span>
          </label>
        </div>
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={salvarSubconta}
            className="h-10 rounded-lg bg-[#3B6D11] px-5 text-xs font-semibold text-white"
          >
            {editandoSubconta ? "ATUALIZAR SUBCONTA" : "SALVAR SUBCONTA"}
          </button>
          {editandoSubconta && (
            <button onClick={limparFormSubconta} className="text-xs text-gray-500 underline">
              Cancelar
            </button>
          )}
          {msgSubconta && <span className="text-xs">{msgSubconta}</span>}
        </div>
      </div>

      {/* Listagem agrupada por categoria */}
      <div className="flex flex-col gap-3">
        {subcontasPorCategoria.map(({ categoria, itens }) => (
          <div key={categoria.id} className="rounded-xl border border-gray-200 bg-white dark:bg-[#1E293B] p-3.5">
            <div className="mb-2 flex items-center gap-2 border-b border-gray-100 dark:border-white/10 pb-2">
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-bold ${
                  categoria.tipo === "Receita" ? "bg-[#EAF3DE] dark:bg-green-900/40 text-[#3B6D11] dark:text-green-400" : "bg-[#FCEBEB] dark:bg-red-900/40 text-[#A32D2D]"
                }`}
              >
                {categoria.tipo}
              </span>
              <span className="text-sm font-bold text-gray-700 dark:text-gray-200">{categoria.nome}</span>
            </div>
            {itens.length === 0 ? (
              <p className="text-xs italic text-gray-400 dark:text-gray-500">Nenhuma subconta cadastrada.</p>
            ) : (
              <div className="flex flex-col">
                {itens.map((s) => (
                  <div
                    key={s.id}
                    className="flex items-center gap-2 border-b border-gray-50 py-1.5 text-xs last:border-0"
                  >
                    <span className="flex-1 text-gray-700 dark:text-gray-200">{s.nome}</span>
                    {s.fixa === 1 && (
                      <span className="rounded bg-[#E6F1FB] dark:bg-blue-900/40 px-1.5 py-0.5 text-[9px] font-bold text-[#0C447C] dark:text-blue-300">
                        FIXA
                      </span>
                    )}
                    {s.diaVencimento && (
                      <span className="rounded bg-[#FAEEDA] dark:bg-yellow-900/40 px-1.5 py-0.5 text-[9px] font-bold text-[#854F0B]">
                        Dia {s.diaVencimento}
                      </span>
                    )}
                    {s.orcamento > 0 && (
                      <span className="text-[10px] text-gray-400 dark:text-gray-500">
                        orç. R$ {s.orcamento.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}
                      </span>
                    )}
                    <button onClick={() => prepararEdicaoSubconta(s)}>
                      <Pencil size={13} className="text-[#0C447C] dark:text-blue-300" />
                    </button>
                    <button onClick={() => excluirSubconta(s.id)}>
                      <Trash2 size={13} className="text-red-500" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
