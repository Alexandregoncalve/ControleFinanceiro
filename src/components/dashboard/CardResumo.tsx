import { LucideIcon } from "lucide-react";
import { fmt } from "@/lib/utils";

interface CardResumoProps {
  titulo: string;
  icon: LucideIcon;
  valor: number;
  corBorda: string;
  variacaoTexto?: string;
  metaTexto?: string;
  destaque?: { texto: string; cor: "verde" | "vermelho" };
}

/** Traduz big_card() / card_meta() de views/dashboard.py */
export function CardResumo({
  titulo,
  icon: Icon,
  valor,
  corBorda,
  variacaoTexto,
  metaTexto,
  destaque,
}: CardResumoProps) {
  return (
    <div
      className="flex h-32 flex-1 flex-col gap-1 rounded-xl bg-white p-3.5 shadow-sm"
      style={{ borderLeft: `4px solid ${corBorda}` }}
    >
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold" style={{ color: corBorda }}>
          {titulo}
        </span>
        <Icon size={14} style={{ color: corBorda }} />
      </div>
      <span className="text-xl font-bold" style={{ color: corBorda }}>
        {fmt(valor)}
      </span>
      {variacaoTexto && <span className="text-[10px] text-gray-500">{variacaoTexto}</span>}
      {destaque && (
        <span
          className={`w-fit rounded px-1.5 py-0.5 text-[10px] font-semibold ${
            destaque.cor === "verde" ? "bg-[#E8F5E9] text-[#2E7D32]" : "bg-[#FFEBEE] text-[#C62828]"
          }`}
        >
          {destaque.texto}
        </span>
      )}
      {metaTexto && <span className="text-[10px] italic text-gray-400">{metaTexto}</span>}
    </div>
  );
}
