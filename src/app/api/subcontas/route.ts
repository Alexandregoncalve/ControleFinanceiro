import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();

  const subcontas = await prisma.subconta.findMany({
    where: { usuarioId: sessao.id },
    include: { categoria: { select: { nome: true, tipo: true } } },
    orderBy: [{ categoria: { nome: "asc" } }, { nome: "asc" }],
  });

  const resultado = subcontas.map((s: (typeof subcontas)[number]) => ({
    id: s.id,
    categoriaId: s.categoriaId,
    nome: s.nome,
    fixa: s.fixa,
    orcamento: s.orcamento ?? 0,
    diaVencimento: s.diaVencimento,
    categoriaNome: s.categoria.nome,
    categoriaTipo: s.categoria.tipo,
  }));

  return apiOk({ subcontas: resultado });
});

const subcontaSchema = z.object({
  categoriaId: z.number(),
  nome: z.string().min(1, "Informe o nome da subconta."),
  fixa: z.boolean().default(false),
  orcamento: z.number().default(0),
  diaVencimento: z.number().nullable().optional(),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = subcontaSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { categoriaId, nome, fixa, orcamento, diaVencimento } = parsed.data;

  const subconta = await prisma.subconta.create({
    data: {
      usuarioId: sessao.id,
      categoriaId,
      nome: nome.trim().toUpperCase(),
      fixa: fixa ? 1 : 0,
      orcamento,
      diaVencimento: diaVencimento ?? null,
    },
  });

  return apiOk({ subconta }, 201);
});
