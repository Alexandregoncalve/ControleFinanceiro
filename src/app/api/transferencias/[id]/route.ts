import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

// Traduzido de excluir_transferencia() em views/bancos.py:
// remove a transferência E as duas transações espelho criadas junto com ela.
export const DELETE = comTratamentoErro(
  async (_req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const tid = Number(id);

    const t = await prisma.transferencia.findFirst({
      where: { id: tid, usuarioId: sessao.id },
    });
    if (!t) return apiErro("Transferência não encontrada.", 404);

    await prisma.$transaction(async (tx: PrismaTransaction) => {
      await tx.transacao.deleteMany({
        where: {
          usuarioId: sessao.id,
          bancoId: t.bancoOrig,
          tipo: "Despesa",
          data: t.data,
          valor: t.valor,
          descricao: { contains: "Transf." },
        },
      });
      await tx.transacao.deleteMany({
        where: {
          usuarioId: sessao.id,
          bancoId: t.bancoDest,
          tipo: "Receita",
          data: t.data,
          valor: t.valor,
          descricao: { contains: "Transf." },
        },
      });
      await tx.transferencia.delete({ where: { id: tid } });
    });

    return apiOk({ ok: true });
  }
);

const transferenciaUpdateSchema = z.object({
  data: z.string().min(1),
  valor: z.number().positive(),
  bancoOrig: z.number(),
  bancoDest: z.number(),
  descricao: z.string().optional(),
});

export const PUT = comTratamentoErro(
  async (req: NextRequest, { params }: { params: Promise<{ id: string }> }) => {
    const sessao = await exigirSessao();
    const { id } = await params;
    const tid = Number(id);
    const body = await req.json();
    const parsed = transferenciaUpdateSchema.safeParse(body);

    if (!parsed.success) return apiErro(parsed.error.issues[0].message);

    const old = await prisma.transferencia.findFirst({ where: { id: tid, usuarioId: sessao.id } });
    if (!old) return apiErro("Transferência não encontrada.", 404);

    const { data, valor, bancoOrig, bancoDest, descricao } = parsed.data;
    const desc = descricao?.trim() || "Transferência entre bancos";

    const [origem, destino] = await Promise.all([
      prisma.banco.findFirst({ where: { id: bancoOrig, usuarioId: sessao.id } }),
      prisma.banco.findFirst({ where: { id: bancoDest, usuarioId: sessao.id } }),
    ]);
    if (!origem || !destino) return apiErro("Banco inválido.", 404);

    await prisma.$transaction(async (tx: PrismaTransaction) => {
      // Remove transações antigas espelho
      await tx.transacao.deleteMany({
        where: {
          usuarioId: sessao.id,
          bancoId: old.bancoOrig,
          tipo: "Despesa",
          data: old.data,
          valor: old.valor,
          descricao: { contains: "Transf." },
        },
      });
      await tx.transacao.deleteMany({
        where: {
          usuarioId: sessao.id,
          bancoId: old.bancoDest,
          tipo: "Receita",
          data: old.data,
          valor: old.valor,
          descricao: { contains: "Transf." },
        },
      });

      await tx.transferencia.update({
        where: { id: tid },
        data: { data, valor, bancoOrig, bancoDest, descricao: desc },
      });

      const subconta = await tx.subconta.findFirst({
        where: { usuarioId: sessao.id, nome: { contains: "TRANSFER", mode: "insensitive" } },
      });
      const fallback = subconta ?? (await tx.subconta.findFirst({ where: { usuarioId: sessao.id } }));

      if (fallback) {
        await tx.transacao.create({
          data: {
            usuarioId: sessao.id,
            data,
            valor,
            subcontaId: fallback.id,
            tipo: "Despesa",
            descricao: `Transf. → ${destino.nomeBanco} | ${desc}`,
            bancoId: bancoOrig,
          },
        });
        await tx.transacao.create({
          data: {
            usuarioId: sessao.id,
            data,
            valor,
            subcontaId: fallback.id,
            tipo: "Receita",
            descricao: `Transf. ← ${origem.nomeBanco} | ${desc}`,
            bancoId: bancoDest,
          },
        });
      }
    });

    return apiOk({ ok: true });
  }
);
