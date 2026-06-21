/**
 * Estrutura do campo `detalhes` (JSON) do VinculoRenda, variando por tipo.
 */

// ── CLT ──────────────────────────────────────────────────────────────────
export interface DetalhesCLT {
  empresa: string;
  cargo: string;
  salarioBruto: number;
  diaPagamento: number | null; // se null, assume o 5º dia útil legal calculado dinamicamente

  recebeValeTransporte: boolean;
  recebeValeAlimentacao: boolean;
  valorValeAlimentacao: number;

  recebeAdiantamento: boolean;
  percentualAdiantamento: number;
  diaAdiantamento: number | null;
}

export const DETALHES_CLT_VAZIO: DetalhesCLT = {
  empresa: "",
  cargo: "",
  salarioBruto: 0,
  diaPagamento: null,
  recebeValeTransporte: false,
  recebeValeAlimentacao: false,
  valorValeAlimentacao: 0,
  recebeAdiantamento: false,
  percentualAdiantamento: 40,
  diaAdiantamento: null,
};

// ── AUTÔNOMO ─────────────────────────────────────────────────────────────
export interface DetalhesAutonomo {
  atividade: string; // descrição livre: "Designer", "Consultor", etc.
  rendaMediaMensal: number; // estimativa, usada só de referência (renda real varia mês a mês)
  planoINSS: "simplificado_11" | "normal_20" | "baixa_renda_5";
  prestaServicoPJ: boolean; // se true, parte do INSS pode já vir retida na fonte pelo contratante
}

export const DETALHES_AUTONOMO_VAZIO: DetalhesAutonomo = {
  atividade: "",
  rendaMediaMensal: 0,
  planoINSS: "simplificado_11",
  prestaServicoPJ: false,
};

// ── MEI ──────────────────────────────────────────────────────────────────
export interface DetalhesMEI {
  nomeFantasia: string;
  cnpj: string;
  atividade: "comercio" | "servico" | "ambos";
  faturamentoMedioMensal: number; // para alertar sobre o limite anual de R$ 81.000
  diaVencimentoDAS: number; // padrão 20, fixo por lei
}

export const DETALHES_MEI_VAZIO: DetalhesMEI = {
  nomeFantasia: "",
  cnpj: "",
  atividade: "servico",
  faturamentoMedioMensal: 0,
  diaVencimentoDAS: 20,
};

// ── SIMPLES NACIONAL (ME / EPP) ──────────────────────────────────────────
export interface DetalhesSimplesNacional {
  razaoSocial: string;
  cnpj: string;
  anexo: "I" | "II" | "III" | "IV" | "V";
  faturamento12meses: number; // RBT12 — base para calcular a alíquota efetiva
  faturamentoMedioMensal: number;
  folhaPagamento12meses: number; // usado para o Fator R (só relevante no Anexo V)
  diaVencimentoDAS: number; // padrão dia 20
}

export const DETALHES_SIMPLES_VAZIO: DetalhesSimplesNacional = {
  razaoSocial: "",
  cnpj: "",
  anexo: "III",
  faturamento12meses: 0,
  faturamentoMedioMensal: 0,
  folhaPagamento12meses: 0,
  diaVencimentoDAS: 20,
};

export type TipoVinculo = "CLT" | "AUTONOMO" | "MEI" | "SIMPLES_NACIONAL";

export type DetalhesVinculo = DetalhesCLT | DetalhesAutonomo | DetalhesMEI | DetalhesSimplesNacional;

export interface VinculoRendaDTO {
  id: number;
  tipo: TipoVinculo;
  apelido: string;
  ativo: boolean;
  detalhes: DetalhesVinculo;
  criadoEm: string;
}
