import { Landmark, Wifi } from "lucide-react";
import { fmt } from "@/lib/utils";

interface CartaoBancoProps {
  nomeBanco: string;
  saldo: number;
  agencia?: string | null;
  numeroConta?: string | null;
  variante?: "azul" | "verde";
  className?: string;
}

const GRADIENTES = {
  azul: "linear-gradient(135deg, #042C53, #185FA5)",
  verde: "linear-gradient(135deg, #173404, #3B6D11)",
};

/** Card visual de conta bancária com estética de cartão físico (gradiente, chip, textura). */
export function CartaoBanco({
  nomeBanco,
  saldo,
  agencia,
  numeroConta,
  variante = "azul",
  className = "",
}: CartaoBancoProps) {
  return (
    <div
      className={`relative flex min-h-[150px] flex-col justify-between overflow-hidden rounded-2xl p-5 text-white ${className}`}
      style={{ background: GRADIENTES[variante] }}
    >
      <div className="flex items-start justify-between">
        <Landmark size={20} className="opacity-85" />
        <span className="text-[10px] tracking-wider opacity-70">CONTA CORRENTE</span>
      </div>
      <div>
        <p className="mb-0.5 text-[11px] opacity-65">{nomeBanco}</p>
        <p className="text-xl font-medium tracking-wide">{fmt(saldo)}</p>
      </div>
      <div className="flex items-end justify-between text-[10px] opacity-70">
        <span>
          Ag {agencia || "—"} · Cta {numeroConta || "—"}
        </span>
        <Wifi size={15} className="rotate-90" />
      </div>
    </div>
  );
}
