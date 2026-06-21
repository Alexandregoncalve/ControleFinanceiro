import { NextResponse } from "next/server";

export function apiOk<T>(data: T, status = 200) {
  return NextResponse.json(data, { status });
}

export function apiErro(mensagem: string, status = 400) {
  return NextResponse.json({ erro: mensagem }, { status });
}

/**
 * Envolve um handler de rota para capturar erros de forma padronizada,
 * incluindo o caso especial de sessão ausente (lançado por exigirSessao()).
 */
export function comTratamentoErro<T extends unknown[]>(
  handler: (...args: T) => Promise<Response>
) {
  return async (...args: T): Promise<Response> => {
    try {
      return await handler(...args);
    } catch (ex) {
      if (ex instanceof Error && ex.message === "UNAUTHENTICATED") {
        return apiErro("Não autenticado.", 401);
      }
      console.error("[API erro]", ex);
      return apiErro("Erro interno do servidor.", 500);
    }
  };
}
