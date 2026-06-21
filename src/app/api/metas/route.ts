import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { mesAnterior } from "@/lib/utils";

/**
 * GET /api/metas?mes=06/2026
 * Traduzido da lógica em dashboard.py: se não houver meta para o mês,
 * busca automaticamente a do mês anterior (sem persistir, só para exibição).
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);
  const mes = searchParams.get("mes");

  if (!mes) return apiErro("Informe o parâmetro 'mes'.");

  let meta = await prisma.meta.findUnique({
    where: { usuarioId_mes: { usuarioId: sessao.id, mes } },
  });

  let copiadaDoMesAnterior = false;
  if (!meta) {
    const metaAnterior = await prisma.meta.findUnique({
      where: { usuarioId_mes: { usuarioId: sessao.id, mes: mesAnterior(mes) } },
    });
    if (metaAnterior) {
      meta = metaAnterior;
      copiadaDoMesAnterior = true;
    }
  }

  return apiOk({ meta, copiadaDoMesAnterior });
});

const metaSchema = z.object({
  mes: z.string().min(1),
  metaReceita: z.number().default(0),
  metaDespesa: z.number().default(0),
  metaResultado: z.number().default(0),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = metaSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { mes, metaReceita, metaDespesa, metaResultado } = parsed.data;

  const meta = await prisma.meta.upsert({
    where: { usuarioId_mes: { usuarioId: sessao.id, mes } },
    update: { metaReceita, metaDespesa, metaResultado },
    create: { usuarioId: sessao.id, mes, metaReceita, metaDespesa, metaResultado },
  });

  return apiOk({ meta });
});
