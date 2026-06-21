import { fmt } from "@/lib/utils";
import { DashboardData } from "@/types/dashboard";

interface ComoEstaOMesProps {
  resumo: DashboardData["resumo"];
  historico: DashboardData["historico"];
}

/** Traduz a seção "Como está o mês" de views/dashboard.py */
export function ComoEstaOMes({ resumo, historico }: ComoEstaOMesProps) {
  const { receitas, despesas, resultado } = resumo;
  const maxAtual = Math.max(receitas, despesas, 1);
  const positivo = resultado >= 0;

  const maxHist = Math.max(...historico.map((h) => Math.max(h.receita, h.despesa)), 1);

  return (
    <div className="flex flex-col gap-3">
      <div
        className={`rounded-md px-3 py-2 text-xs font-bold ${
          positivo ? "bg-[#E8F5E9] text-[#2E7D32]" : "bg-[#FFEBEE] text-[#C62828]"
        }`}
      >
        {positivo ? "✅" : "❌"}{" "}
        {positivo
          ? `Sobrou ${fmt(resultado)} este mês`
          : `Gastou ${fmt(Math.abs(resultado))} a mais do que recebeu`}
      </div>

      <BarraComparativa label="Receita" valor={receitas} max={maxAtual} cor="#2E7D32" />
      <BarraComparativa label="Despesa" valor={despesas} max={maxAtual} cor="#C62828" />

      <hr className="border-[#E8EEF7]" />
      <p className="text-[10px] text-gray-400">Histórico dos últimos meses</p>

      <div className="flex flex-col gap-1.5">
        {historico.map((h) => {
          const saldo = h.receita - h.despesa;
          const corSaldo = saldo >= 0 ? "#2E7D32" : "#C62828";
          return (
            <div
              key={h.mes}
              className={`flex items-center gap-2 rounded px-1 py-1 ${h.ehAtual ? "bg-[#EEF4FF]" : ""}`}
            >
              <span
                className={`w-14 flex-shrink-0 text-[10px] font-bold ${
                  h.ehAtual ? "text-[#1565C0]" : "text-gray-500"
                }`}
              >
                {h.mes}
                {h.ehAtual && " ◀"}
              </span>
              <div className="flex flex-1 flex-col gap-0.5">
                <div
                  className="h-2 rounded bg-[#2E7D32]"
                  style={{ width: `${Math.max(3, (h.receita / maxHist) * 100)}%` }}
                />
                <div
                  className="h-2 rounded bg-[#C62828]"
                  style={{ width: `${Math.max(3, (h.despesa / maxHist) * 100)}%` }}
                />
              </div>
              <span className="w-20 flex-shrink-0 text-right text-[10px] font-bold" style={{ color: corSaldo }}>
                {saldo >= 0 ? "+" : "-"}
                {fmt(Math.abs(saldo))}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BarraComparativa({
  label,
  valor,
  max,
  cor,
}: {
  label: string;
  valor: number;
  max: number;
  cor: string;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-14 flex-shrink-0 text-[11px] font-bold" style={{ color: cor }}>
        {label}
      </span>
      <div className="h-5 flex-1 rounded bg-[#F0F4FA]">
        <div
          className="h-5 rounded transition-all"
          style={{ width: `${(valor / max) * 100}%`, backgroundColor: cor }}
        />
      </div>
      <span className="w-24 flex-shrink-0 text-right text-[11px] font-bold" style={{ color: cor }}>
        {fmt(valor)}
      </span>
    </div>
  );
}
