import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const pagamentoSchema = z.object({
  dividaId: z.number(),
  valor: z.number().positive("Informe o valor pago."),
  data: z.string().min(1, "Data inválida."),
  observacao: z.string().optional(),
});

/**
 * POST /api/divida-pagamentos
 * Traduzido de registrar_pagamento() em views/dividas.py: registra o pagamento avulso
 * e, se a dívida tiver subconta vinculada, também cria uma transação de despesa no extrato.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = pagamentoSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { dividaId, valor, data, observacao } = parsed.data;

  const divida = await prisma.divida.findFirst({ where: { id: dividaId, usuarioId: sessao.id } });
  if (!divida) return apiErro("Dívida não encontrada.", 404);

  const pagamento = await prisma.$transaction(async (tx: PrismaTransaction) => {
    let transacaoId: number | null = null;

    if (divida.subcontaId) {
      const transacao = await tx.transacao.create({
        data: {
          usuarioId: sessao.id,
          subcontaId: divida.subcontaId,
          tipo: "Despesa",
          valor,
          data,
          descricao: observacao?.trim() || divida.nome,
        },
      });
      transacaoId = transacao.id;
    }

    return tx.dividaPagamento.create({
      data: {
        dividaId,
        usuarioId: sessao.id,
        valor,
        data,
        observacao: observacao?.trim() || null,
        transacaoId,
      },
    });
  });

  return apiOk({ pagamento }, 201);
});
