import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

/**
 * DELETE /api/divida-pagamentos/[id]
 * Traduzido de make_fn()/excluir pagamento em views/dividas.py: remove o pagamento
 * e, se houver, a transação espelho criada no extrato.
 */
export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const pid = Number(id);

    const pagamento = await prisma.dividaPagamento.findFirst({
      where: { id: pid, usuarioId: sessao.id },
    });
    if (!pagamento) return apiErro("Pagamento não encontrado.", 404);

    await prisma.$transaction(async (tx: PrismaTransaction) => {
      if (pagamento.transacaoId) {
        await tx.transacao.deleteMany({ where: { id: pagamento.transacaoId, usuarioId: sessao.id } });
      }
      await tx.dividaPagamento.delete({ where: { id: pid } });
    });

    return apiOk({ ok: true });
  }
);
