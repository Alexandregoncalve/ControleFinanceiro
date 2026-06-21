import { Heart } from "lucide-react";
import { DashboardData } from "@/types/dashboard";

interface CardSaudeProps {
  saude: DashboardData["saude"];
}

const CORES_LABEL: Record<DashboardData["saude"]["label"], { cor: string; bg: string }> = {
  BOA: { cor: "#3B6D11", bg: "#EAF3DE" },
  REGULAR: { cor: "#854F0B", bg: "#FAEEDA" },
  ATENÇÃO: { cor: "#A32D2D", bg: "#FCEBEB" },
};

/** Traduz o card de saúde financeira de views/dashboard.py */
export function CardSaude({ saude }: CardSaudeProps) {
  const { cor, bg } = CORES_LABEL[saude.label];

  return (
    <div
      className="flex h-32 flex-1 flex-col items-center justify-center gap-0.5 rounded-xl p-3"
      style={{ backgroundColor: bg, borderLeft: `4px solid ${cor}` }}
      title={`Poupança: ${saude.indicadores.poupanca}% · Orçamento: ${saude.indicadores.orcamento}% · Fixas pagas: ${saude.indicadores.fixasPagas}% · Renda livre: ${saude.indicadores.rendaLivre}%`}
    >
      <div className="flex items-center gap-1">
        <Heart size={12} style={{ color: cor }} />
        <span className="text-[10px] font-bold" style={{ color: cor }}>
          SAÚDE
        </span>
      </div>
      <span className="text-3xl font-bold" style={{ color: cor }}>
        {saude.score}
      </span>
      <span className="text-[11px] font-bold" style={{ color: cor }}>
        {saude.label}
      </span>
      <span className="text-[9px] text-gray-500">financeira</span>
    </div>
  );
}
