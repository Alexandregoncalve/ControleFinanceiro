/**
 * Tabelas e cálculos tributários — ano-base 2026.
 *
 * IMPORTANTE: estes valores mudam todo ano (geralmente em janeiro, atrelados ao
 * novo salário mínimo). Quando a tabela for atualizada pelo governo, somente
 * este arquivo precisa ser revisado — todo o resto do sistema consome as
 * funções abaixo, não os números brutos.
 *
 * Fontes (consultadas em 2026):
 * - Salário mínimo 2026: R$ 1.621,00
 * - Teto INSS 2026: R$ 8.475,55
 * - DAS MEI: Receita Federal (receita.fazenda.gov.br) — INSS 5% do mínimo + ICMS/ISS fixos
 * - Simples Nacional: Lei Complementar 123/2006, tabela vigente desde 2018 (sem alteração até 2027)
 */

export const SALARIO_MINIMO_2026 = 1621.0;
export const TETO_INSS_2026 = 8475.55;

// ── INSS — Autônomo / Contribuinte Individual ──────────────────────────────

export type PlanoINSS = "simplificado_11" | "normal_20" | "baixa_renda_5";

export const PLANOS_INSS: Record<PlanoINSS, { label: string; aliquota: number; descricao: string }> = {
  simplificado_11: {
    label: "Plano Simplificado (11%)",
    aliquota: 0.11,
    descricao: "11% sobre o salário mínimo. Não dá direito a aposentadoria por tempo de contribuição.",
  },
  normal_20: {
    label: "Plano Normal (20%)",
    aliquota: 0.2,
    descricao: "20% sobre a renda declarada (entre o mínimo e o teto). Dá direito a todos os benefícios.",
  },
  baixa_renda_5: {
    label: "Facultativo Baixa Renda (5%)",
    aliquota: 0.05,
    descricao: "5% sobre o salário mínimo. Exclusivo para quem se enquadra no perfil de baixa renda do CadÚnico.",
  },
};

/** Calcula a contribuição mensal de INSS para autônomo/contribuinte individual. */
export function calcularINSSAutonomo(plano: PlanoINSS, rendaDeclarada: number): number {
  if (plano === "normal_20") {
    const base = Math.min(Math.max(rendaDeclarada, SALARIO_MINIMO_2026), TETO_INSS_2026);
    return Math.round(base * 0.2 * 100) / 100;
  }
  // Planos simplificado e baixa renda incidem sempre sobre o salário mínimo
  return Math.round(SALARIO_MINIMO_2026 * PLANOS_INSS[plano].aliquota * 100) / 100;
}

// ── IRRF — Carnê-leão (tabela progressiva mensal) ──────────────────────────
// Lei 15.270/2025 — isenção ampliada para até R$ 5.000,00/mês a partir de 2026.

interface FaixaIRRF {
  ate: number; // limite superior da faixa (Infinity para a última)
  aliquota: number;
  deducao: number;
}

export const TABELA_IRRF_MENSAL_2026: FaixaIRRF[] = [
  { ate: 5000.0, aliquota: 0, deducao: 0 },
  { ate: 7350.0, aliquota: 0.275, deducao: 1375.0 }, // faixa de transição/desconto progressivo simplificada
  { ate: Infinity, aliquota: 0.275, deducao: 869.36 },
];

/** Calcula o IRRF mensal (carnê-leão) sobre a base de cálculo já líquida de deduções. */
export function calcularIRRFMensal(baseCalculo: number): number {
  if (baseCalculo <= 0) return 0;
  const faixa = TABELA_IRRF_MENSAL_2026.find((f) => baseCalculo <= f.ate) ?? TABELA_IRRF_MENSAL_2026[TABELA_IRRF_MENSAL_2026.length - 1];
  const imposto = baseCalculo * faixa.aliquota - faixa.deducao;
  return Math.max(0, Math.round(imposto * 100) / 100);
}

// ── MEI — DAS fixo mensal ───────────────────────────────────────────────────

export type AtividadeMEI = "comercio" | "servico" | "ambos";

const INSS_MEI = Math.round(SALARIO_MINIMO_2026 * 0.05 * 100) / 100; // R$ 81,05
const ICMS_MEI = 1.0;
const ISS_MEI = 5.0;

export const LIMITE_FATURAMENTO_MEI_ANUAL = 81000.0;

/** Calcula o valor fixo do DAS-MEI mensal, conforme a atividade. */
export function calcularDASMEI(atividade: AtividadeMEI): number {
  if (atividade === "comercio") return Math.round((INSS_MEI + ICMS_MEI) * 100) / 100;
  if (atividade === "servico") return Math.round((INSS_MEI + ISS_MEI) * 100) / 100;
  return Math.round((INSS_MEI + ICMS_MEI + ISS_MEI) * 100) / 100; // ambos
}

// ── Simples Nacional — Anexos I a V ─────────────────────────────────────────

export type AnexoSimples = "I" | "II" | "III" | "IV" | "V";

