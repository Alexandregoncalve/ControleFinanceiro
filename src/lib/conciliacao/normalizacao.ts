/**
 * Utilitários de normalização de dados para o parser de conciliação.
 * Centraliza a conversão de formatos variados de data e valor em
 * formatos padronizados usados pelo sistema.
 */

/**
 * Tenta interpretar uma string de data em qualquer dos formatos comuns
 * usados em extratos bancários brasileiros e retorna DD/MM/AAAA.
 * Retorna null se não conseguir interpretar.
 */
export function normalizarData(texto: string): string | null {
  if (!texto) return null;
  const s = texto.trim().replace(/['"]/g, "");

  // DD/MM/AAAA ou DD-MM-AAAA
  const m1 = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
  if (m1) {
    const [, d, mo, a] = m1;
    if (Number(mo) >= 1 && Number(mo) <= 12 && Number(d) >= 1 && Number(d) <= 31) {
      return `${d.padStart(2, "0")}/${mo.padStart(2, "0")}/${a}`;
    }
  }

  // AAAA/MM/DD ou AAAA-MM-DD (ISO)
  const m2 = s.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$/);
  if (m2) {
    const [, a, mo, d] = m2;
    if (Number(mo) >= 1 && Number(mo) <= 12 && Number(d) >= 1 && Number(d) <= 31) {
      return `${d.padStart(2, "0")}/${mo.padStart(2, "0")}/${a}`;
    }
  }

  // DDMMAAAA (sem separador — comum em alguns extratos)
  const m3 = s.match(/^(\d{2})(\d{2})(\d{4})$/);
  if (m3) {
    const [, d, mo, a] = m3;
    if (Number(mo) >= 1 && Number(mo) <= 12 && Number(d) >= 1 && Number(d) <= 31) {
      return `${d}/${mo}/${a}`;
    }
  }

  // DD/MM/AA (ano com 2 dígitos)
  const m4 = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2})$/);
  if (m4) {
    const [, d, mo, aa] = m4;
    const a = Number(aa) >= 50 ? `19${aa}` : `20${aa}`;
    if (Number(mo) >= 1 && Number(mo) <= 12 && Number(d) >= 1 && Number(d) <= 31) {
      return `${d.padStart(2, "0")}/${mo.padStart(2, "0")}/${a}`;
    }
  }

  return null;
}

/**
 * Tenta interpretar um valor monetário de string para número.
 * Suporta formatos brasileiros (1.234,56) e americanos (1,234.56),
 * além de valores com sinais negativos ou entre parênteses.
 */
export function normalizarValor(texto: string): number | null {
  if (!texto || texto.trim() === "" || texto.trim() === "-") return null;

  let s = texto
    .trim()
    .replace(/[R$\s'"]/g, "")  // remove R$, espaços, aspas
    .replace(/\(([^)]+)\)/, "-$1"); // (123,45) -> -123,45

  const negativo = s.startsWith("-");
  s = s.replace(/^-/, "");

  let numero: number;

  // Formato brasileiro: 1.234,56
  if (/^\d{1,3}(\.\d{3})*(,\d+)?$/.test(s)) {
    numero = parseFloat(s.replace(/\./g, "").replace(",", "."));
  }
  // Formato americano: 1,234.56
  else if (/^\d{1,3}(,\d{3})*(\.\d+)?$/.test(s)) {
    numero = parseFloat(s.replace(/,/g, ""));
  }
  // Só dígitos e vírgula: 1234,56
  else if (/^\d+(,\d+)?$/.test(s)) {
    numero = parseFloat(s.replace(",", "."));
  }
  // Só dígitos e ponto: 1234.56
  else if (/^\d+(\.\d+)?$/.test(s)) {
    numero = parseFloat(s);
  } else {
    return null;
  }

  if (isNaN(numero)) return null;
  return negativo ? -numero : numero;
}

/**
 * Detecta se uma coluna representa débito ou crédito pelo conteúdo.
 * Retorna "Despesa", "Receita" ou null se não conseguir detectar.
 */
export function detectarTipoPeloConteudo(texto: string): "Receita" | "Despesa" | null {
  const s = texto.trim().toUpperCase();
  if (["D", "DEB", "DEBITO", "DÉBITO", "SAIDA", "SAÍDA", "OUT"].includes(s)) return "Despesa";
  if (["C", "CRE", "CREDITO", "CRÉDITO", "ENTRADA", "IN"].includes(s)) return "Receita";
  return null;
}

/**
 * Compara dois strings ignorando acentos e maiúsculas.
 * Usada para detectar nomes de colunas.
 */
export function pareceCom(texto: string, padroes: string[]): boolean {
  const normalizado = texto
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
  return padroes.some((p) => normalizado.includes(p));
}
