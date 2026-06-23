"use client";

import { CheckCircle2, XCircle } from "lucide-react";
import { ValidacaoCampo } from "@/lib/validacao-cadastro";

interface CampoValidadoProps {
  label: string;
  value: string;
  onChange: (valor: string) => void;
  onBlur?: () => void;
  validacao?: ValidacaoCampo;
  placeholder?: string;
  maxLength?: number;
  type?: string;
  className?: string;
}

/** Traduz a lógica visual de set_field_state() em cadastro.py para React/Tailwind */
export function CampoValidado({
  label,
  value,
  onChange,
  onBlur,
  validacao,
  placeholder,
  maxLength,
  type = "text",
  className = "",
}: CampoValidadoProps) {
  const corBorda =
    validacao?.valido === true
      ? "border-green-500 focus:ring-green-500"
      : validacao?.valido === false
      ? "border-red-500 focus:ring-red-500"
      : "border-gray-300 focus:ring-[#0C447C]";

  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <div className="relative">
        <input
          type={type}
          value={value}
          placeholder={placeholder}
          maxLength={maxLength}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          className={`w-full rounded-lg border bg-white px-3 py-2 pr-8 text-sm text-gray-900 outline-none focus:ring-1 ${corBorda}`}
        />
        {validacao?.valido === true && (
          <CheckCircle2
            size={16}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-green-500"
          />
        )}
        {validacao?.valido === false && (
          <XCircle
            size={16}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-red-500"
          />
        )}
      </div>
      {validacao?.valido === false && validacao.erro && (
        <span className="text-[11px] text-red-600">{validacao.erro}</span>
      )}
    </label>
  );
}
