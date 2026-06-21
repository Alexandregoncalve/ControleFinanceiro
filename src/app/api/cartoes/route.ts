import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();

  const cartoes = await prisma.cartao.findMany({
    where: { usuarioId: sessao.id },
    include: { banco: { select: { nomeBanco: true } } },
    orderBy: { nomeCartao: "asc" },
  });

  const resultado = cartoes.map((c: (typeof cartoes)[number]) => ({
    id: c.id,
    nomeCartao: c.nomeCartao,
    limite: c.limite ?? 0,
    diaVencimento: c.diaVencimento,
    bancoId: c.bancoId,
    bancoNome: c.banco?.nomeBanco ?? null,
    tipo: c.tipo,
  }));

  return apiOk({ cartoes: resultado });
});

const cartaoSchema = z.object({
  nomeCartao: z.string().min(1, "Informe o nome do cartão."),
  tipo: z.enum(["Crédito", "Débito", "Ambos"]),
  limite: z.number().default(0),
  bancoId: z.number(),
  diaVencimento: z.number().nullable().optional(),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = cartaoSchema.safeParse(body);

  if (!parsed.success) {
    return apiErro(parsed.error.issues[0].message);
  }

  const cartao = await prisma.cartao.create({
    data: { usuarioId: sessao.id, ...parsed.data },
  });

  return apiOk({ cartao }, 201);
});
