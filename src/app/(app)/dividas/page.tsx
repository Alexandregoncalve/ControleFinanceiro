"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle,
  Plus,
  Save,
  ChevronDown,
  ChevronUp,
  Trash2,
  CheckCheck,
  Receipt,
  Info,
} from "lucide-react";
import { InputMoeda } from "@/components/ui/InputMoeda";
import { fmt, formatarDataBR, parseDataBR } from "@/lib/utils";

interface Pagamento {
  id: number;
  valor: number;
  data: string;
  observacao: string | null;
}

interface Divida {
  id: number;
  nome: string;
  tipoControle: "parcelada" | "livre";
  valorTotal: number;
  valorParcela: number | null;
  totalParcelas: number | null;
  diaVencimento: number | null;
  dataInicio: string | null;
  taxaJuros: number | null;
  status: "ativa" | "quitada";
  totalPago: number;
  saldo: number;
  pagamentos: Pagamento[];
}

function statusBadge(d: Divida, hoje: Date) {
  if (d.status === "quitada" || d.saldo <= 0) {
    return { cor: "#639922", label: "Quitada" };
  }
  const datasPag = d.pagamentos.map((p) => parseDataBR(p.data));
  const ultima = datasPag.length > 0 ? new Date(Math.max(...datasPag.map((dt) => dt.getTime()))) : null;

  if (d.tipoControle === "parcelada" && ultima) {
    const dias = Math.floor((hoje.getTime() - ultima.getTime()) / 86400000);
    if (dias > 35) return { cor: "#A32D2D", label: "Atrasado" };
  }
  if (!ultima) return { cor: "#854F0B", label: "Sem pagto" };
  return { cor: "#0C447C", label: "Em dia" };
}

