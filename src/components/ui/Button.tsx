import { ButtonHTMLAttributes } from "react";
import { LoadingBotao } from "./Loading";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: "primario" | "secundario" | "perigo" | "fantasma";
  carregando?: boolean;
}

const ESTILOS: Record<NonNullable<ButtonProps["variante"]>, string> = {
  primario: "bg-[#0C447C] text-white hover:bg-[#042C53]",
  secundario: "bg-[#3B6D11] text-white hover:bg-[#173404]",
  perigo: "border border-[#A32D2D] text-[#A32D2D] hover:bg-[#FCEBEB]",
  fantasma: "border border-gray-300 text-gray-600 hover:bg-gray-50",
};

/** Botão padronizado da identidade visual (azul = ação primária, verde = confirmação, vermelho = exclusão). */
export function Button({
  variante = "primario",
  carregando = false,
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || carregando}
      className={`flex h-10 items-center justify-center gap-2 rounded-lg px-5 text-xs font-semibold transition disabled:opacity-60 ${ESTILOS[variante]} ${className}`}
      {...props}
    >
      {carregando && <LoadingBotao size={14} />}
      {children}
    </button>
  );
}
