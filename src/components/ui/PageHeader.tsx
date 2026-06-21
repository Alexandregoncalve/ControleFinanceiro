import { LucideIcon } from "lucide-react";

interface PageHeaderProps {
  titulo: string;
  icon?: LucideIcon;
  acoes?: React.ReactNode;
}

/** Cabeçalho padronizado de página: ícone + título azul + linha verde decorativa + slot de ações à direita. */
export function PageHeader({ titulo, icon: Icon, acoes }: PageHeaderProps) {
  return (
    <div className="mb-5 flex items-end justify-between gap-3">
      <div>
        <div className="flex items-center gap-2">
          {Icon && <Icon className="text-[#0C447C]" size={24} />}
          <h1 className="text-xl font-bold text-[#0C447C]">{titulo}</h1>
        </div>
        <div className="mt-1.5 h-[3px] w-16 rounded bg-[#3B6D11]" />
      </div>
      {acoes && <div className="flex items-center gap-2">{acoes}</div>}
    </div>
  );
}
