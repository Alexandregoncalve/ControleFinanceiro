import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const categoriaUpdateSchema = z.object({
  nome: z.string().min(1, "Informe o nome da conta pai."),
  tipo: z.enum(["Receita", "Despesa"]),
});

export const PUT = comTratamentoErro(
  async (req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const body = await req.json();
    const parsed = categoriaUpdateSchema.safeParse(body);

    if (!parsed.success) return apiErro(parsed.error.issues[0].message);

    const resultado = await prisma.categoria.updateMany({
      where: { id: Number(id), usuarioId: sessao.id },
      data: {
        nome: parsed.data.nome.trim().toUpperCase(),
        tipo: parsed.data.tipo,
      },
    });

    if (resultado.count === 0) return apiErro("Conta pai não encontrada.", 404);
    return apiOk({ ok: true });
  }
);

/**
 * Impede excluir uma categoria que ainda tem subcontas vinculadas — evita deixar
 * lançamentos órfãos. O usuário precisa mover/excluir as subcontas primeiro.
 */
export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const cid = Number(id);

    const categoria = await prisma.categoria.findFirst({ where: { id: cid, usuarioId: sessao.id } });
    if (!categoria) return apiErro("Conta pai não encontrada.", 404);

    const qtdSubcontas = await prisma.subconta.count({ where: { categoriaId: cid, usuarioId: sessao.id } });
    if (qtdSubcontas > 0) {
      return apiErro(
        `Esta conta pai tem ${qtdSubcontas} subconta(s) vinculada(s). Exclua ou mova-as antes de excluir a conta pai.`,
        400
      );
    }

    await prisma.categoria.delete({ where: { id: cid } });
    return apiOk({ ok: true });
  }
);
