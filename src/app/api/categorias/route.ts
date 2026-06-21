import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();
  const categorias = await prisma.categoria.findMany({
    where: { usuarioId: sessao.id },
    orderBy: [{ tipo: "asc" }, { nome: "asc" }],
  });
  return apiOk({ categorias });
});

const categoriaSchema = z.object({
  nome: z.string().min(1, "Informe o nome da conta pai."),
  tipo: z.enum(["Receita", "Despesa"]),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = categoriaSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const categoria = await prisma.categoria.create({
    data: {
      usuarioId: sessao.id,
      nome: parsed.data.nome.trim().toUpperCase(),
      tipo: parsed.data.tipo,
    },
  });

  return apiOk({ categoria }, 201);
});
