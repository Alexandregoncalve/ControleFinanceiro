import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const transacaoUpdateSchema = z.object({
  data: z.string().min(1),
  valor: z.number().positive(),
  descricao: z.string().optional(),
  subcontaId: z.number(),
  bancoId: z.number().nullable().optional(),
  categoriaRealId: z.number().nullable().optional(),
});

export const PUT = comTratamentoErro(
  async (req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const body = await req.json();
    const parsed = transacaoUpdateSchema.safeParse(body);

    if (!parsed.success) return apiErro(parsed.error.issues[0].message);

    const subconta = await prisma.subconta.findFirst({
      where: { id: parsed.data.subcontaId, usuarioId: sessao.id },
      include: { categoria: { select: { tipo: true } } },
    });
    if (!subconta) return apiErro("Subconta não encontrada.", 404);

    const resultado = await prisma.transacao.updateMany({
      where: { id: Number(id), usuarioId: sessao.id },
      data: { ...parsed.data, tipo: subconta.categoria.tipo },
    });

    if (resultado.count === 0) return apiErro("Transação não encontrada.", 404);
    return apiOk({ ok: true });
  }
);

export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;

    const resultado = await prisma.transacao.deleteMany({
      where: { id: Number(id), usuarioId: sessao.id },
    });

    if (resultado.count === 0) return apiErro("Transação não encontrada.", 404);
    return apiOk({ ok: true });
  }
);