export default function DividasPage() {
  const [dividas, setDividas] = useState<Divida[]>([]);
  const [resumo, setResumo] = useState({ totalPagoGeral: 0, saldoTotalGeral: 0, qtdAtivas: 0, qtdQuitadas: 0 });
  const [expandidas, setExpandidas] = useState<Set<number>>(new Set());

  // Form nova dívida
  const [tipo, setTipo] = useState<"parcelada" | "livre">("livre");
  const [nome, setNome] = useState("");
  const [valorTotal, setValorTotal] = useState(0);
  const [valorParcela, setValorParcela] = useState(0);
  const [totalParcelas, setTotalParcelas] = useState("");
  const [diaVenc, setDiaVenc] = useState("");
  const [dataInicio, setDataInicio] = useState("");
  const [taxa, setTaxa] = useState(0);
  const [msgForm, setMsgForm] = useState<{ texto: string; cor: "red" | "green" } | null>(null);

  // Form pagamento
  const [dividaPagId, setDividaPagId] = useState<number | "">("");
  const [valorPag, setValorPag] = useState(0);
  const [dataPag, setDataPag] = useState(formatarDataBR(new Date()));
  const [obsPag, setObsPag] = useState("");
  const [msgPag, setMsgPag] = useState<{ texto: string; cor: "red" | "green" } | null>(null);

  const carregar = useCallback(async () => {
    const res = await fetch("/api/dividas");
    if (res.ok) {
      const data = await res.json();
      setDividas(data.dividas);
      setResumo(data.resumo);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  function toggleExpandida(id: number) {
    setExpandidas((prev) => {
      const novo = new Set(prev);
      if (novo.has(id)) novo.delete(id);
      else novo.add(id);
      return novo;
    });
  }

  function limparFormDivida() {
    setNome("");
    setValorTotal(0);
    setValorParcela(0);
    setTotalParcelas("");
    setDiaVenc("");
    setDataInicio("");
    setTaxa(0);
  }

  async function cadastrarDivida() {
    setMsgForm(null);
    if (!nome.trim()) {
      setMsgForm({ texto: "Informe o nome da dívida.", cor: "red" });
      return;
    }
    if (valorTotal <= 0) {
      setMsgForm({ texto: "Informe o valor total da dívida.", cor: "red" });
      return;
    }
    if (tipo === "parcelada") {
      if (valorParcela <= 0) {
        setMsgForm({ texto: "Informe o valor da parcela.", cor: "red" });
        return;
      }
      if (!totalParcelas) {
        setMsgForm({ texto: "Informe o número de parcelas.", cor: "red" });
        return;
      }
      if (!diaVenc) {
        setMsgForm({ texto: "Informe o dia de vencimento.", cor: "red" });
        return;
      }
    }

    const res = await fetch("/api/dividas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nome: nome.trim(),
        tipoControle: tipo,
        valorTotal,
        valorParcela: tipo === "parcelada" ? valorParcela : undefined,
        totalParcelas: tipo === "parcelada" ? Number(totalParcelas) : undefined,
        diaVencimento: tipo === "parcelada" ? Number(diaVenc) : undefined,
        dataInicio: tipo === "parcelada" ? dataInicio : undefined,
        taxaJuros: taxa,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      setMsgForm({
        texto: `✅ Dívida "${nome.trim()}" cadastrada!${data.aviso ? " " + data.aviso : ""}`,
        cor: "green",
      });
      limparFormDivida();
      carregar();
    } else {
      const err = await res.json();
      setMsgForm({ texto: `❌ ${err.erro}`, cor: "red" });
    }
  }

  async function registrarPagamento() {
    setMsgPag(null);
    if (!dividaPagId) {
      setMsgPag({ texto: "Selecione a dívida.", cor: "red" });
      return;
    }
    if (valorPag <= 0) {
      setMsgPag({ texto: "Informe o valor pago.", cor: "red" });
      return;
    }

    const res = await fetch("/api/divida-pagamentos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dividaId: Number(dividaPagId),
        valor: valorPag,
        data: dataPag,
        observacao: obsPag.trim(),
      }),
    });

    if (res.ok) {
      setMsgPag({ texto: `✅ Pagamento de ${fmt(valorPag)} registrado!`, cor: "green" });
      setValorPag(0);
      setObsPag("");
      setDividaPagId("");
      carregar();
    } else {
      const err = await res.json();
      setMsgPag({ texto: `❌ ${err.erro}`, cor: "red" });
    }
  }

  async function quitarDivida(id: number, nomeD: string) {
    if (!confirm(`Marcar "${nomeD}" como quitada?`)) return;
    await fetch(`/api/dividas/${id}/quitar`, { method: "POST" });
    carregar();
  }

  async function excluirDivida(id: number, nomeD: string) {
    if (!confirm(`Excluir "${nomeD}" e todos os seus pagamentos?`)) return;
    await fetch(`/api/dividas/${id}`, { method: "DELETE" });
    carregar();
  }

  async function excluirPagamento(id: number, valor: number, data: string) {
    if (!confirm(`Excluir pagamento de ${fmt(valor)} em ${data}?`)) return;
    await fetch(`/api/divida-pagamentos/${id}`, { method: "DELETE" });
    carregar();
  }

  const dividasAtivas = dividas.filter((d) => d.status === "ativa");

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-5 p-6">
      <div className="flex items-center gap-2">
        <AlertTriangle className="text-[#A32D2D]" size={26} />
        <h1 className="text-xl font-bold text-[#A32D2D]">CONTROLE DE DÍVIDAS</h1>
      </div>

      {/* Resumo */}
      <div className="flex flex-wrap gap-3">
        <CardResumo titulo="💸 TOTAL PAGO" valor={fmt(resumo.totalPagoGeral)} sub="soma de todos os pagamentos" cor="#A32D2D" />
        <CardResumo titulo="📋 DÍVIDAS ATIVAS" valor={String(resumo.qtdAtivas)} sub="dívidas em aberto" cor="#0C447C" />
        <CardResumo titulo="⏳ SALDO DEVEDOR" valor={fmt(resumo.saldoTotalGeral)} sub="total ainda a pagar" cor="#854F0B" />
        <CardResumo titulo="✅ QUITADAS" valor={String(resumo.qtdQuitadas)} sub="dívidas encerradas" cor="#639922" />
      </div>

      {/* Cadastrar nova dívida */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <p className="text-sm font-bold text-[#A32D2D]">➕ CADASTRAR NOVA DÍVIDA</p>
        <p className="mb-3 text-xs text-gray-400">Escolha como quer controlar essa dívida</p>

        <div className="mb-3 flex items-center gap-2">
          <span className="text-xs text-gray-500">Tipo de controle:</span>
          <button
            onClick={() => setTipo("parcelada")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
              tipo === "parcelada" ? "bg-[#0C447C] text-white" : "bg-gray-200 text-gray-600"
            }`}
          >
            🔵 PARCELADA
          </button>
          <button
            onClick={() => setTipo("livre")}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold ${
              tipo === "livre" ? "bg-[#854F0B] text-white" : "bg-gray-200 text-gray-600"
            }`}
          >
            🟠 PAGAMENTO LIVRE
          </button>
        </div>

        <div className={`mb-3 flex items-start gap-2 rounded-lg p-2.5 ${tipo === "parcelada" ? "bg-[#E6F1FB]" : "bg-[#FAEEDA]"}`}>
          <Info size={14} className={`mt-0.5 flex-shrink-0 ${tipo === "parcelada" ? "text-[#0C447C]" : "text-[#854F0B]"}`} />
          <p className={`text-xs italic ${tipo === "parcelada" ? "text-[#0C447C]" : "text-[#854F0B]"}`}>
            {tipo === "parcelada"
              ? "Uma conta fixa será criada automaticamente e aparecerá em Contas Fixas todo mês para você dar baixa."
              : "Sem vencimento fixo. Você registra o pagamento quando e quanto quiser, abatendo do saldo devedor."}
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <CampoTexto label="Nome da Dívida" value={nome} onChange={setNome} className="w-64" />
          <InputMoeda label="Valor Total (R$)" value={valorTotal} onChange={setValorTotal} className="w-40" />
        </div>

        {tipo === "parcelada" && (
          <div className="mt-2.5 flex flex-wrap gap-3">
            <InputMoeda label="Valor da Parcela (R$)" value={valorParcela} onChange={setValorParcela} className="w-44" />
            <CampoTexto label="Nº Parcelas" value={totalParcelas} onChange={setTotalParcelas} className="w-28" tipo="number" />
            <CampoTexto label="Dia Vencimento" value={diaVenc} onChange={setDiaVenc} className="w-32" tipo="number" />
            <CampoTexto label="Data Início (DD/MM/AAAA)" value={dataInicio} onChange={setDataInicio} className="w-44" />
            <InputMoeda label="Juros % a.m." value={taxa} onChange={setTaxa} className="w-32" />
          </div>
        )}

        <button
          onClick={cadastrarDivida}
          className="mt-3 flex items-center gap-2 rounded-lg bg-[#0C447C] px-5 py-2.5 text-xs font-semibold text-white"
        >
          <Plus size={14} /> CADASTRAR DÍVIDA
        </button>
        {msgForm && (
          <p className={`mt-2 text-xs font-medium ${msgForm.cor === "red" ? "text-red-600" : "text-green-600"}`}>
            {msgForm.texto}
          </p>
        )}
      </div>

      {/* Registrar pagamento avulso */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <p className="text-sm font-bold text-[#A32D2D]">💰 REGISTRAR PAGAMENTO</p>
        <p className="mb-3 text-xs text-gray-400">
          Para dívidas parceladas, dê baixa diretamente em Contas Fixas. Aqui registre pagamentos avulsos.
        </p>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex w-64 flex-col gap-1">
            <span className="text-xs font-medium text-gray-600">Dívida</span>
            <select
              value={dividaPagId}
              onChange={(e) => setDividaPagId(e.target.value ? Number(e.target.value) : "")}
              disabled={dividasAtivas.length === 0}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none disabled:bg-gray-100"
            >
              <option value="">{dividasAtivas.length === 0 ? "Nenhuma dívida ativa" : "Selecione a dívida"}</option>
              {dividasAtivas.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.nome} ({d.tipoControle === "livre" ? "livre" : "parcelada"})
                </option>
              ))}
            </select>
          </label>
          <InputMoeda label="Valor Pago (R$)" value={valorPag} onChange={setValorPag} className="w-40" />
          <CampoTexto label="Data Pagamento" value={dataPag} onChange={setDataPag} className="w-36" />
          <CampoTexto label="Observação (opcional)" value={obsPag} onChange={setObsPag} className="w-56" />
          <button
            onClick={registrarPagamento}
            className="flex h-[38px] items-center gap-1.5 rounded-lg bg-[#A32D2D] px-4 text-xs font-semibold text-white"
          >
            <Save size={14} /> REGISTRAR
          </button>
        </div>
        {msgPag && (
          <p className={`mt-2 text-xs font-medium ${msgPag.cor === "red" ? "text-red-600" : "text-green-600"}`}>
            {msgPag.texto}
          </p>
        )}
      </div>

      {/* Lista de dívidas */}
      <div>
        <p className="mb-2 text-sm font-bold text-[#A32D2D]">📋 DÍVIDAS REGISTRADAS</p>
        {dividas.length === 0 ? (
          <p className="text-sm italic text-gray-400">Nenhuma dívida cadastrada.</p>
        ) : (
          <div className="flex flex-col gap-2.5">
            {dividas.map((d) => {
              const badge = statusBadge(d, new Date());
              const progresso = d.totalParcelas
                ? Math.min(d.pagamentos.length / d.totalParcelas, 1)
                : d.saldo <= 0
                ? 1
                : 0;
              const expandida = expandidas.has(d.id);
              const tipoCor = d.tipoControle === "parcelada" ? "#0C447C" : "#854F0B";

              const infoParts: string[] = [];
              if (d.tipoControle === "parcelada") {
                if (d.valorParcela) infoParts.push(`Parcela: ${fmt(d.valorParcela)}`);
                if (d.diaVencimento) infoParts.push(`Vence dia ${d.diaVencimento}`);
                if (d.dataInicio) infoParts.push(`Início: ${d.dataInicio}`);
                if (d.taxaJuros) infoParts.push(`Juros: ${d.taxaJuros.toFixed(2)}% a.m.`);
              }

              return (
                <div key={d.id} className="rounded-xl border border-gray-200 bg-white p-3.5 shadow-sm">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-[180px] flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-gray-800">{d.nome}</span>
                        <span
                          className="rounded-full border px-2 py-0.5 text-[10px] font-bold"
                          style={{ borderColor: tipoCor, color: tipoCor }}
                        >
                          {d.tipoControle === "parcelada" ? "Parcelada" : "Pagto Livre"}
                        </span>
                      </div>
                      {infoParts.length > 0 && (
                        <p className="text-[10px] text-gray-400">{infoParts.join("  •  ")}</p>
                      )}
                    </div>

                    <span
                      className="flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-bold"
                      style={{ borderColor: badge.cor, color: badge.cor }}
                    >
                      {badge.label}
                    </span>

                    <div className="text-right">
                      <p className="text-[10px] text-gray-400">Total pago</p>
                      <p className="text-sm font-bold text-[#A32D2D]">{fmt(d.totalPago)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-gray-400">Saldo devedor</p>
                      <p className="text-sm font-bold" style={{ color: d.saldo > 0 ? "#854F0B" : "#639922" }}>
                        {d.saldo > 0 ? fmt(d.saldo) : "Quitado"}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-gray-400">Valor total</p>
                      <p className="text-xs text-gray-500">{fmt(d.valorTotal)}</p>
                    </div>

                    <div className="flex items-center gap-1">
                      <button onClick={() => toggleExpandida(d.id)} title="Ver pagamentos">
                        {expandida ? (
                          <ChevronUp size={18} className="text-[#0C447C]" />
                        ) : (
                          <ChevronDown size={18} className="text-[#0C447C]" />
                        )}
                      </button>
                      {d.status === "ativa" && (
                        <button onClick={() => quitarDivida(d.id, d.nome)} title="Marcar como quitada">
                          <CheckCheck size={18} className="text-[#639922]" />
                        </button>
                      )}
                      <button onClick={() => excluirDivida(d.id, d.nome)} title="Excluir dívida">
                        <Trash2 size={18} className="text-[#A32D2D]" />
                      </button>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center gap-2">
                    <span className="flex-1 text-[10px] text-gray-400">
                      {d.totalParcelas
                        ? `${d.pagamentos.length}/${d.totalParcelas} parcelas pagas`
                        : `${d.pagamentos.length} pagamento(s)`}
                    </span>
                    <span className="text-[10px] font-bold text-[#0C447C]">{Math.round(progresso * 100)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded bg-gray-200">
                    <div
                      className="h-1.5 rounded"
                      style={{ width: `${progresso * 100}%`, backgroundColor: progresso >= 1 ? "#639922" : tipoCor }}
                    />
                  </div>

                  {expandida && (
                    <div className="mt-2.5 flex flex-col gap-1.5 border-t border-gray-100 pt-2.5">
                      {d.pagamentos.length === 0 ? (
                        <p className="text-xs italic text-gray-400">Nenhum pagamento registrado ainda.</p>
                      ) : (
                        d.pagamentos.map((p) => (
                          <div
                            key={p.id}
                            className="flex items-center gap-2 rounded-md bg-[#F4F7FB] px-3 py-1.5"
                          >
                            <Receipt size={14} className="text-[#0C447C]" />
                            <span className="w-20 flex-shrink-0 text-xs text-gray-500">{p.data}</span>
                            <span className="flex-1 truncate text-xs text-gray-500">{p.observacao || ""}</span>
                            <span className="text-xs font-bold text-[#A32D2D]">{fmt(p.valor)}</span>
                            <button onClick={() => excluirPagamento(p.id, p.valor, p.data)}>
                              <Trash2 size={13} className="text-[#A32D2D]" />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function CardResumo({ titulo, valor, sub, cor }: { titulo: string; valor: string; sub: string; cor: string }) {
  return (
    <div className="min-w-[200px] flex-1 rounded-xl p-4 text-white shadow" style={{ backgroundColor: cor }}>
      <p className="text-[11px] font-bold">{titulo}</p>
      <p className="text-xl font-bold">{valor}</p>
      <p className="text-[10px] text-white/70">{sub}</p>
    </div>
  );
}

function CampoTexto({
  label,
  value,
  onChange,
  className = "",
  tipo = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  className?: string;
  tipo?: string;
}) {
  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <input
        type={tipo}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
      />
    </label>
  );
}
