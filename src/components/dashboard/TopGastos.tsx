import { fmt } from "@/lib/utils";

interface TopGastosProps {
  gastos: { nome: string; total: number }[];
  totalDespesas: number;
}

/** Traduz a seção "Onde está indo o dinheiro" de views/dashboard.py */
export function TopGastos({ gastos, totalDespesas }: TopGastosProps) {
  if (gastos.length === 0) {
    return <p className="text-sm italic text-gray-400">Sem despesas no período.</p>;
  }

  const max = gastos[0].total;

  return (
    <div className="flex flex-col">
      {gastos.map((g, i) => {
        const pct = totalDespesas > 0 ? (g.total / totalDespesas) * 100 : 0;
        return (
          <div key={g.nome} className="flex items-center gap-2 border-b border-[#F4F7FB] py-1.5 last:border-0">
            <div className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-[#E6F1FB] text-[10px] font-bold text-[#0C447C]">
              {i + 1}
            </div>
            <span className="w-44 flex-shrink-0 truncate text-[11px] text-gray-700">{g.nome}</span>
            <div className="h-1.5 w-20 flex-shrink-0 rounded bg-[#F4F7FB]">
              <div
                className="h-1.5 rounded bg-[#A32D2D]"
                style={{ width: `${Math.max(3, (g.total / max) * 100)}%` }}
              />
            </div>
            <span className="w-20 flex-shrink-0 text-right text-[11px] font-bold text-[#A32D2D]">
              {fmt(g.total)}
            </span>
            <span className="w-9 flex-shrink-0 text-right text-[10px] text-gray-400">{pct.toFixed(1)}%</span>
          </div>
        );
      })}
    </div>
  );
}
