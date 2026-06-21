import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const subcontaUpdateSchema = z.object({
  categoriaId: z.number(),
  nome: z.string().min(1),
  fixa: z.boolean(),
  orcamento: z.number(),
  diaVencimento: z.number().nullable().optional(),
});

export const PUT = comTratamentoErro(
  async (req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const body = await req.json();
    const parsed = subcontaUpdateSchema.safeParse(body);

    if (!parsed.success) return apiErro(parsed.error.issues[0].message);

    const resultado = await prisma.subconta.updateMany({
      where: { id: Number(id), usuarioId: sessao.id },
      data: {
        categoriaId: parsed.data.categoriaId,
        nome: parsed.data.nome.trim().toUpperCase(),
        fixa: parsed.data.fixa ? 1 : 0,
        orcamento: parsed.data.orcamento,
        diaVencimento: parsed.data.diaVencimento ?? null,
      },
    });

    if (resultado.count === 0) return apiErro("Subconta não encontrada.", 404);
    return apiOk({ ok: true });
  }
);

export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;

    const resultado = await prisma.subconta.deleteMany({
      where: { id: Number(id), usuarioId: sessao.id },
    });

    if (resultado.count === 0) return apiErro("Subconta não encontrada.", 404);
    return apiOk({ ok: true });
  }
);
