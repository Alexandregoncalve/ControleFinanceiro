/**
 * Tipos compartilhados do módulo de conciliação bancária.
 * Usados tanto pelo backend (parsers) quanto pelo frontend (wizard de importação).
 */

/** Uma linha de extrato como o sistema a enxerga após o parsing */
export interface LinhaExtrato {
  /** Linha original do arquivo — usada para depuração e exibição na prévia */
  linhaOriginal: string;
  /** Data no formato DD/MM/AAAA (após normalização) */
  data: string;
  /** Descrição/histórico da transação */
  descricao: string;
  /** Valor em reais (sempre positivo — o tipo determina se é receita ou despesa) */
  valor: number;
  /** "Receita" ou "Despesa" — detectado pelo sinal ou coluna de tipo */
  tipo: "Receita" | "Despesa";
  /** Se verdadeiro, o usuário selecionou para importar (padrão: true) */
  selecionada: boolean;
  /** Índice da linha no arquivo original */
  indice: number;
}

/** Mapeamento de colunas detectado/configurado pelo usuário */
export interface MapeamentoColunas {
  /** Índice da coluna de data (0-based) */
  data: number | null;
  /** Índice da coluna de descrição */
  descricao: number | null;
  /** Índice da coluna de valor único (quando débito e crédito estão juntos) */
  valor: number | null;
  /** Índice da coluna de débito (quando separados) */
  debito: number | null;
  /** Índice da coluna de crédito (quando separados) */
  credito: number | null;
  /** Índice da coluna de tipo (ex: "D"/"C", "Débito"/"Crédito") */
  tipo: number | null;
}

/** Resultado do parsing de um arquivo */
export interface ResultadoParsing {
  /** As linhas detectadas */
  linhas: LinhaExtrato[];
  /** Mapeamento de colunas usado (para o usuário confirmar/ajustar) */
  mapeamento: MapeamentoColunas;
  /** Headers detectados (primeiras linhas do arquivo) */
  headers: string[];
  /** Todas as linhas brutas (para o usuário ver e corrigir o mapeamento) */
  linhasBrutas: string[][];
  /** Avisos do parser (ex: "3 linhas ignoradas por data inválida") */
  avisos: string[];
  /** Formato detectado */
  formato: "csv" | "xlsx" | "pdf";
  /** Banco detectado automaticamente */
  bancoDetectado?: string;
  /** ID do banco cadastrado que corresponde ao extrato */
  bancoId?: number | null;
  /** Nome do banco detectado */
  bancoNome?: string | null;
}

/** Padrões conhecidos de extrato bancário para detecção automática de colunas */
export const PADROES_COLUNA = {
  data: [
    "data", "date", "dt", "vencimento", "lançamento", "lancamento", "competencia",
    "movimentação", "movimentacao", "liquidação", "liquidacao", "mov", "liq",
  ],
  descricao: [
    "descricao", "descrição", "historico", "histórico", "memo",
    "description", "detalhe", "complemento", "favorecido", "beneficiario",
    "lançamento", "lancamento", "histórico", "historico",
  ],
  valor: [
    "valor", "value", "amount", "montante", "quantia",
    "valor (r$)", "valor r$", "vlr", "vl",
  ],
  debito: ["debito", "débito", "saida", "saída", "debit", "valor debito", "valor débito"],
  credito: ["credito", "crédito", "entrada", "credit", "valor credito", "valor crédito"],
  tipo: ["tipo", "natureza", "dc", "d/c", "type"],
};
