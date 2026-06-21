export interface DashboardData {
  mes: string;
  resumo: {
    receitas: number;
    despesas: number;
    resultado: number;
    receitasAnterior: number;
    despesasAnterior: number;
    resultadoAnterior: number;
    metaReceita: number;
    metaDespesa: number;
    metaResultado: number;
    metaCopiada: boolean;
  };
  saldoAcumulado: number;
  bancos: {
    id: number;
    nomeBanco: string;
    saldoInicial: number;
    saldoAtual: number;
    agencia: string | null;
    numeroConta: string | null;
  }[];
  cartao: { total: number; percentualDespesas: number };
  fixas: {
    valor: number;
    valorAnterior: number;
    percentualDespesas: number;
    totalContas: number;
    pendentes: number;
    lancadas: number;
  };
  saude: {
    score: number;
    label: "BOA" | "REGULAR" | "ATENÇÃO";
    indicadores: {
      poupanca: number;
      orcamento: number;
      fixasPagas: number;
      rendaLivre: number;
    };
  };
  gastos: { nome: string; total: number }[];
  orcamentos: { nome: string; total: number; orcamento: number }[];
  historico: { mes: string; receita: number; despesa: number; ehAtual: boolean }[];
  diasRestantes: number;
}
