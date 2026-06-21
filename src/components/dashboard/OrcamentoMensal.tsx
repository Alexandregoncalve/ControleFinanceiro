import { fmt } from "@/lib/utils";

interface OrcamentoMensalProps {
  orcamentos: { nome: string; total: number; orcamento: number }[];
}

function statusOrcamento(pct: number) {
  if (pct >= 100) return { icone: "🔴", bg: "#FCEBEB", cor: "#A32D2D", trilha: "#F7C1C1" };
  if (pct >= 80) return { icone: "🟡", bg: "#FAEEDA", cor: "#854F0B", trilha: "#FAC775" };
  return { icone: "✅", bg: "#EAF3DE", cor: "#3B6D11", trilha: "#C0DD97" };
}

/** Traduz a seção de Orçamento mensal de views/dashboard.py — grid 3 colunas, ordenado por % de uso */
export function OrcamentoMensal({ orcamentos }: OrcamentoMensalProps) {
  if (orcamentos.length === 0) {
    return <p className="text-sm italic text-gray-400">Nenhum orçamento definido.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {orcamentos.map((o) => {
        const pct = o.orcamento > 0 ? (o.total / o.orcamento) * 100 : 0;
        const { icone, bg, cor, trilha } = statusOrcamento(pct);
        const diff = Math.abs(o.orcamento - o.total);
        const sub = o.total > o.orcamento ? `Ultrapassado ${fmt(diff)}` : `Restam ${fmt(diff)}`;

        return (
          <div key={o.nome} className="rounded-lg p-2.5" style={{ backgroundColor: bg }}>
            <div className="mb-0.5 flex items-center justify-between gap-1">
              <span className="truncate text-[11px] font-bold" style={{ color: cor }}>
                {icone} {o.nome}
              </span>
              <span className="flex-shrink-0 text-[11px] font-bold" style={{ color: cor }}>
                {pct.toFixed(0)}%
              </span>
            </div>
            <p className="truncate text-[9px]" style={{ color: cor }}>
              {fmt(o.total)} / {fmt(o.orcamento)}
            </p>
            <div className="my-1 h-1.5 rounded" style={{ backgroundColor: trilha }}>
              <div
                className="h-1.5 rounded"
                style={{ width: `${Math.min(100, pct)}%`, backgroundColor: cor }}
              />
            </div>
            <p className="text-[9px]" style={{ color: cor }}>
              {sub}
            </p>
          </div>
        );
      })}
    </div>
  );
}
