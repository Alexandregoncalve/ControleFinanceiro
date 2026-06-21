import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { formatarDataBR } from "@/lib/utils";

/** POST /api/dividas/[id]/quitar — traduzido de on_quitar() em views/dividas.py */
export const POST = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const did = Number(id);

    const divida = await prisma.divida.findFirst({ where: { id: did, usuarioId: sessao.id } });
    if (!divida) return apiErro("Dívida não encontrada.", 404);

    await prisma.$transaction(async (tx: PrismaTransaction) => {
      await tx.divida.update({
        where: { id: did },
        data: { status: "quitada", dataQuitacao: formatarDataBR(new Date()) },
      });
      if (divida.subcontaId) {
        await tx.subconta.update({ where: { id: divida.subcontaId }, data: { fixa: 0 } });
      }
    });

    return apiOk({ ok: true });
  }
);
