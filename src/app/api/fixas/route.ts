import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { mesAtual } from "@/lib/utils";

/**
 * GET /api/fixas?mes=06/2026
 * Traduzido de fixas_view() em views/fixas.py: lista subcontas marcadas como fixa=1
 * que ainda não tiveram transação lançada no mês, ordenadas por dia de vencimento.
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);
  const mes = searchParams.get("mes") || mesAtual();

  const todasFixas = await prisma.subconta.findMany({
    where: { usuarioId: sessao.id, fixa: 1 },
    orderBy: [{ diaVencimento: "asc" }, { nome: "asc" }],
  });

  const transacoesDoMes = await prisma.transacao.findMany({
    where: { usuarioId: sessao.id, data: { endsWith: `/${mes}` } },
    select: { subcontaId: true },
  });
  const pagos = new Set(transacoesDoMes.map((t: { subcontaId: number }) => t.subcontaId));

  const pendentes = todasFixas.filter((s: (typeof todasFixas)[number]) => !pagos.has(s.id));
  const lancadas = todasFixas.length - pendentes.length;

  return apiOk({
    pendentes,
    total: todasFixas.length,
    lancadas,
    mes,
  });
});

const baixarItemSchema = z.object({
  subcontaId: z.number(),
  valor: z.number().positive(),
  descricao: z.string().optional(),
  data: z.string().min(1),
});

const baixarSchema = z.object({
  itens: z.array(baixarItemSchema).min(1, "Selecione ao menos uma conta."),
  bancoId: z.number().nullable().optional(),
});

/** POST /api/fixas — traduzido da função baixar() em views/fixas.py */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = baixarSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { itens, bancoId } = parsed.data;

  const subcontaIds = itens.map((i) => i.subcontaId);
  const subcontas = await prisma.subconta.findMany({
    where: { id: { in: subcontaIds }, usuarioId: sessao.id },
    include: { categoria: { select: { tipo: true } } },
  });
  const tipoMap = new Map(subcontas.map((s: (typeof subcontas)[number]) => [s.id, s.categoria.tipo]));

  const dataParaCriar = itens.map((item) => ({
    usuarioId: sessao.id,
    data: item.data,
    valor: item.valor,
    subcontaId: item.subcontaId,
    tipo: tipoMap.get(item.subcontaId) ?? "Despesa",
    descricao: item.descricao || "",
    bancoId: bancoId ?? null,
  }));

  await prisma.transacao.createMany({ data: dataParaCriar });

  return apiOk({ ok: true, criadas: dataParaCriar.length });
});
