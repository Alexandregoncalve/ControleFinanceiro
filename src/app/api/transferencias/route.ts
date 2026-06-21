import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();

  const transferencias = await prisma.transferencia.findMany({
    where: { usuarioId: sessao.id },
    include: {
      bancoOrigem: { select: { nomeBanco: true } },
      bancoDestino: { select: { nomeBanco: true } },
    },
    orderBy: [{ data: "desc" }, { id: "desc" }],
    take: 30,
  });

  const resultado = transferencias.map((t: (typeof transferencias)[number]) => ({
    id: t.id,
    data: t.data,
    valor: t.valor,
    bancoOrig: t.bancoOrig,
    bancoDest: t.bancoDest,
    bancoOrigNome: t.bancoOrigem.nomeBanco,
    bancoDestNome: t.bancoDestino.nomeBanco,
    descricao: t.descricao,
  }));

  return apiOk({ transferencias: resultado });
});

const transferenciaSchema = z
  .object({
    data: z.string().min(1),
    valor: z.number().positive("Informe um valor válido."),
    bancoOrig: z.number(),
    bancoDest: z.number(),
    descricao: z.string().optional(),
  })
  .refine((d) => d.bancoOrig !== d.bancoDest, {
    message: "Origem e destino não podem ser iguais.",
  });

/**
 * Traduzido de realizar_transferencia() em views/bancos.py.
 * Cria o registro de transferência E as duas transações espelho (despesa na origem,
 * receita no destino), usando uma subconta "TRANSFERÊNCIAS" — igual à lógica Python
 * que busca (ou usa fallback de) uma subconta com "TRANSFER" no nome.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = transferenciaSchema.safeParse(body);

  if (!parsed.success) {
    return apiErro(parsed.error.issues[0].message);
  }

  const { data, valor, bancoOrig, bancoDest, descricao } = parsed.data;
  const desc = descricao?.trim() || "Transferência entre bancos";

  const [origem, destino] = await Promise.all([
    prisma.banco.findFirst({ where: { id: bancoOrig, usuarioId: sessao.id } }),
    prisma.banco.findFirst({ where: { id: bancoDest, usuarioId: sessao.id } }),
  ]);

  if (!origem || !destino) {
    return apiErro("Banco de origem ou destino inválido.", 404);
  }

  // Busca subconta de transferência; se não existir, usa qualquer subconta como fallback
  let subconta = await prisma.subconta.findFirst({
    where: { usuarioId: sessao.id, nome: { contains: "TRANSFER", mode: "insensitive" } },
  });
  if (!subconta) {
    subconta = await prisma.subconta.findFirst({ where: { usuarioId: sessao.id } });
  }

  const resultado = await prisma.$transaction(async (tx: PrismaTransaction) => {
    const transferencia = await tx.transferencia.create({
      data: { usuarioId: sessao.id, data, valor, bancoOrig, bancoDest, descricao: desc },
    });

    if (subconta) {
      await tx.transacao.create({
        data: {
          usuarioId: sessao.id,
          data,
          valor,
          subcontaId: subconta.id,
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
          subcontaId: subconta.id,
          tipo: "Receita",
          descricao: `Transf. ← ${origem.nomeBanco} | ${desc}`,
          bancoId: bancoDest,
        },
      });
    }

    return transferencia;
  });

  return apiOk({
    transferencia: resultado,
    aviso: subconta
      ? null
      : "Transferência salva, mas sem subconta de transferência cadastrada. Crie uma subconta com 'Transf' no nome.",
  });
});
