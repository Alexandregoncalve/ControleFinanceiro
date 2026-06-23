"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, CheckCircle2, ArrowRight, ArrowLeft, AlertTriangle, FileText } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { apiFetch } from "@/lib/api-fetch";
import { fmt } from "@/lib/utils";
import { LinhaExtrato, ResultadoParsing } from "@/lib/conciliacao/tipos";

// Busca simples de subconta via API — específica para conciliação
function BuscaSubcontaConciliacao({
  subcontaId,
  subcontaNome,
  onSelecionar,
}: {
  subcontaId: number | null;
  subcontaNome: string;
  onSelecionar: (nome: string, id: number) => void;
}) {
  const [busca, setBusca] = useState("");
  const [opcoes, setOpcoes] = useState<{ id: number; nome: string; categoria: string }[]>([]);
  const [aberto, setAberto] = useState(false);

  async function pesquisar(q: string) {
    setBusca(q);
    if (q.length < 2) { setOpcoes([]); return; }
    const res = await apiFetch<{ subcontas: { id: number; nome: string; categoria: string }[] }>(
      `/api/subcontas?busca=${encodeURIComponent(q)}`,
      { toastErro: false }
    );
    if (res.ok && res.data) setOpcoes(res.data.subcontas);
    setAberto(true);
  }

  return (
    <div className="relative">
      <input
        type="text"
        value={subcontaId ? subcontaNome : busca}
        onChange={(e) => { onSelecionar("", 0); pesquisar(e.target.value); }}
        placeholder="Digite para buscar a conta (ex: Sicredi, Salário...)"
        className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-[#0C447C] dark:border-white/15 dark:bg-[#0F172A] dark:text-gray-100"
      />
      {aberto && opcoes.length > 0 && (
        <div className="absolute top-full left-0 right-0 z-20 mt-1 max-h-48 overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg dark:border-white/10 dark:bg-[#1E293B]">
          {opcoes.map((o) => (
            <button
              key={o.id}
              className="flex w-full flex-col px-3 py-2 text-left hover:bg-[#E6F1FB] dark:hover:bg-white/10"
              onClick={() => { onSelecionar(o.nome, o.id); setBusca(""); setAberto(false); }}
            >
              <span className="text-sm text-gray-800 dark:text-gray-100">{o.nome}</span>
              <span className="text-[10px] text-gray-400">{o.categoria}</span>
            </button>
          ))}
        </div>
      )}
      {subcontaId ? (
        <p className="mt-1 text-xs text-[#3B6D11] dark:text-green-400">✓ {subcontaNome}</p>
      ) : null}
    </div>
  );
}

type Passo = 1 | 2 | 3;

const FORMATOS_ACEITOS = ".csv,.xlsx,.xls,.ofx,.qfx,.pdf";

export default function ConciliacaoPage() {
  const [passo, setPasso] = useState<Passo>(1);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [resultado, setResultado] = useState<ResultadoParsing | null>(null);
  const [linhas, setLinhas] = useState<LinhaExtrato[]>([]);
  const [subcontaId, setSubcontaId] = useState<number | null>(null);
  const [subcontaNome, setSubcontaNome] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [importando, setImportando] = useState(false);
  const [mensagemFinal, setMensagemFinal] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const totalSelecionadas = linhas.filter((l) => l.selecionada).length;
  const totalReceitas = linhas.filter((l) => l.selecionada && l.tipo === "Receita").reduce((a, l) => a + l.valor, 0);
  const totalDespesas = linhas.filter((l) => l.selecionada && l.tipo === "Despesa").reduce((a, l) => a + l.valor, 0);

  async function processarArquivo() {
    if (!arquivo) return;
    setCarregando(true);

    const form = new FormData();
    form.append("arquivo", arquivo);

    const res = await apiFetch<ResultadoParsing>("/api/conciliacao/parsear", {
      method: "POST",
      body: form,
      mensagemErroPadrao: "Não foi possível processar o arquivo.",
    });

    setCarregando(false);
    if (res.ok && res.data) {
      setResultado(res.data);
      setLinhas(res.data.linhas);
      setPasso(2);
    }
  }

  async function confirmarImportacao() {
    if (!subcontaId || linhas.length === 0) return;
    setImportando(true);

    const res = await apiFetch<{ importadas: number; duplicatas: number; mensagem: string }>(
      "/api/conciliacao/confirmar",
      {
        method: "POST",
        body: JSON.stringify({ subcontaId, linhas }),
        mensagemErroPadrao: "Erro ao importar os lançamentos.",
      }
    );

    setImportando(false);
    if (res.ok && res.data) {
      setMensagemFinal(res.data.mensagem);
      setPasso(3);
    }
  }

  function reiniciar() {
    setPasso(1);
    setArquivo(null);
    setResultado(null);
    setLinhas([]);
    setSubcontaId(null);
    setSubcontaNome("");
    setMensagemFinal("");
  }

  function alternarLinha(idx: number) {
    setLinhas((prev) =>
      prev.map((l, i) => (i === idx ? { ...l, selecionada: !l.selecionada } : l))
    );
  }

  function selecionarTodas(selecionada: boolean) {
    setLinhas((prev) => prev.map((l) => ({ ...l, selecionada })));
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setArquivo(f);
  }, []);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-4 p-4 sm:p-6">
      <PageHeader titulo="Conciliação Bancária" icon={FileText} />

      {/* Indicador de passos */}
      <div className="flex items-center gap-2">
        {([1, 2, 3] as Passo[]).map((p) => (
          <div key={p} className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold ${
                passo >= p
                  ? "bg-[#0C447C] text-white"
                  : "bg-gray-200 text-gray-500 dark:bg-white/10 dark:text-gray-400"
              }`}
            >
              {passo > p ? <CheckCircle2 size={14} /> : p}
            </div>
            <span className={`text-xs ${passo >= p ? "text-[#0C447C] dark:text-blue-300 font-medium" : "text-gray-400"}`}>
              {p === 1 ? "Upload" : p === 2 ? "Revisão" : "Concluído"}
            </span>
            {p < 3 && <ArrowRight size={12} className="text-gray-300" />}
          </div>
        ))}
      </div>

      {/* PASSO 1 — Upload */}
      {passo === 1 && (
        <div className="flex flex-col gap-4">
          <div
            className="flex cursor-pointer flex-col items-center gap-3 rounded-xl border-2 border-dashed border-[#0C447C]/30 bg-white p-10 transition hover:border-[#0C447C]/60 hover:bg-[#E6F1FB]/30 dark:bg-[#1E293B] dark:border-white/20"
            onClick={() => inputRef.current?.click()}
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
          >
            <Upload size={36} className="text-[#0C447C] dark:text-blue-300 opacity-70" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
                Arraste o extrato aqui ou clique para selecionar
              </p>
              <p className="mt-1 text-xs text-gray-400">
                Formatos aceitos: CSV, Excel (.xlsx/.xls), OFX, PDF — até 10MB
              </p>
            </div>
            {arquivo && (
              <div className="flex items-center gap-2 rounded-lg bg-[#EAF3DE] px-3 py-1.5 dark:bg-green-900/40">
                <CheckCircle2 size={14} className="text-[#3B6D11] dark:text-green-400" />
                <span className="text-xs font-medium text-[#3B6D11] dark:text-green-400">{arquivo.name}</span>
              </div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept={FORMATOS_ACEITOS}
              className="hidden"
              onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
            />
          </div>

          <div className="rounded-lg bg-[#E6F1FB] p-3 dark:bg-blue-900/30">
            <p className="text-xs text-[#0C447C] dark:text-blue-300">
              <strong>Dica:</strong> O formato OFX (exportado pelo Sicredi) é o mais confiável —
              os dados já vêm estruturados e a importação é mais precisa. Se possível, prefira
              OFX ou XLS ao PDF.
            </p>
          </div>

          <Button
            variante="primario"
            carregando={carregando}
            disabled={!arquivo || carregando}
            onClick={processarArquivo}
            className="self-end"
          >
            {carregando ? "Processando..." : "PROCESSAR ARQUIVO"}
            {!carregando && <ArrowRight size={14} />}
          </Button>
        </div>
      )}

      {/* PASSO 2 — Revisão */}
      {passo === 2 && resultado && (
        <div className="flex flex-col gap-4">
          {resultado.avisos.length > 0 && (
            <div className="flex flex-col gap-1.5 rounded-lg bg-[#FAEEDA] p-3 dark:bg-yellow-900/30">
              {resultado.avisos.map((a, i) => (
                <div key={i} className="flex items-start gap-2">
                  <AlertTriangle size={13} className="mt-0.5 flex-shrink-0 text-[#854F0B]" />
                  <p className="text-xs text-[#854F0B]">{a}</p>
                </div>
              ))}
            </div>
          )}

          <div className="rounded-xl border border-[#E2E8F0] bg-white p-4 dark:border-white/10 dark:bg-[#1E293B]">
            <p className="mb-3 text-sm font-bold text-[#0C447C] dark:text-blue-300">
              Selecione a conta de destino
            </p>
            <BuscaSubcontaConciliacao
              subcontaId={subcontaId}
              subcontaNome={subcontaNome}
              onSelecionar={(nome, id) => { setSubcontaNome(nome); setSubcontaId(id); }}
            />
          </div>

          <div className="rounded-xl border border-[#E2E8F0] bg-white dark:border-white/10 dark:bg-[#1E293B]">
            <div className="flex items-center justify-between border-b border-[#E2E8F0] p-3 dark:border-white/10">
              <div className="flex items-center gap-3">
                <p className="text-sm font-bold text-[#0C447C] dark:text-blue-300">
                  {linhas.length} transações detectadas
                </p>
                <span className="text-xs text-gray-400">{totalSelecionadas} selecionadas</span>
              </div>
              <div className="flex gap-2">
                <button onClick={() => selecionarTodas(true)} className="text-xs text-[#0C447C] hover:underline dark:text-blue-300">
                  Todas
                </button>
                <button onClick={() => selecionarTodas(false)} className="text-xs text-gray-400 hover:underline">
                  Nenhuma
                </button>
              </div>
            </div>

            <div className="max-h-[400px] overflow-y-auto">
              {linhas.map((l, i) => (
                <label
                  key={i}
                  className="flex cursor-pointer items-start gap-3 border-b border-[#F4F7FB] p-3 hover:bg-gray-50 last:border-0 dark:border-white/5 dark:hover:bg-white/5"
                >
                  <input
                    type="checkbox"
                    checked={l.selecionada}
                    onChange={() => alternarLinha(i)}
                    className="mt-0.5 h-4 w-4 flex-shrink-0"
                  />
                  <div className="flex flex-1 flex-col gap-0.5 min-w-0">
                    <span className="truncate text-sm text-gray-800 dark:text-gray-100">{l.descricao}</span>
                    <span className="text-[10px] text-gray-400">{l.data}</span>
                  </div>
                  <span
                    className={`flex-shrink-0 text-sm font-bold ${
                      l.tipo === "Receita" ? "text-[#3B6D11] dark:text-green-400" : "text-[#A32D2D]"
                    }`}
                  >
                    {l.tipo === "Despesa" ? "-" : "+"}
                    {fmt(l.valor)}
                  </span>
                </label>
              ))}
            </div>

            <div className="flex gap-4 border-t border-[#E2E8F0] p-3 dark:border-white/10">
              <div className="flex-1 text-center">
                <p className="text-[10px] text-gray-400">Entradas selecionadas</p>
                <p className="text-sm font-bold text-[#3B6D11] dark:text-green-400">{fmt(totalReceitas)}</p>
              </div>
              <div className="flex-1 text-center">
                <p className="text-[10px] text-gray-400">Saídas selecionadas</p>
                <p className="text-sm font-bold text-[#A32D2D]">{fmt(totalDespesas)}</p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <Button variante="fantasma" onClick={() => setPasso(1)}>
              <ArrowLeft size={14} /> Voltar
            </Button>
            <Button
              variante="primario"
              carregando={importando}
              disabled={!subcontaId || totalSelecionadas === 0 || importando}
              onClick={confirmarImportacao}
            >
              {importando ? "Importando..." : `IMPORTAR ${totalSelecionadas} LANÇAMENTO(S)`}
              {!importando && <ArrowRight size={14} />}
            </Button>
          </div>
        </div>
      )}

      {/* PASSO 3 — Concluído */}
      {passo === 3 && (
        <div className="flex flex-col items-center gap-4 py-10">
          <CheckCircle2 size={56} className="text-[#3B6D11] dark:text-green-400" />
          <p className="text-lg font-bold text-gray-800 dark:text-gray-100">Importação concluída!</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{mensagemFinal}</p>
          <div className="flex gap-3">
            <Button variante="fantasma" onClick={reiniciar}>
              Importar outro arquivo
            </Button>
            <Button variante="secundario" onClick={() => window.location.href = "/extrato"}>
              Ver no Extrato
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