interface FaixaSimples {
  ate: number;
  aliquota: number;
  deducao: number;
}

export const LIMITE_FATURAMENTO_SIMPLES_ANUAL = 4_800_000.0;

const TABELAS_SIMPLES: Record<AnexoSimples, FaixaSimples[]> = {
  I: [
    { ate: 180_000, aliquota: 0.04, deducao: 0 },
    { ate: 360_000, aliquota: 0.073, deducao: 5_940 },
    { ate: 720_000, aliquota: 0.095, deducao: 13_860 },
    { ate: 1_800_000, aliquota: 0.107, deducao: 22_500 },
    { ate: 3_600_000, aliquota: 0.143, deducao: 87_300 },
    { ate: 4_800_000, aliquota: 0.19, deducao: 378_000 },
  ],
  II: [
    { ate: 180_000, aliquota: 0.045, deducao: 0 },
    { ate: 360_000, aliquota: 0.078, deducao: 5_940 },
    { ate: 720_000, aliquota: 0.1, deducao: 13_860 },
    { ate: 1_800_000, aliquota: 0.112, deducao: 22_500 },
    { ate: 3_600_000, aliquota: 0.147, deducao: 85_500 },
    { ate: 4_800_000, aliquota: 0.3, deducao: 720_000 },
  ],
  III: [
    { ate: 180_000, aliquota: 0.06, deducao: 0 },
    { ate: 360_000, aliquota: 0.112, deducao: 9_360 },
    { ate: 720_000, aliquota: 0.135, deducao: 17_640 },
    { ate: 1_800_000, aliquota: 0.16, deducao: 35_640 },
    { ate: 3_600_000, aliquota: 0.21, deducao: 125_640 },
    { ate: 4_800_000, aliquota: 0.33, deducao: 648_000 },
  ],
  IV: [
    { ate: 180_000, aliquota: 0.045, deducao: 0 },
    { ate: 360_000, aliquota: 0.09, deducao: 8_100 },
    { ate: 720_000, aliquota: 0.102, deducao: 12_420 },
    { ate: 1_800_000, aliquota: 0.14, deducao: 39_780 },
    { ate: 3_600_000, aliquota: 0.22, deducao: 183_780 },
    { ate: 4_800_000, aliquota: 0.33, deducao: 828_000 },
  ],
  V: [
    { ate: 180_000, aliquota: 0.155, deducao: 0 },
    { ate: 360_000, aliquota: 0.18, deducao: 4_500 },
    { ate: 720_000, aliquota: 0.195, deducao: 9_900 },
    { ate: 1_800_000, aliquota: 0.205, deducao: 17_100 },
    { ate: 3_600_000, aliquota: 0.23, deducao: 62_100 },
    { ate: 4_800_000, aliquota: 0.305, deducao: 540_000 },
  ],
};

export const DESCRICAO_ANEXO: Record<AnexoSimples, string> = {
  I: "Comércio (lojas, e-commerce, distribuidoras)",
  II: "Indústria (fábricas, transformação)",
  III: "Serviços com folha alta (contabilidade, agências, academias)",
  IV: "Serviços sem CPP no DAS (advocacia, medicina, limpeza, construção civil)",
  V: "Serviços intelectuais (TI, engenharia, consultoria, publicidade)",
};

/**
 * Calcula a alíquota efetiva do Simples Nacional: (RBT12 × alíquota nominal − dedução) ÷ RBT12.
 * RBT12 = receita bruta acumulada nos últimos 12 meses.
 */
export function calcularAliquotaEfetivaSimples(anexo: AnexoSimples, rbt12: number): number {
  if (rbt12 <= 0) return 0;
  const tabela = TABELAS_SIMPLES[anexo];
  const faixa = tabela.find((f) => rbt12 <= f.ate) ?? tabela[tabela.length - 1];
  const efetiva = (rbt12 * faixa.aliquota - faixa.deducao) / rbt12;
  return Math.max(0, efetiva);
}

/** Calcula o valor do DAS do mês: alíquota efetiva × faturamento do mês. */
export function calcularDASSimplesNacional(anexo: AnexoSimples, rbt12: number, faturamentoMes: number): number {
  const aliquota = calcularAliquotaEfetivaSimples(anexo, rbt12);
  return Math.round(faturamentoMes * aliquota * 100) / 100;
}

/**
 * Fator R: se folha de pagamento (12m) / RBT12 >= 28%, empresas do Anexo V
 * podem ser tributadas pelas alíquotas (menores) do Anexo III.
 */
export function calcularFatorR(folhaPagamento12m: number, rbt12: number): number {
  if (rbt12 <= 0) return 0;
  return folhaPagamento12m / rbt12;
}

export function anexoEfetivoComFatorR(anexoOriginal: AnexoSimples, fatorR: number): AnexoSimples {
  if (anexoOriginal === "V" && fatorR >= 0.28) return "III";
  return anexoOriginal;
}
