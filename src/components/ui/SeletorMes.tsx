"use client";

interface SeletorMesProps {
  mes: string; // "MM/AAAA"
  onChange: (mes: string) => void;
}

/** Gera os últimos 12 meses a partir do mês atual, mais recente primeiro */
function gerarOpcoesMeses(): string[] {
  const hoje = new Date();
  const opcoes: string[] = [];
  let m = hoje.getMonth() + 1;
  let a = hoje.getFullYear();
  for (let i = 0; i < 24; i++) {
    opcoes.push(`${String(m).padStart(2, "0")}/${a}`);
    m -= 1;
    if (m === 0) {
      m = 12;
      a -= 1;
    }
  }
  return opcoes;
}

export function SeletorMes({ mes, onChange }: SeletorMesProps) {
  const opcoes = gerarOpcoesMeses();

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px] text-gray-400">Período:</span>
      <select
        value={mes}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs font-medium text-gray-700 outline-none focus:border-[#1565C0]"
      >
        {opcoes.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}
