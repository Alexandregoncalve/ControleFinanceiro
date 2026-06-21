import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

// Traduzido de get_saldos_map() + card_banco() em views/bancos.py:
// calcula o saldo real = saldo_inicial + receitas - despesas lançadas naquele banco.
async function calcularSaldosBancos(usuarioId: number) {
  const somas = await prisma.transacao.groupBy({
    by: ["bancoId", "tipo"],
    where: { usuarioId, bancoId: { not: null } },
    _sum: { valor: true },
  });

  const mapa = new Map<number, { receitas: number; despesas: number }>();
  for (const s of somas) {
    if (!s.bancoId) continue;
    const atual = mapa.get(s.bancoId) ?? { receitas: 0, despesas: 0 };
    if (s.tipo === "Receita") atual.receitas += s._sum.valor ?? 0;
    else atual.despesas += s._sum.valor ?? 0;
    mapa.set(s.bancoId, atual);
  }
  return mapa;
}

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();

  const bancos = await prisma.banco.findMany({
    where: { usuarioId: sessao.id },
    orderBy: { nomeBanco: "asc" },
  });

  const saldosMap = await calcularSaldosBancos(sessao.id);

  const resultado = bancos.map((b: (typeof bancos)[number]) => {
    const mov = saldosMap.get(b.id) ?? { receitas: 0, despesas: 0 };
    return {
      ...b,
      saldoAtual: b.saldoInicial + mov.receitas - mov.despesas,
    };
  });

  return apiOk({ bancos: resultado });
});

const bancoSchema = z.object({
  nomeBanco: z.string().min(1, "Informe o nome do banco."),
  codigoBanco: z.string().optional().nullable(),
  agencia: z.string().optional().nullable(),
  numeroConta: z.string().optional().nullable(),
  saldoInicial: z.number().default(0),
  dataCriacao: z.string().optional().nullable(),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = bancoSchema.safeParse(body);

  if (!parsed.success) {
    return apiErro(parsed.error.issues[0].message);
  }

  const banco = await prisma.banco.create({
    data: { usuarioId: sessao.id, ...parsed.data },
  });

  return apiOk({ banco }, 201);
});
