import { CreditCard } from "lucide-react";

interface CartaoCreditoProps {
  nomeCartao: string;
  nomeBanco?: string | null;
  titular?: string;
  ultimosDigitos?: string;
  className?: string;
}

/** Card visual de cartão de crédito com chip, número mascarado e estética de cartão físico. */
export function CartaoCredito({
  nomeCartao,
  nomeBanco,
  titular = "TITULAR DA CONTA",
  ultimosDigitos = "0000",
  className = "",
}: CartaoCreditoProps) {
  return (
    <div
      className={`relative flex min-h-[180px] flex-col justify-between rounded-2xl p-5 text-white ${className}`}
      style={{ background: "linear-gradient(135deg, #042C53, #0C447C)" }}
    >
      <div className="flex items-start justify-between">
        <div
          className="h-7 w-9 rounded-md"
          style={{ background: "linear-gradient(135deg, #EF9F27, #FAC775)" }}
        />
        <CreditCard size={18} className="opacity-70" />
      </div>

      <div>
        <p className="font-mono text-base tracking-[0.18em]">•••• •••• •••• {ultimosDigitos}</p>
        <p className="mt-1 text-[10px] opacity-60">
          {nomeCartao}
          {nomeBanco ? ` · ${nomeBanco}` : ""}
        </p>
      </div>

      <div className="flex items-end justify-between">
        <div>
          <p className="mb-0.5 text-[9px] opacity-60">TITULAR</p>
          <p className="text-xs tracking-wide">{titular}</p>
        </div>
      </div>
    </div>
  );
}
