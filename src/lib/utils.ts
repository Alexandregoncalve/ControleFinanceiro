// Utilitários de formatação — traduzido de utils.py (Python)

/** Formata um número como moeda brasileira: 1234.5 -> "R$ 1.234,50" */
export function fmt(valor: number | null | undefined): string {
  const v = valor ?? 0;
  return `R$ ${v.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/** Formata um número como percentual: 33.456 -> "33.5%" */
export function fmtPct(valor: number): string {
  return `${valor.toFixed(1)}%`;
}

/**
 * Converte uma string de input de usuário em número.
 * Aceita formatos brasileiros: "1.234,56", "1234,56", "1234.56", "1234"
 * Traduzido de limpar_valor() em utils.py
 */
export function limparValor(txt: string | null | undefined): number {
  if (!txt) return 0;
  const limpo = txt.trim().replace("R$", "").trim();
  if (!limpo) return 0;

  try {
    if (limpo.includes(",") && limpo.includes(".")) {
      // "1.234,56" -> remove pontos de milhar, troca vírgula por ponto
      return parseFloat(limpo.replace(/\./g, "").replace(",", ".")) || 0;
    } else if (limpo.includes(",")) {
      // "1234,56" -> troca vírgula por ponto
      return parseFloat(limpo.replace(",", ".")) || 0;
    } else if (limpo.includes(".")) {
      const partes = limpo.split(".");
      if (partes[partes.length - 1].length === 2) {
        // "1234.56" -> já é decimal válido
        return parseFloat(limpo) || 0;
      } else {
        // "1.234" -> ponto é separador de milhar
        return parseFloat(limpo.replace(/\./g, "")) || 0;
      }
    } else {
      return parseFloat(limpo) || 0;
    }
  } catch {
    return 0;
  }
}

/** Formata um número para exibição em campo de input de moeda: 1234.5 -> "1.234,50" */
export function formatarMoedaInput(valor: number): string {
  return valor.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Retorna a string do mês atual no formato MM/AAAA, igual ao Python */
export function mesAtual(): string {
  const hoje = new Date();
  const mes = String(hoje.getMonth() + 1).padStart(2, "0");
  return `${mes}/${hoje.getFullYear()}`;
}

/** Dado "MM/AAAA", retorna o mês anterior no mesmo formato */
export function mesAnterior(mesStr: string): string {
  const [m, a] = mesStr.split("/").map(Number);
  let novoMes = m - 1;
  let novoAno = a;
  if (novoMes === 0) {
    novoMes = 12;
    novoAno -= 1;
  }
  return `${String(novoMes).padStart(2, "0")}/${novoAno}`;
}

/** Dado "MM/AAAA", retorna o mês seguinte no mesmo formato */
export function mesSeguinte(mesStr: string): string {
  const [m, a] = mesStr.split("/").map(Number);
  let novoMes = m + 1;
  let novoAno = a;
  if (novoMes === 13) {
    novoMes = 1;
    novoAno += 1;
  }
  return `${String(novoMes).padStart(2, "0")}/${novoAno}`;
}

/** Compara cronologicamente duas strings "MM/AAAA" (para sort) */
export function compararMes(a: string, b: string): number {
  const [ma, aa] = a.split("/").map(Number);
  const [mb, ab] = b.split("/").map(Number);
  if (aa !== ab) return aa - ab;
  return ma - mb;
}

/** Converte "DD/MM/AAAA" em objeto Date (assume meio-dia para evitar problemas de fuso) */
export function parseDataBR(dataStr: string): Date {
  const [d, m, a] = dataStr.split("/").map(Number);
  return new Date(a, m - 1, d, 12, 0, 0);
}

/** Converte Date em string "DD/MM/AAAA" */
export function formatarDataBR(date: Date): string {
  const d = String(date.getDate()).padStart(2, "0");
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const a = date.getFullYear();
  return `${d}/${m}/${a}`;
}

/** Retorna quantos dias tem um mês (1-12) em um determinado ano */
export function diasNoMes(mes: number, ano: number): number {
  return new Date(ano, mes, 0).getDate();
}

/**
 * Calcula o 5º dia útil do mês seguinte a partir de um mês/ano de referência —
 * o prazo legal máximo de pagamento de salário (CLT art. 459, §1º).
 * Sábado conta como dia útil (Instrução Normativa 01/1989); domingo não.
 * Não considera feriados nacionais/locais (variam por município), só fins de semana.
 */
export function calcular5DiaUtilMesSeguinte(mesRef: number, anoRef: number): number {
  let mes = mesRef + 1;
  let ano = anoRef;
  if (mes > 12) {
    mes = 1;
    ano += 1;
  }

  let diaUtil = 0;
  let dia = 1;
  while (diaUtil < 5) {
    const data = new Date(ano, mes - 1, dia);
    const diaSemana = data.getDay(); // 0 = domingo
    if (diaSemana !== 0) diaUtil++;
    if (diaUtil === 5) return dia;
    dia++;
  }
  return dia;
}

/** Valida CPF — traduzido de validar_cpf() em cadastro.py */
export function validarCPF(cpfStr: string): boolean {
  const cpf = cpfStr.replace(/\D/g, "");
  if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) return false;

  for (let i = 9; i <= 10; i++) {
    let soma = 0;
    for (let n = 0; n < i; n++) {
      soma += parseInt(cpf[n]) * (i + 1 - n);
    }
    const digito = ((soma * 10) % 11) % 10;
    if (parseInt(cpf[i]) !== digito) return false;
  }
  return true;
}
