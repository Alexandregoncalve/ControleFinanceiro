// Tipos compartilhados entre API e componentes — espelham o schema Prisma

export interface BancoDTO {
  id: number;
  nomeBanco: string;
  saldoInicial: number;
  dataCriacao: string | null;
  agencia: string | null;
  numeroConta: string | null;
  codigoBanco: string | null;
  saldoAtual?: number; // calculado: saldoInicial + receitas - despesas
}

export interface CartaoDTO {
  id: number;
  nomeCartao: string;
  limite: number;
  diaVencimento: number | null;
  bancoId: number | null;
  bancoNome?: string | null;
  tipo: string | null;
}

export interface CategoriaDTO {
  id: number;
  nome: string;
  tipo: "Receita" | "Despesa";
}

export interface SubcontaDTO {
  id: number;
  categoriaId: number;
  nome: string;
  fixa: number;
  orcamento: number;
  diaVencimento: number | null;
  categoriaNome?: string;
  categoriaTipo?: "Receita" | "Despesa";
}

export interface TransacaoDTO {
  id: number;
  data: string;
  valor: number;
  descricao: string | null;
  subcontaId: number;
  subcontaNome?: string;
  tipo: "Receita" | "Despesa";
  metodoPagamento: string | null;
  cartaoId: number | null;
  parcelaAtual: number;
  totalParcelas: number;
  categoriaRealId: number | null;
  categoriaRealNome?: string | null;
  bancoId: number | null;
  bancoNome?: string | null;
}

export interface MetaDTO {
  id: number;
  mes: string;
  metaReceita: number;
  metaDespesa: number;
  metaResultado: number;
}

export interface TransferenciaDTO {
  id: number;
  data: string;
  valor: number;
  bancoOrig: number;
  bancoDest: number;
  bancoOrigNome?: string;
  bancoDestNome?: string;
  descricao: string | null;
}
