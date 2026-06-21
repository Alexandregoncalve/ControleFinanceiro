import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";
import { mesAtual } from "@/lib/utils";

function normalizar(s: string): string {
  return s
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
}

/**
 * GET /api/cartao-fatura?mes=06/2026
 * Traduzido de views/cartao.py: casa cada cartão cadastrado (tabela "cartoes")
 * com a subconta de lançamentos correspondente (nome contendo "CARTAO"/"CARTÃO"
 * e alguma palavra em comum com o nome do cartão), calcula fatura do mês,
 * limite disponível e parcelas futuras.
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);
  const mes = searchParams.get("mes") || mesAtual();
  const [mSel, aSel] = mes.split("/").map(Number);

  const [cartoes, subcontasCartao] = await Promise.all([
    prisma.cartao.findMany({
      where: { usuarioId: sessao.id },
      include: { banco: { select: { nomeBanco: true } } },
      orderBy: { nomeCartao: "asc" },
    }),
    prisma.subconta.findMany({
      where: {
        usuarioId: sessao.id,
        OR: [{ nome: { contains: "CARTAO", mode: "insensitive" } }, { nome: { contains: "CARTÃO", mode: "insensitive" } }],
      },
    }),
  ]);

  const usados = new Set<number>();
  const pares: { cartao: (typeof cartoes)[number] | null; subconta: (typeof subcontasCartao)[number] | null }[] = [];

  for (const c of cartoes) {
    const palavras = normalizar(c.nomeCartao)
      .split(/\s+/)
      .filter((p) => p.length >= 3);
    let match: (typeof subcontasCartao)[number] | null = null;
    for (const s of subcontasCartao) {
      if (usados.has(s.id)) continue;
      const nomeNorm = normalizar(s.nome);
      if (palavras.some((p) => nomeNorm.includes(p))) {
        match = s;
        break;
      }
    }
    if (match) usados.add(match.id);
    pares.push({ cartao: c, subconta: match });
  }

  for (const s of subcontasCartao) {
    if (!usados.has(s.id)) pares.push({ cartao: null, subconta: s });
  }

  const blocos = await Promise.all(
    pares.map(async ({ cartao, subconta }) => {
      let compras: { descricao: string | null; valor: number; parcelaAtual: number; totalParcelas: number }[] = [];
      let faturaAtual = 0;
      let parcelasFuturas = 0;

      if (subconta) {
        const transacoesMes = await prisma.transacao.findMany({
          where: { usuarioId: sessao.id, subcontaId: subconta.id, tipo: "Despesa", data: { endsWith: `/${mes}` } },
          select: { descricao: true, valor: true, parcelaAtual: true, totalParcelas: true },
          orderBy: { valor: "desc" },
        });
        compras = transacoesMes;
        faturaAtual = transacoesMes.reduce((acc: number, t: (typeof transacoesMes)[number]) => acc + t.valor, 0);

        const todasParceladas = await prisma.transacao.findMany({
          where: { usuarioId: sessao.id, subcontaId: subconta.id, tipo: "Despesa", totalParcelas: { gt: 1 } },
          select: { data: true, valor: true },
        });
        for (const t of todasParceladas) {
          const [, mStr, aStr] = t.data.split("/");
          const m = Number(mStr);
          const a = Number(aStr);
          if (a > aSel || (a === aSel && m > mSel)) {
            parcelasFuturas += t.valor;
          }
        }
      }

      return {
        nome: cartao?.nomeCartao ?? subconta?.nome ?? "—",
        tipo: cartao?.tipo ?? null,
        bancoNome: cartao?.banco?.nomeBanco ?? null,
        limite: cartao?.limite ?? subconta?.orcamento ?? 0,
        faturaAtual,
        parcelasFuturas,
        compras,
        temSubconta: subconta !== null,
      };
    })
  );

  return apiOk({ cartoes: blocos, mes });
});
