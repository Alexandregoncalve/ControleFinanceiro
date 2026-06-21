"use client";

import { useState, useMemo } from "react";
import { ArrowRight } from "lucide-react";

interface SubcontaOpcao {
  id: number;
  nome: string;
  categoriaTipo?: "Receita" | "Despesa";
}

interface BuscaSubcontaProps {
  label: string;
  subcontas: SubcontaOpcao[];
  onSelecionar: (s: SubcontaOpcao) => void;
  placeholder?: string;
  className?: string;
}

/** Traduz o autocomplete de busca de conta em views/avulso.py (filtrar_contas / filtrar_cat_real) */
export function BuscaSubconta({
  label,
  subcontas,
  onSelecionar,
  placeholder = "Digite para buscar...",
  className = "",
}: BuscaSubcontaProps) {
  const [texto, setTexto] = useState("");
  const [aberto, setAberto] = useState(false);

  const filtradas = useMemo(() => {
    if (!texto.trim()) return [];
    const termo = texto.toUpperCase();
    return subcontas.filter((s) => s.nome.toUpperCase().includes(termo)).slice(0, 8);
  }, [texto, subcontas]);

  function selecionar(s: SubcontaOpcao) {
    setTexto(s.nome);
    setAberto(false);
    onSelecionar(s);
  }

  return (
    <div className={`relative flex flex-col gap-1 ${className}`}>
      <span className="text-xs font-medium text-gray-600">{label}</span>
      <input
        type="text"
        value={texto}
        placeholder={placeholder}
        onChange={(e) => {
          setTexto(e.target.value);
          setAberto(true);
        }}
        onFocus={() => setAberto(true)}
        onBlur={() => setTimeout(() => setAberto(false), 150)}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
      />
      {aberto && filtradas.length > 0 && (
        <div className="absolute top-full z-10 mt-1 w-full overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg">
          {filtradas.map((s) => (
            <button
              key={s.id}
              type="button"
              onMouseDown={() => selecionar(s)}
              className="flex w-full items-center gap-2 border-b border-gray-100 px-3 py-2 text-left text-xs last:border-0 hover:bg-gray-50"
            >
              <ArrowRight
                size={12}
                className={s.categoriaTipo === "Receita" ? "text-[#3B6D11]" : "text-[#A32D2D]"}
              />
              <span className="flex-1">{s.nome}</span>
              {s.categoriaTipo && (
                <span
                  className={`text-[10px] ${
                    s.categoriaTipo === "Receita" ? "text-[#3B6D11]" : "text-[#A32D2D]"
                  }`}
                >
                  ({s.categoriaTipo})
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
