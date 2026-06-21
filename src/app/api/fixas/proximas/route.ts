import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";
import { mesAtual } from "@/lib/utils";

/**
 * GET /api/fixas/proximas?dias=1
 * Lista contas fixas com dia_vencimento dentro da janela de antecedência informada
 * (padrão: amanhã) que AINDA NÃO foram lançadas no mês corrente.
 * Usado pelo modal de aviso ao logar.
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);
  const diasAntecedencia = Number(searchParams.get("dias") || 1);

  const mes = mesAtual();
  const hoje = new Date();
  const diaHoje = hoje.getDate();

  const todasFixas = await prisma.subconta.findMany({
    where: { usuarioId: sessao.id, fixa: 1, diaVencimento: { not: null } },
    orderBy: { diaVencimento: "asc" },
  });

  const transacoesDoMes = await prisma.transacao.findMany({
    where: { usuarioId: sessao.id, data: { endsWith: `/${mes}` } },
    select: { subcontaId: true },
  });
  const jaLancadas = new Set(transacoesDoMes.map((t: { subcontaId: number }) => t.subcontaId));

  const proximas = todasFixas.filter((s: { id: number; diaVencimento: number | null }) => {
    if (jaLancadas.has(s.id)) return false;
    if (s.diaVencimento === null) return false;
    const diff = s.diaVencimento - diaHoje;
    return diff >= 0 && diff <= diasAntecedencia;
  });

  return apiOk({ proximas, mes });
});
