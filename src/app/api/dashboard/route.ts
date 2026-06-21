import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";
import { mesAtual, mesAnterior, diasNoMes } from "@/lib/utils";

interface TransacaoBasica {
  data: string;
  valor: number;
  tipo: string;
  bancoId?: number | null;
}

/**
 * GET /api/dashboard?mes=06/2026
 * Tradução completa da lógica de carregar() em views/dashboard.py:
 * cards de resumo, saúde financeira, bancos, top gastos, orçamento, histórico.
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const uid = sessao.id;
  const { searchParams } = new URL(req.url);
  const mes = searchParams.get("mes") || mesAtual();
  const mesAnt = mesAnterior(mes);
  const [mSel, aSel] = mes.split("/").map(Number);

  // ── Receitas / despesas do mês e do mês anterior ────────────────────
  const [somaMesAtual, somaMesAnterior] = await Promise.all([
    prisma.transacao.groupBy({
      by: ["tipo"],
      where: { usuarioId: uid, data: { endsWith: `/${mes}` } },
      _sum: { valor: true },
    }),
    prisma.transacao.groupBy({
      by: ["tipo"],
      where: { usuarioId: uid, data: { endsWith: `/${mesAnt}` } },
      _sum: { valor: true },
    }),
  ]);

  type GrupoSoma = { tipo: string; _sum: { valor: number | null } };
  const ent = (somaMesAtual as GrupoSoma[]).find((s) => s.tipo === "Receita")?._sum.valor ?? 0;
  const sai = (somaMesAtual as GrupoSoma[]).find((s) => s.tipo === "Despesa")?._sum.valor ?? 0;
  const entAnt = (somaMesAnterior as GrupoSoma[]).find((s) => s.tipo === "Receita")?._sum.valor ?? 0;
  const saiAnt = (somaMesAnterior as GrupoSoma[]).find((s) => s.tipo === "Despesa")?._sum.valor ?? 0;
  const saldoMes = ent - sai;
  const saldoAnt = entAnt - saiAnt;

  // ── Saldo acumulado total e por banco (até o mês/ano selecionado, inclusive) ──
  const bancos = await prisma.banco.findMany({ where: { usuarioId: uid } });
  const saldoInicialTotal = bancos.reduce(
    (acc: number, b: { saldoInicial: number }) => acc + b.saldoInicial,
    0
  );

  const todasTransacoes: TransacaoBasica[] = await prisma.transacao.findMany({
    where: { usuarioId: uid },
    select: { data: true, valor: true, tipo: true, bancoId: true },
  });

  function dentroDoFiltro(t: TransacaoBasica): boolean {
    const [, mStr, aStr] = t.data.split("/");
    const m = Number(mStr);
    const a = Number(aStr);
    return a < aSel || (a === aSel && m <= mSel);
  }

  let saldoMovAcumulado = 0;
  for (const t of todasTransacoes) {
    if (dentroDoFiltro(t)) {
      saldoMovAcumulado += t.tipo === "Receita" ? t.valor : -t.valor;
    }
  }
  const saldoAcumulado = saldoInicialTotal + saldoMovAcumulado;

  const bancosComSaldo = bancos.map((b: (typeof bancos)[number]) => {
    let mov = 0;
    for (const t of todasTransacoes) {
      if (t.bancoId !== b.id) continue;
      if (dentroDoFiltro(t)) {
        mov += t.tipo === "Receita" ? t.valor : -t.valor;
      }
    }
    return {
      id: b.id,
      nomeBanco: b.nomeBanco,
      saldoInicial: b.saldoInicial,
      saldoAtual: b.saldoInicial + mov,
      agencia: b.agencia,
      numeroConta: b.numeroConta,
    };
  });

  // ── Metas do mês (com fallback para o mês anterior) ──────────────────
  let meta = await prisma.meta.findUnique({ where: { usuarioId_mes: { usuarioId: uid, mes } } });
  let metaCopiada = false;
  if (!meta) {
    meta = await prisma.meta.findUnique({ where: { usuarioId_mes: { usuarioId: uid, mes: mesAnt } } });
    if (meta) metaCopiada = true;
  }
  const metaReceita = meta?.metaReceita ?? 0;
  const metaDespesa = meta?.metaDespesa ?? 0;
  const metaResultado = meta?.metaResultado ?? 0;

  // ── Gastos por categoria (subconta), considerando categoria_real ────
  const transacoesMes = await prisma.transacao.findMany({
    where: { usuarioId: uid, tipo: "Despesa", data: { endsWith: `/${mes}` } },
    include: {
      subconta: { select: { nome: true, fixa: true, orcamento: true } },
      categoriaReal: { select: { nome: true, orcamento: true } },
    },
  });
  type TransacaoComSub = (typeof transacoesMes)[number];

  const gastosMap = new Map<string, number>();
  for (const t of transacoesMes) {
    const nome = t.categoriaReal?.nome ?? t.subconta.nome;
    gastosMap.set(nome, (gastosMap.get(nome) ?? 0) + t.valor);
  }
  const gastos = Array.from(gastosMap.entries())
    .map(([nome, total]) => ({ nome, total }))
    .sort((a, b) => b.total - a.total);

  // ── Cartão de crédito (% das despesas do mês) ─────────────────────────
  const totalCartao = transacoesMes
    .filter((t: TransacaoComSub) => /CART[AÃ]O/i.test(t.subconta.nome))
    .reduce((acc: number, t: TransacaoComSub) => acc + t.valor, 0);
  const pctCartao = sai > 0 ? (totalCartao / sai) * 100 : 0;

  // ── Despesas fixas do mês ─────────────────────────────────────────────
  const totalFixas = await prisma.subconta.count({ where: { usuarioId: uid, fixa: 1 } });
  const transacoesDoMesIds = await prisma.transacao.findMany({
    where: { usuarioId: uid, data: { endsWith: `/${mes}` } },
    select: { subcontaId: true },
  });
  const subcontasComLancamento = new Set(
    transacoesDoMesIds.map((t: { subcontaId: number }) => t.subcontaId)
  );
  const fixasIds = await prisma.subconta.findMany({
    where: { usuarioId: uid, fixa: 1 },
    select: { id: true },
  });
  const fixasPendentes = fixasIds.filter(
    (f: { id: number }) => !subcontasComLancamento.has(f.id)
  ).length;

  const fixasValor = transacoesMes
    .filter((t: TransacaoComSub) => t.subconta.fixa === 1)
    .reduce((acc: number, t: TransacaoComSub) => acc + t.valor, 0);

  const transacoesMesAnterior = await prisma.transacao.findMany({
    where: { usuarioId: uid, tipo: "Despesa", data: { endsWith: `/${mesAnt}` } },
    include: { subconta: { select: { fixa: true } } },
  });
  type TransacaoComFixa = (typeof transacoesMesAnterior)[number];
  const fixasValorAnt = transacoesMesAnterior
    .filter((t: TransacaoComFixa) => t.subconta.fixa === 1)
    .reduce((acc: number, t: TransacaoComFixa) => acc + t.valor, 0);

  const pctFixasDesp = sai > 0 ? (fixasValor / sai) * 100 : 0;

  // ── Orçamento mensal (categorias com orçamento definido) ─────────────
  // Usa o orçamento já incluído na consulta de transacoesMes (subconta/categoriaReal),
  // evitando N consultas extras ao banco dentro do loop.
  const orcamentosMap = new Map<string, { total: number; orcamento: number }>();
  for (const t of transacoesMes) {
    const orcamentoAplicavel = t.categoriaReal ? t.categoriaReal.orcamento ?? 0 : t.subconta.orcamento ?? 0;
    if (orcamentoAplicavel > 0) {
      const nome = t.categoriaReal?.nome ?? t.subconta.nome;
      const atual = orcamentosMap.get(nome) ?? { total: 0, orcamento: orcamentoAplicavel };
      atual.total += t.valor;
      orcamentosMap.set(nome, atual);
    }
  }
  const orcamentos = Array.from(orcamentosMap.entries())
    .map(([nome, v]) => ({ nome, total: v.total, orcamento: v.orcamento }))
    .sort((a, b) => b.total / b.orcamento - a.total / a.orcamento);

  // ── Score de saúde financeira (4 indicadores ponderados) ─────────────
  const scorePoupanca = ent > 0 ? Math.max(0, Math.min(100, Math.round((saldoMes / ent) * 100))) : 0;
  const orcOk = orcamentos.filter((o) => o.total <= o.orcamento).length;
  const scoreOrcamento = orcamentos.length > 0 ? Math.round((orcOk / orcamentos.length) * 100) : 100;
  const scoreFixas =
    totalFixas > 0 ? Math.max(0, Math.round(((totalFixas - fixasPendentes) / totalFixas) * 100)) : 100;
  const scoreComprometimento = ent > 0 ? Math.max(0, 100 - Math.round((sai / ent) * 100)) : 0;
  const scoreFinal = Math.round(
    scorePoupanca * 0.35 + scoreOrcamento * 0.25 + scoreFixas * 0.25 + scoreComprometimento * 0.15
  );

  let saudeLabel: "BOA" | "REGULAR" | "ATENÇÃO";
  if (scoreFinal >= 70) saudeLabel = "BOA";
  else if (scoreFinal >= 40) saudeLabel = "REGULAR";
  else saudeLabel = "ATENÇÃO";

  // ── Histórico mensal (para o gráfico "Como está o mês") ──────────────
  const todasComData: TransacaoBasica[] = await prisma.transacao.findMany({
    where: { usuarioId: uid },
    select: { data: true, valor: true, tipo: true },
  });
  const histMap = new Map<string, { receita: number; despesa: number }>();
  for (const t of todasComData) {
    const partes = t.data.split("/");
    const chave = `${partes[1]}/${partes[2]}`;
    const atual = histMap.get(chave) ?? { receita: 0, despesa: 0 };
    if (t.tipo === "Receita") atual.receita += t.valor;
    else atual.despesa += t.valor;
    histMap.set(chave, atual);
  }
  const mesesOrdenados = Array.from(histMap.keys()).sort((a, b) => {
    const [ma, aa] = a.split("/").map(Number);
    const [mb, ab] = b.split("/").map(Number);
    return aa !== ab ? aa - ab : ma - mb;
  });
  const mesesAnteriores = mesesOrdenados.filter((m) => m !== mes).slice(-4);
  const historico = [...mesesAnteriores, mes].map((m) => ({
    mes: m,
    receita: histMap.get(m)?.receita ?? 0,
    despesa: histMap.get(m)?.despesa ?? 0,
    ehAtual: m === mes,
  }));

  // ── Dias restantes no mês (só faz sentido se for o mês corrente real) ──
  const hoje = new Date();
  const ehMesAtualReal = mSel === hoje.getMonth() + 1 && aSel === hoje.getFullYear();
  const diasRestantes = ehMesAtualReal ? Math.max(0, diasNoMes(mSel, aSel) - hoje.getDate()) : 0;

  return apiOk({
    mes,
    resumo: {
      receitas: ent,
      despesas: sai,
      resultado: saldoMes,
      receitasAnterior: entAnt,
      despesasAnterior: saiAnt,
      resultadoAnterior: saldoAnt,
      metaReceita,
      metaDespesa,
      metaResultado,
      metaCopiada,
    },
    saldoAcumulado,
    bancos: bancosComSaldo,
    cartao: { total: totalCartao, percentualDespesas: pctCartao },
    fixas: {
      valor: fixasValor,
      valorAnterior: fixasValorAnt,
      percentualDespesas: pctFixasDesp,
      totalContas: totalFixas,
      pendentes: fixasPendentes,
      lancadas: totalFixas - fixasPendentes,
    },
    saude: {
      score: scoreFinal,
      label: saudeLabel,
      indicadores: {
        poupanca: scorePoupanca,
        orcamento: scoreOrcamento,
        fixasPagas: scoreFixas,
        rendaLivre: scoreComprometimento,
      },
    },
    gastos: gastos.slice(0, 10),
    orcamentos,
    historico,
    diasRestantes,
  });
});
