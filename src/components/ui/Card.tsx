interface CardProps {
  children: React.ReactNode;
  className?: string;
  titulo?: string;
  subtitulo?: string;
}

/** Card base padronizado: fundo branco, borda sutil, sombra leve, radius consistente. */
export function Card({ children, className = "", titulo, subtitulo }: CardProps) {
  return (
    <div className={`rounded-xl border border-[#E2E8F0] bg-white p-4 shadow-sm ${className}`}>
      {titulo && (
        <div className="mb-3 border-b-2 border-[#E6F1FB] pb-2">
          <p className="text-sm font-bold text-[#0C447C]">{titulo}</p>
          {subtitulo && <p className="text-[11px] text-[#64748B]">{subtitulo}</p>}
        </div>
      )}
      {children}
    </div>
  );
}
