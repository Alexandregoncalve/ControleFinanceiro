"use client";

import { useState } from "react";
import { Landmark, CreditCard, ArrowLeftRight, Pencil, Trash2, RefreshCw } from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { CartaoBanco } from "@/components/ui/CartaoBanco";
import { CartaoCredito } from "@/components/ui/CartaoCredito";
import { useBancos } from "@/hooks/useBancos";
import { fmt, formatarDataBR } from "@/lib/utils";

interface Cartao {
  id: number;
  nomeCartao: string;
  limite: number;
  bancoId: number | null;
  bancoNome: string | null;
  tipo: string | null;
}

interface Transferencia {
  id: number;
  data: string;
  valor: number;
  bancoOrig: number;
  bancoDest: number;
  bancoOrigNome?: string;
  bancoDestNome?: string;
  descricao: string | null;
}

export default function BancosPage() {
  const { bancos, recarregar: recarregarBancos } = useBancos();
  const [cartoes, setCartoes] = useState<Cartao[]>([]);
  const [transferencias, setTransferencias] = useState<Transferencia[]>([]);

  // ── Formulário Banco ──────────────────────────────────────────────────
  const [editandoBanco, setEditandoBanco] = useState<number | null>(null);
  const [nomeBanco, setNomeBanco] = useState("");
  const [codigoBanco, setCodigoBanco] = useState("");
  const [agencia, setAgencia] = useState("");
  const [conta, setConta] = useState("");
  const [saldoInicial, setSaldoInicial] = useState(0);
  const [dataInicial, setDataInicial] = useState(formatarDataBR(new Date()));
  const [msgBanco, setMsgBanco] = useState("");

  // ── Formulário Cartão ──────────────────────────────────────────────────
  const [editandoCartao, setEditandoCartao] = useState<number | null>(null);
  const [nomeCartao, setNomeCartao] = useState("");
  const [tipoCartao, setTipoCartao] = useState("");
  const [limite, setLimite] = useState(0);
  const [bancoCartaoId, setBancoCartaoId] = useState<number | "">("");
  const [msgCartao, setMsgCartao] = useState("");

  // ── Formulário Transferência ───────────────────────────────────────────
  const [transfOrig, setTransfOrig] = useState<number | "">("");
  const [transfDest, setTransfDest] = useState<number | "">("");
  const [transfValor, setTransfValor] = useState(0);
  const [transfDesc, setTransfDesc] = useState("Transferência entre bancos");
  const [transfData, setTransfData] = useState(formatarDataBR(new Date()));
  const [editandoTransf, setEditandoTransf] = useState<number | null>(null);
  const [msgTransf, setMsgTransf] = useState("");

  async function carregarCartoes() {
    const res = await fetch("/api/cartoes");
    if (res.ok) setCartoes((await res.json()).cartoes);
  }

  async function carregarTransferencias() {
    const res = await fetch("/api/transferencias");
    if (res.ok) setTransferencias((await res.json()).transferencias);
  }

  async function carregarTudo() {
    await Promise.all([recarregarBancos(), carregarCartoes(), carregarTransferencias()]);
  }

  // Carrega na montagem
  useState(() => {
    carregarCartoes();
    carregarTransferencias();
  });

  // ── BANCO ────────────────────────────────────────────────────────────
  function prepararEdicaoBanco(b: (typeof bancos)[number]) {
    setEditandoBanco(b.id);
    setNomeBanco(b.nomeBanco);
    setCodigoBanco(b.codigoBanco || "");
    setAgencia(b.agencia || "");
    setConta(b.numeroConta || "");
    setSaldoInicial(b.saldoInicial);
    setDataInicial(b.dataCriacao || formatarDataBR(new Date()));
  }

  function limparFormBanco() {
    setEditandoBanco(null);
    setNomeBanco("");
    setCodigoBanco("");
    setAgencia("");
    setConta("");
    setSaldoInicial(0);
    setDataInicial(formatarDataBR(new Date()));
  }

  async function salvarBanco() {
    if (!nomeBanco.trim()) {
      setMsgBanco("⚠️ Informe o nome do banco.");
      return;
    }
    const payload = {
      nomeBanco: nomeBanco.trim(),
      codigoBanco: codigoBanco.trim() || null,
      agencia: agencia.trim() || null,
      numeroConta: conta.trim() || null,
      saldoInicial,
      dataCriacao: dataInicial,
    };

    const res = editandoBanco
      ? await fetch(`/api/bancos/${editandoBanco}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      : await fetch("/api/bancos", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

    if (res.ok) {
      setMsgBanco("✅ Banco salvo!");
      limparFormBanco();
      recarregarBancos();
    } else {
      setMsgBanco("❌ Erro ao salvar.");
    }
  }

  async function excluirBanco(id: number) {
    await fetch(`/api/bancos/${id}`, { method: "DELETE" });
    recarregarBancos();
  }

  // ── CARTÃO ───────────────────────────────────────────────────────────
  function prepararEdicaoCartao(c: Cartao) {
    setEditandoCartao(c.id);
    setNomeCartao(c.nomeCartao);
    setTipoCartao(c.tipo || "");
    setLimite(c.limite);
    setBancoCartaoId(c.bancoId || "");
  }

  function limparFormCartao() {
    setEditandoCartao(null);
    setNomeCartao("");
    setTipoCartao("");
    setLimite(0);
    setBancoCartaoId("");
  }

  async function salvarCartao() {
    if (!nomeCartao.trim() || !tipoCartao || !bancoCartaoId) {
      setMsgCartao("⚠️ Preencha todos os campos.");
      return;
    }
    const payload = {
      nomeCartao: nomeCartao.trim(),
      tipo: tipoCartao,
      limite,
      bancoId: Number(bancoCartaoId),
    };

    const res = editandoCartao
      ? await fetch(`/api/cartoes/${editandoCartao}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      : await fetch("/api/cartoes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

    if (res.ok) {
      setMsgCartao("✅ Cartão salvo!");
      limparFormCartao();
      carregarCartoes();
    } else {
      setMsgCartao("❌ Erro ao salvar.");
    }
  }

  async function excluirCartao(id: number) {
    await fetch(`/api/cartoes/${id}`, { method: "DELETE" });
    carregarCartoes();
  }

  // ── TRANSFERÊNCIA ────────────────────────────────────────────────────
  function cancelarEdicaoTransf() {
    setEditandoTransf(null);
    setTransfOrig("");
    setTransfDest("");
    setTransfValor(0);
    setTransfDesc("Transferência entre bancos");
    setTransfData(formatarDataBR(new Date()));
  }

  function prepararEdicaoTransf(t: Transferencia) {
    setEditandoTransf(t.id);
    setTransfOrig(t.bancoOrig);
    setTransfDest(t.bancoDest);
    setTransfValor(t.valor);
    setTransfDesc(t.descricao || "Transferência entre bancos");
    setTransfData(t.data);
  }

  async function realizarTransferencia() {
    setMsgTransf("");
    if (!transfOrig || !transfDest) {
      setMsgTransf("⚠️ Selecione origem e destino.");
      return;
    }
    if (transfOrig === transfDest) {
      setMsgTransf("⚠️ Origem e destino não podem ser iguais.");
      return;
    }
    if (transfValor <= 0) {
      setMsgTransf("⚠️ Informe um valor válido.");
      return;
    }

    const payload = {
      data: transfData,
      valor: transfValor,
      bancoOrig: Number(transfOrig),
      bancoDest: Number(transfDest),
      descricao: transfDesc.trim(),
    };

    const res = editandoTransf
      ? await fetch(`/api/transferencias/${editandoTransf}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      : await fetch("/api/transferencias", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

    if (res.ok) {
      setMsgTransf("✅ Transferência realizada!");
      cancelarEdicaoTransf();
      carregarTudo();
    } else {
      const err = await res.json();
      setMsgTransf(`❌ ${err.erro || "Erro ao transferir."}`);
    }
  }

  async function excluirTransferencia(id: number) {
    await fetch(`/api/transferencias/${id}`, { method: "DELETE" });
    carregarTudo();
  }

  return (
    <div className="flex flex-col gap-5 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Landmark className="text-[#0C447C] dark:text-blue-300" size={26} />
          <h1 className="text-xl font-bold text-[#0C447C] dark:text-blue-300">BANCOS E CARTÕES</h1>
        </div>
        <button
          onClick={carregarTudo}
          className="flex items-center gap-1.5 rounded-lg border border-[#85B7EB] bg-[#E6F1FB] dark:bg-blue-900/40 px-3 py-1.5 text-xs font-medium text-[#0C447C] dark:text-blue-300"
        >
          <RefreshCw size={13} /> Atualizar
        </button>
      </div>

      {/* Formulários lado a lado */}
      <div className="flex flex-col gap-4 lg:flex-row">
        {/* Form Banco */}
        <div className="flex-1 rounded-xl border-2 border-[#85B7EB] bg-[#E6F1FB] dark:bg-blue-900/40 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Landmark size={18} className="text-[#0C447C] dark:text-blue-300" />
            <span className="text-sm font-bold text-[#0C447C] dark:text-blue-300">Cadastrar / Editar Banco</span>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-2.5">
            <CampoSimples label="Nome do Banco" value={nomeBanco} onChange={setNomeBanco} className="w-full sm:w-48" />
            <CampoSimples label="Cód. Banco" value={codigoBanco} onChange={setCodigoBanco} className="w-24" />
            <CampoSimples label="Agência" value={agencia} onChange={setAgencia} className="w-28" />
            <CampoSimples label="Nº Conta" value={conta} onChange={setConta} className="w-28" />
          </div>
          <div className="mt-2.5 flex flex-wrap gap-2.5">
            <InputMoeda label="Saldo Inicial" value={saldoInicial} onChange={setSaldoInicial} className="w-full sm:w-36" />
            <CampoSimples label="Data Inicial" value={dataInicial} onChange={setDataInicial} className="w-32" />
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={salvarBanco}
              className="rounded-lg bg-[#0C447C] px-5 py-2 text-xs font-semibold text-white"
            >
              {editandoBanco ? "ATUALIZAR BANCO" : "SALVAR BANCO"}
            </button>
            {editandoBanco && (
              <button onClick={limparFormBanco} className="text-xs text-gray-500 underline">
                Cancelar
              </button>
            )}
            {msgBanco && <span className="text-xs">{msgBanco}</span>}
          </div>
        </div>

        {/* Form Cartão */}
        <div className="flex-1 rounded-xl border-2 border-[#FAC775] bg-[#FAEEDA] dark:bg-yellow-900/40 p-4">
          <div className="mb-3 flex items-center gap-2">
            <CreditCard size={18} className="text-[#854F0B]" />
            <span className="text-sm font-bold text-[#854F0B]">Cadastrar / Editar Cartão</span>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-2.5">
            <CampoSimples label="Nome do Cartão" value={nomeCartao} onChange={setNomeCartao} className="w-full sm:w-48" />
            <label className="flex w-32 flex-col gap-1">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Tipo</span>
              <select
                value={tipoCartao}
                onChange={(e) => setTipoCartao(e.target.value)}
                className="rounded-lg border border-gray-300 dark:border-white/15 px-2 py-2 text-sm outline-none"
              >
                <option value="">—</option>
                <option value="Crédito">Crédito</option>
                <option value="Débito">Débito</option>
                <option value="Ambos">Ambos</option>
              </select>
            </label>
          </div>
          <div className="mt-2.5 flex flex-wrap gap-2.5">
            <InputMoeda label="Limite" value={limite} onChange={setLimite} className="w-full sm:w-36" />
            <label className="flex w-44 flex-col gap-1">
              <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Banco vinculado</span>
              <select
                value={bancoCartaoId}
                onChange={(e) => setBancoCartaoId(e.target.value ? Number(e.target.value) : "")}
                className="rounded-lg border border-gray-300 dark:border-white/15 px-2 py-2 text-sm outline-none"
              >
                <option value="">—</option>
                {bancos.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.nomeBanco}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={salvarCartao}
              className="rounded-lg bg-[#854F0B] px-5 py-2 text-xs font-semibold text-white"
            >
              {editandoCartao ? "ATUALIZAR CARTÃO" : "SALVAR CARTÃO"}
            </button>
            {editandoCartao && (
              <button onClick={limparFormCartao} className="text-xs text-gray-500 underline">
                Cancelar
              </button>
            )}
            {msgCartao && <span className="text-xs">{msgCartao}</span>}
          </div>
        </div>
      </div>

      {/* Listas lado a lado */}
      <div className="flex flex-col gap-4 lg:flex-row">
        <div className="flex-1 rounded-xl border border-[#85B7EB] bg-[#E6F1FB] dark:bg-blue-900/40 p-3.5">
          <div className="mb-2 flex items-center gap-2">
            <Landmark size={16} className="text-[#0C447C] dark:text-blue-300" />
            <span className="text-sm font-bold text-[#0C447C] dark:text-blue-300">Bancos Cadastrados</span>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-3">
            {bancos.length === 0 ? (
              <p className="text-xs text-gray-500 dark:text-gray-400 dark:text-gray-500">Nenhum banco cadastrado.</p>
            ) : (
              bancos.map((b, i) => (
                <div key={b.id} className="w-full sm:w-[270px]">
                  <CartaoBanco
                    nomeBanco={b.nomeBanco}
                    saldo={b.saldoAtual ?? b.saldoInicial}
                    agencia={b.agencia}
                    numeroConta={b.numeroConta}
                    variante={i % 2 === 0 ? "azul" : "verde"}
                  />
                  <div className="mt-1.5 flex justify-end gap-3 px-1">
                    <button
                      onClick={() => prepararEdicaoBanco(b)}
                      className="flex items-center gap-1 text-[11px] text-[#0C447C] hover:underline"
                    >
                      <Pencil size={12} /> Editar
                    </button>
                    <button
                      onClick={() => excluirBanco(b.id)}
                      className="flex items-center gap-1 text-[11px] text-[#A32D2D] hover:underline"
                    >
                      <Trash2 size={12} /> Excluir
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="flex-1 rounded-xl border border-[#FAC775] bg-[#FAEEDA] dark:bg-yellow-900/40 p-3.5">
          <div className="mb-2 flex items-center gap-2">
            <CreditCard size={16} className="text-[#854F0B]" />
            <span className="text-sm font-bold text-[#854F0B]">Cartões Cadastrados</span>
          </div>
          <div className="flex flex-wrap gap-2 sm:gap-3">
            {cartoes.length === 0 ? (
              <p className="text-xs text-gray-500 dark:text-gray-400 dark:text-gray-500">Nenhum cartão cadastrado.</p>
            ) : (
              cartoes.map((c) => (
                <div key={c.id} className="w-full sm:w-[250px]">
                  <CartaoCredito
                    nomeCartao={c.nomeCartao}
                    nomeBanco={c.bancoNome}
                    titular={c.tipo ?? ""}
                  />
                  <div className="mt-1.5 flex items-center justify-between px-1 text-[11px] text-gray-500 dark:text-gray-400 dark:text-gray-500">
                    <span>Limite: <strong className="text-gray-700 dark:text-gray-200">{fmt(c.limite)}</strong></span>
                    <span>{c.bancoNome || "—"}</span>
                  </div>
                  <div className="mt-1 flex justify-end gap-3 px-1">
                    <button
                      onClick={() => prepararEdicaoCartao(c)}
                      className="flex items-center gap-1 text-[11px] text-[#0C447C] hover:underline"
                    >
                      <Pencil size={12} /> Editar
                    </button>
                    <button
                      onClick={() => excluirCartao(c.id)}
                      className="flex items-center gap-1 text-[11px] text-[#A32D2D] hover:underline"
                    >
                      <Trash2 size={12} /> Excluir
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Transferências */}
      <div className="rounded-xl bg-[#EAF3DE] dark:bg-green-900/40 p-4">
        <div className="mb-3 flex items-center gap-2">
          <ArrowLeftRight size={20} className="text-[#3B6D11] dark:text-green-400" />
          <span className="text-sm font-bold text-[#3B6D11] dark:text-green-400">💸 Transferência entre Bancos</span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <SeletorBanco label="Banco Origem" bancos={bancos} value={transfOrig} onChange={setTransfOrig} />
          <ArrowLeftRight size={18} className="text-[#3B6D11] dark:text-green-400" />
          <SeletorBanco label="Banco Destino" bancos={bancos} value={transfDest} onChange={setTransfDest} />
        </div>

        <div className="mt-2.5 flex flex-wrap gap-2.5">
          <InputMoeda label="Valor" value={transfValor} onChange={setTransfValor} className="w-full sm:w-36" />
          <CampoSimples label="Data" value={transfData} onChange={setTransfData} className="w-32" />
          <CampoSimples label="Descrição" value={transfDesc} onChange={setTransfDesc} className="w-full sm:w-64" />
        </div>

        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={realizarTransferencia}
            className="h-11 rounded-lg bg-[#3B6D11] px-6 text-sm font-semibold text-white"
          >
            💸 {editandoTransf ? "SALVAR EDIÇÃO" : "TRANSFERIR"}
          </button>
          {editandoTransf && (
            <button onClick={cancelarEdicaoTransf} className="text-xs text-red-500 underline">
              ✖ Cancelar edição
            </button>
          )}
        </div>
        {msgTransf && <p className="mt-2 text-xs font-medium">{msgTransf}</p>}

        <hr className="my-3 border-[#97C459]" />
        <p className="mb-2 text-xs font-bold text-[#3B6D11] dark:text-green-400">Últimas transferências:</p>
        <div className="flex max-h-56 flex-col gap-1.5 overflow-y-auto">
          {transferencias.length === 0 ? (
            <p className="text-xs italic text-gray-500 dark:text-gray-400 dark:text-gray-500">Nenhuma transferência realizada.</p>
          ) : (
            transferencias.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between gap-2 rounded-lg border border-[#C0DD97] bg-white dark:bg-[#1E293B] p-2.5"
              >
                <div className="flex-1">
                  <p className="text-[10px] text-gray-400 dark:text-gray-500">{t.data}</p>
                  <p className="text-xs text-gray-700 dark:text-gray-200">{t.descricao || "Transferência"}</p>
                </div>
                <div className="flex items-center gap-1.5 text-xs">
                  <span className="text-[#A32D2D]">{t.bancoOrigNome}</span>
                  <ArrowLeftRight size={12} className="text-gray-400 dark:text-gray-500" />
                  <span className="text-[#3B6D11] dark:text-green-400">{t.bancoDestNome}</span>
                </div>
                <span className="w-24 text-right text-sm font-bold text-[#0C447C] dark:text-blue-300">{fmt(t.valor)}</span>
                <div className="flex gap-1.5">
                  <button onClick={() => prepararEdicaoTransf(t)}>
                    <Pencil size={14} className="text-[#0C447C] dark:text-blue-300" />
                  </button>
                  <button onClick={() => excluirTransferencia(t.id)}>
                    <Trash2 size={14} className="text-red-500" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function CampoSimples({
  label,
  value,
  onChange,
  className = "",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
      />
    </label>
  );
}

function SeletorBanco({
  label,
  bancos,
  value,
  onChange,
}: {
  label: string;
  bancos: { id: number; nomeBanco: string }[];
  value: number | "";
  onChange: (v: number | "") => void;
}) {
  return (
    <label className="flex w-48 flex-col gap-1">
      <span className="text-xs font-medium text-gray-600 dark:text-gray-300">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : "")}
        className="rounded-lg border border-gray-300 dark:border-white/15 px-3 py-2 text-sm outline-none focus:border-[#3B6D11]"
      >
        <option value="">— Selecione —</option>
        {bancos.map((b) => (
          <option key={b.id} value={b.id}>
            {b.nomeBanco}
          </option>
        ))}
      </select>
    </label>
  );
}
