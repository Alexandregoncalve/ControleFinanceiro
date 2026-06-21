import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

/**
 * DELETE /api/dividas/[id]
 * Traduzido de on_excluir() em views/dividas.py: remove a dívida e desvincula
 * (sem excluir) a subconta fixa associada, caso exista.
 */
export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const did = Number(id);

    const divida = await prisma.divida.findFirst({ where: { id: did, usuarioId: sessao.id } });
    if (!divida) return apiErro("Dívida não encontrada.", 404);

    await prisma.$transaction(async (tx: PrismaTransaction) => {
      if (divida.subcontaId) {
        await tx.subconta.update({
          where: { id: divida.subcontaId },
          data: { fixa: 0 },
        });
      }
      await tx.divida.delete({ where: { id: did } });
    });

    return apiOk({ ok: true });
  }
);
