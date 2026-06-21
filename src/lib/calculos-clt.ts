/**
 * Cálculos de benefícios CLT.
 *
 * Vale-transporte: Lei 7.418/1985, art. 4º — desconto máximo de 6% do salário
 * básico do empregado. Se o usuário não informar o custo real do transporte,
 * assumimos o desconto no teto legal de 6% (cenário mais comum na prática).
 *
 * Prazo de pagamento de salário: CLT art. 459, §1º — até o 5º dia útil do mês
 * subsequente ao trabalhado (sábado conta como dia útil, domingo não).
 */

export const PERCENTUAL_VALE_TRANSPORTE = 0.06; // 6% — teto legal, Lei 7.418/85
export const PERCENTUAL_ADIANTAMENTO_SUGERIDO = 0.4; // 40% — sugestão comum de mercado, NÃO é lei

/** Calcula o desconto de vale-transporte sobre o salário base (teto legal de 6%). */
export function calcularDescontoValeTransporte(salarioBase: number): number {
  if (salarioBase <= 0) return 0;
  return Math.round(salarioBase * PERCENTUAL_VALE_TRANSPORTE * 100) / 100;
}

/** Calcula o valor sugerido de adiantamento salarial (sugestão de 40%, editável pelo usuário). */
export function calcularAdiantamentoSugerido(salarioBase: number): number {
  if (salarioBase <= 0) return 0;
  return Math.round(salarioBase * PERCENTUAL_ADIANTAMENTO_SUGERIDO * 100) / 100;
}
