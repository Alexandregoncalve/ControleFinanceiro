import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const bancoUpdateSchema = z.object({
  nomeBanco: z.string().min(1),
  codigoBanco: z.string().optional().nullable(),
  agencia: z.string().optional().nullable(),
  numeroConta: z.string().optional().nullable(),
  saldoInicial: z.number(),
  dataCriacao: z.string().optional().nullable(),
});

export const PUT = comTratamentoErro(
  async (req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const body = await req.json();
    const parsed = bancoUpdateSchema.safeParse(body);

    if (!parsed.success) {
      return apiErro(parsed.error.issues[0].message);
    }

    const banco = await prisma.banco.updateMany({
      where: { id: Number(id), usuarioId: sessao.id },
      data: parsed.data,
    });

    if (banco.count === 0) return apiErro("Banco não encontrado.", 404);
    return apiOk({ ok: true });
  }
);

// Traduzido de excluir_banco() em views/bancos.py
export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;

    const resultado = await prisma.banco.deleteMany({
      where: { id: Number(id), usuarioId: sessao.id },
    });

    if (resultado.count === 0) return apiErro("Banco não encontrado.", 404);
    return apiOk({ ok: true });
  }
);
