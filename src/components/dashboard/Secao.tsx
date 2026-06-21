interface SecaoProps {
  titulo: string;
  subtitulo?: string;
  children: React.ReactNode;
  className?: string;
}

/** Traduz a função secao() de views/dashboard.py */
export function Secao({ titulo, subtitulo, children, className = "" }: SecaoProps) {
  return (
    <div className={`rounded-xl border border-[#E8EEF7] bg-white p-3.5 shadow-sm ${className}`}>
      <div className="mb-2 border-b-2 border-[#E3F2FD] pb-2">
        <p className="text-[13px] font-bold text-[#1565C0]">{titulo}</p>
        {subtitulo && <p className="text-[10px] text-gray-400">{subtitulo}</p>}
      </div>
      {children}
    </div>
  );
}
