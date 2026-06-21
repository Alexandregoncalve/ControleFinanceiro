"use client";

import { useState, useEffect } from "react";
import { limparValor, formatarMoedaInput } from "@/lib/utils";

interface InputMoedaProps {
  label: string;
  value: number;
  onChange: (valor: number) => void;
  placeholder?: string;
  className?: string;
}

/**
 * Campo de texto que formata automaticamente como moeda brasileira ao perder foco.
 * Equivalente ao on_blur=formatar_moeda_input usado em vários formulários Python.
 */
export function InputMoeda({
  label,
  value,
  onChange,
  placeholder = "0,00",
  className = "",
}: InputMoedaProps) {
  const [texto, setTexto] = useState(value > 0 ? formatarMoedaInput(value) : "");

  useEffect(() => {
    setTexto(value > 0 ? formatarMoedaInput(value) : "");
  }, [value]);

  function handleBlur() {
    const numero = limparValor(texto);
    setTexto(numero > 0 ? formatarMoedaInput(numero) : "");
    onChange(numero);
  }

  return (
    <label className={`flex flex-col gap-1 ${className}`}>
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <div className="flex items-center rounded-lg border border-gray-300 bg-white px-3 py-2 focus-within:border-[#1565C0] focus-within:ring-1 focus-within:ring-[#1565C0]">
        <span className="text-sm text-gray-500 mr-1">R$</span>
        <input
          type="text"
          inputMode="decimal"
          value={texto}
          placeholder={placeholder}
          onChange={(e) => setTexto(e.target.value)}
          onBlur={handleBlur}
          className="w-full text-sm outline-none"
        />
      </div>
    </label>
  );
}
