import { Landmark } from "lucide-react";
import { fmt } from "@/lib/utils";
import { DashboardData } from "@/types/dashboard";

interface CardsBancosProps {
  bancos: DashboardData["bancos"];
}

export function CardsBancos({ bancos }: CardsBancosProps) {
  if (bancos.length === 0) {
    return <p className="text-sm italic text-gray-400">Nenhum banco cadastrado.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2.5">
      {bancos.map((b) => (
        <div key={b.id} className="min-w-[170px] flex-1 rounded-xl bg-[#37474F] p-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <Landmark size={14} className="text-white" />
            <span className="text-[11px] font-bold text-white">{b.nomeBanco}</span>
          </div>
          <span className="text-base font-bold text-white">{fmt(b.saldoAtual)}</span>
          <p className="mt-0.5 text-[9px] text-white/60">
            Ag: {b.agencia || "—"} | Cta: {b.numeroConta || "—"}
          </p>
        </div>
      ))}
    </div>
  );
}
