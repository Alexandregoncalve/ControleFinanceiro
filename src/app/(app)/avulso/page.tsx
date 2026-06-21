"use client";

import { useState, useMemo } from "react";
import { Save, CalendarDays, Info } from "lucide-react";
import { BuscaSubconta } from "@/components/forms/BuscaSubconta";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { useSubcontas } from "@/hooks/useSubcontas";
import { useBancos } from "@/hooks/useBancos";
import { fmt, formatarDataBR } from "@/lib/utils";

/** Detecta se a subconta é de cartão de crédito (mesma regra de eh_cartao() em avulso.py) */
function ehCartao(nome: string): boolean {
  return /CART[AÃ]O/i.test(nome);
}

export default function AvulsoPage() {
  const { subcontas } = useSubcontas();
  const { bancos } = useBancos();

  const [data, setData] = useState(formatarDataBR(new Date()));
  const [bancoId, setBancoId] = useState<number | "">("");
  const [subcontaSel, setSubcontaSel] = useState<{ id: number; nome: string } | null>(null);
  const [catRealSel, setCatRealSel] = useState<{ id: number; nome: string } | null>(null);
  const [valor, setValor] = useState(0);
  const [descricao, setDescricao] = useState("");
  const [parcelas, setParcelas] = useState(1);
  const [msg, setMsg] = useState<{ texto: string; cor: "red" | "green" } | null>(null);
  const [salvando, setSalvando] = useState(false);

  const ehCartaoSelecionado = subcontaSel ? ehCartao(subcontaSel.nome) : false;

  const infoParcelas = useMemo(() => {
    if (!ehCartaoSelecionado || valor <= 0) return "";
    const parcela = valor / parcelas;
    const [d, m, a] = data.split("/").map(Number);
    const dataBase = new Date(a, m - 1, d, 12);

    if (parcelas === 1) {
      const venc = new Date(dataBase);
      venc.setMonth(venc.getMonth() + 1);
      return `💳 Vence em ${formatarDataBR(venc)}`;
    }

    const primeira = new Date(dataBase);
    primeira.setMonth(primeira.getMonth() + 1);
    const ultima = new Date(dataBase);
    ultima.setMonth(ultima.getMonth() + parcelas);

    return `💳 ${parcelas}x ${fmt(parcela)} — 1ª ${formatarDataBR(primeira)}, última ${formatarDataBR(ultima)}`;
  }, [ehCartaoSelecionado, valor, parcelas, data]);

  function resetarFormulario(manterBancoEData: boolean) {
    setSubcontaSel(null);
    setCatRealSel(null);
    setValor(0);
    setDescricao("");
    setParcelas(1);
    if (!manterBancoEData) {
      setData(formatarDataBR(new Date()));
      setBancoId("");
    }
  }

  async function salvar() {
    setMsg(null);

    if (!subcontaSel) {
      setMsg({ texto: "⚠️ Selecione uma conta.", cor: "red" });
      return;
    }
    if (valor <= 0) {
      setMsg({ texto: "⚠️ Informe um valor.", cor: "red" });
      return;
    }
    if (ehCartaoSelecionado && !catRealSel) {
      setMsg({ texto: "⚠️ Informe a categoria real do gasto no cartão.", cor: "red" });
      return;
    }

    setSalvando(true);
    try {
      const res = await fetch("/api/transacoes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          data,
          valor,
          descricao: descricao.trim(),
          subcontaId: subcontaSel.id,
          bancoId: bancoId || null,
          categoriaRealId: catRealSel?.id ?? null,
          parcelas: ehCartaoSelecionado ? parcelas : 1,
        }),
      });

      if (res.ok) {
        setMsg({ texto: "✅ Salvo! Banco mantido.", cor: "green" });
        resetarFormulario(true);
      } else {
        const err = await res.json();
        setMsg({ texto: `❌ ${err.erro || "Erro ao salvar."}`, cor: "red" });
      }
    } catch {
      setMsg({ texto: "❌ Erro de conexão.", cor: "red" });
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
      <h1 className="text-xl font-bold text-[#1565C0]">LANÇAMENTO AVULSO</h1>

      <div className="flex items-center gap-2 rounded-lg bg-[#E3F2FD] px-3 py-2.5">
        <Info size={16} className="flex-shrink-0 text-[#1565C0]" />
        <p className="text-xs italic text-[#1565C0]">Banco fica selecionado entre lançamentos.</p>
      </div>

      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">Data</span>
          <div className="flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2">
            <CalendarDays size={14} className="text-gray-400" />
            <input
              type="text"
              value={data}
              onChange={(e) => setData(e.target.value)}
              placeholder="DD/MM/AAAA"
              className="w-24 text-sm outline-none"
            />
          </div>
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-xs font-medium text-gray-600">🏦 Banco</span>
          <select
            value={bancoId}
            onChange={(e) => setBancoId(e.target.value ? Number(e.target.value) : "")}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#1565C0]"
          >
            <option value="">— Banco —</option>
            {bancos.map((b) => (
              <option key={b.id} value={b.id}>
                {b.nomeBanco}
              </option>
            ))}
          </select>
        </label>
      </div>

      <BuscaSubconta
        label="🔍 Buscar conta"
        subcontas={subcontas}
        onSelecionar={(s) => {
          setSubcontaSel(s);
          if (!descricao.trim()) setDescricao(s.nome);
          if (!ehCartao(s.nome)) {
            setCatRealSel(null);
            setParcelas(1);
          }
        }}
        className="max-w-md"
      />

      <InputMoeda label="Valor" value={valor} onChange={setValor} className="w-48" />

      {ehCartaoSelecionado && (
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">Parcelas</span>
            <select
              value={parcelas}
              onChange={(e) => setParcelas(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#1565C0]"
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {n}x
                </option>
              ))}
            </select>
          </label>
          {infoParcelas && <p className="pb-2 text-xs italic text-[#1565C0]">{infoParcelas}</p>}
        </div>
      )}

      {ehCartaoSelecionado && (
        <div className="flex flex-col gap-2 rounded-lg bg-[#FFF3E0] p-3">
          <p className="text-xs font-bold text-[#E65100]">💡 Onde foi gasto no cartão?</p>
          <BuscaSubconta
            label="Categoria real do gasto"
            subcontas={subcontas.filter((s) => !ehCartao(s.nome))}
            onSelecionar={setCatRealSel}
            className="max-w-md"
          />
        </div>
      )}

      <label className="flex max-w-md flex-col gap-1">
        <span className="text-xs font-medium text-gray-600">Descrição</span>
        <input
          type="text"
          value={descricao}
          onChange={(e) => setDescricao(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#1565C0] focus:ring-1 focus:ring-[#1565C0]"
        />
      </label>

      {msg && (
        <p className={`text-sm font-medium ${msg.cor === "red" ? "text-red-600" : "text-green-600"}`}>
          {msg.texto}
        </p>
      )}

      <button
        onClick={salvar}
        disabled={salvando}
        className="flex h-11 items-center justify-center gap-2 rounded-lg bg-[#1565C0] font-semibold text-white transition hover:bg-[#1257A8] disabled:opacity-60"
      >
        <Save size={16} />
        SALVAR LANÇAMENTO
      </button>
    </div>
  );
}
