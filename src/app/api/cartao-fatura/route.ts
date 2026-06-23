import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";
import { mesAtual, parseDataBR } from "@/lib/utils";

function normalizar(s: string): string {
  return s
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase();
}

function descBase(descricao: string | null): string {
  if (!descricao) return "";
  const partes = descricao.trim().split(" ");
  const sufixo = partes[partes.length - 1];
  if (sufixo && sufixo.includes("/")) {
    const [a, b] = sufixo.split("/");
    if (/^\d+$/.test(a) && /^\d+$/.test(b)) {
      return partes.slice(0, -1).join(" ");
    }
  }
  return descricao;
}

/**
 * GET /api/cartao-fatura?mes=06/2026
 * Traduzido de views/cartao.py: casa cada cartão cadastrado (tabela "cartoes")
 * com a subconta de lançamentos correspondente, calcula fatura do mês (separando
 * o que já venceu/foi pago do que ainda está em aberto), limite disponível,
 * provisionamento de parcelas futuras mês a mês, e a lista de parcelamentos
 * em andamento daquele cartão especificamente (usa subconta.id como critério,
 * não mais comparação de texto entre nomes — mais confiável).
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);
  const mes = searchParams.get("mes") || mesAtual();
  const [mSel, aSel] = mes.split("/").map(Number);
  const hoje = new Date();

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
      let compras: { descricao: string | null; valor: number; parcelaAtual: number; totalParcelas: number; data: string }[] = [];
      let faturaAtual = 0;
      let parcelasFuturas = 0;
      let proximaFatura: { mes: string; valor: number } | null = null;
      let provisionamento: { mes: string; valor: number }[] = [];
      let parcelamentos: {
        descBase: string;
        valorParcela: number;
        valorTotal: number;
        pagas: number;
        totalParcelas: number;
        proximaData: string | null;
        status: "quitado" | "nao_iniciado" | "em_andamento";
      }[] = [];

      if (subconta) {
        const transacoesMes = await prisma.transacao.findMany({
          where: { usuarioId: sessao.id, subcontaId: subconta.id, tipo: "Despesa", data: { endsWith: `/${mes}` } },
          select: { descricao: true, valor: true, parcelaAtual: true, totalParcelas: true, data: true },
          orderBy: { valor: "desc" },
        });
        compras = transacoesMes;
        faturaAtual = transacoesMes.reduce((acc: number, t: (typeof transacoesMes)[number]) => acc + t.valor, 0);

        // Todas as transações parceladas desta subconta (qualquer mês)
        const todasParceladas = await prisma.transacao.findMany({
          where: { usuarioId: sessao.id, subcontaId: subconta.id, tipo: "Despesa", totalParcelas: { gt: 1 } },
          select: { descricao: true, data: true, valor: true, parcelaAtual: true, totalParcelas: true },
          orderBy: { data: "asc" },
        });

        // Parcelas futuras (total) + provisionamento mês a mês (próximos 6 meses)
        const provMap = new Map<string, number>();
        for (const t of todasParceladas) {
          const [, mStr, aStr] = t.data.split("/");
          const m = Number(mStr);
          const a = Number(aStr);
          const ehFutura = a > aSel || (a === aSel && m > mSel);
          if (ehFutura) {
            parcelasFuturas += t.valor;
            const chave = `${mStr}/${aStr}`;
            provMap.set(chave, (provMap.get(chave) ?? 0) + t.valor);
          }
        }
        provisionamento = Array.from(provMap.entries())
          .map(([mesChave, valor]) => ({ mes: mesChave, valor }))
          .sort((x, y) => {
            const [mx, ax] = x.mes.split("/").map(Number);
            const [my, ay] = y.mes.split("/").map(Number);
            return ax !== ay ? ax - ay : mx - my;
          })
          .slice(0, 6);

        proximaFatura = provisionamento.length > 0 ? provisionamento[0] : null;

        // Agrupa parcelamentos por compra (descrição-base), com status de progresso
        const porCompra = new Map<string, typeof todasParceladas>();
        for (const t of todasParceladas) {
          const chave = `${descBase(t.descricao)}||${t.totalParcelas}`;
          if (!porCompra.has(chave)) porCompra.set(chave, []);
          porCompra.get(chave)!.push(t);
        }
        parcelamentos = Array.from(porCompra.entries()).map(([chave, itens]) => {
          const base = chave.split("||")[0];
          const datasOrd = [...itens].sort((a, b) => parseDataBR(a.data).getTime() - parseDataBR(b.data).getTime());
          const pagas = datasOrd.filter((t) => parseDataBR(t.data) <= hoje).length;
          const totalParcelas = itens[0].totalParcelas;
          const restantes = totalParcelas - pagas;
          const proxima = datasOrd.find((t) => parseDataBR(t.data) > hoje)?.data ?? null;
          const valorParcela = itens[0].valor;

          let status: "quitado" | "nao_iniciado" | "em_andamento";
          if (restantes === 0) status = "quitado";
          else if (pagas === 0) status = "nao_iniciado";
          else status = "em_andamento";

          return {
            descBase: base || "(sem descrição)",
            valorParcela,
            valorTotal: valorParcela * totalParcelas,
            pagas,
            totalParcelas,
            proximaData: proxima,
            status,
          };
        });
      }

      return {
        nome: cartao?.nomeCartao ?? subconta?.nome ?? "—",
        tipo: cartao?.tipo ?? null,
        bancoNome: cartao?.banco?.nomeBanco ?? null,
        limite: cartao?.limite ?? subconta?.orcamento ?? 0,
        faturaAtual,
        proximaFatura,
        parcelasFuturas,
        provisionamento,
        compras,
        parcelamentos,
        temSubconta: subconta !== null,
      };
    })
  );

  return apiOk({ cartoes: blocos, mes });
});
