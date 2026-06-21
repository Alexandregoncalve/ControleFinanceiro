import { CartaoBanco } from "@/components/ui/CartaoBanco";
import { DashboardData } from "@/types/dashboard";

interface CardsBancosProps {
  bancos: DashboardData["bancos"];
}

const VARIANTES: ("azul" | "verde")[] = ["azul", "verde"];

export function CardsBancos({ bancos }: CardsBancosProps) {
  if (bancos.length === 0) {
    return <p className="text-sm italic text-gray-400">Nenhum banco cadastrado.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {bancos.map((b, i) => (
        <CartaoBanco
          key={b.id}
          nomeBanco={b.nomeBanco}
          saldo={b.saldoAtual}
          agencia={b.agencia}
          numeroConta={b.numeroConta}
          variante={VARIANTES[i % VARIANTES.length]}
        />
      ))}
    </div>
  );
}
