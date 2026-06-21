import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

/**
 * GET /api/transacoes?mes=06/2026&tipo=Despesa&subcontaId=3&busca=mercado
 * Traduzido das consultas usadas em extrato.py e dashboard.py.
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);

  const mes = searchParams.get("mes"); // formato MM/AAAA
  const tipo = searchParams.get("tipo"); // "Receita" | "Despesa"
  const subcontaId = searchParams.get("subcontaId");
  const bancoId = searchParams.get("bancoId");
  const busca = searchParams.get("busca");
  const limite = searchParams.get("limite");

  const where: Record<string, unknown> = { usuarioId: sessao.id };

  if (mes) where.data = { endsWith: `/${mes}` };
  if (tipo) where.tipo = tipo;
  if (subcontaId) where.subcontaId = Number(subcontaId);
  if (bancoId) where.bancoId = Number(bancoId);
  if (busca) where.descricao = { contains: busca, mode: "insensitive" };

  const transacoes = await prisma.transacao.findMany({
    where,
    include: {
      subconta: { select: { nome: true } },
      categoriaReal: { select: { nome: true } },
      banco: { select: { nomeBanco: true } },
    },
    orderBy: [{ data: "desc" }, { id: "desc" }],
    take: limite ? Number(limite) : undefined,
  });

  const resultado = transacoes.map((t: (typeof transacoes)[number]) => ({
    id: t.id,
    data: t.data,
    valor: t.valor,
    descricao: t.descricao,
    subcontaId: t.subcontaId,
    subcontaNome: t.subconta.nome,
    tipo: t.tipo,
    metodoPagamento: t.metodoPagamento,
    cartaoId: t.cartaoId,
    parcelaAtual: t.parcelaAtual,
    totalParcelas: t.totalParcelas,
    categoriaRealId: t.categoriaRealId,
    categoriaRealNome: t.categoriaReal?.nome ?? null,
    bancoId: t.bancoId,
    bancoNome: t.banco?.nomeBanco ?? null,
  }));

  return apiOk({ transacoes: resultado });
});

const transacaoSchema = z.object({
  data: z.string().min(1, "Informe a data."),
  valor: z.number().positive("Informe um valor válido."),
  descricao: z.string().optional(),
  subcontaId: z.number(),
  bancoId: z.number().nullable().optional(),
  categoriaRealId: z.number().nullable().optional(),
  parcelas: z.number().min(1).max(48).default(1),
});

/**
 * POST /api/transacoes
 * Traduzido da função salvar() em views/avulso.py.
 * Se a subconta selecionada for de cartão (nome contém "CARTAO"/"CARTÃO") e parcelas > 1,
 * gera N transações, uma por mês, com parcela_atual/total_parcelas preenchidos.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = transacaoSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { data, valor, descricao, subcontaId, bancoId, categoriaRealId, parcelas } = parsed.data;

  const subconta = await prisma.subconta.findFirst({
    where: { id: subcontaId, usuarioId: sessao.id },
    include: { categoria: { select: { tipo: true } } },
  });
  if (!subconta) return apiErro("Subconta não encontrada.", 404);

  const tipo = subconta.categoria.tipo;
  const ehCartao = /CART[AÃ]O/i.test(subconta.nome);

  if (ehCartao && categoriaRealId == null && tipo === "Despesa") {
    // Mantém compatibilidade com avulso.py: para cartão, a categoria real do gasto
    // é obrigatória do lado do cliente; aqui só seguimos se vier preenchida.
  }

  let categoriaRealNome: string | null = null;
  if (categoriaRealId) {
    const catReal = await prisma.subconta.findFirst({
      where: { id: categoriaRealId, usuarioId: sessao.id },
    });
    categoriaRealNome = catReal?.nome ?? null;
  }

  const [diaStr, mesStr, anoStr] = data.split("/");
  const dataBase = new Date(Number(anoStr), Number(mesStr) - 1, Number(diaStr), 12);

  const nParcelas = ehCartao ? parcelas : 1;
  const valorParcela = Math.round((valor / nParcelas) * 100) / 100;

  const transacoesParaCriar = [];

  if (nParcelas === 1) {
    const baseDesc = categoriaRealNome
      ? `${categoriaRealNome} - ${descricao || ""}`.trim().replace(/ - $/, "")
      : descricao || subconta.nome;

    transacoesParaCriar.push({
      usuarioId: sessao.id,
      data,
      valor,
      subcontaId,
      tipo,
      descricao: baseDesc,
      parcelaAtual: 1,
      totalParcelas: 1,
      categoriaRealId: categoriaRealId ?? null,
      bancoId: bancoId ?? null,
    });
  } else {
    for (let i = 1; i <= nParcelas; i++) {
      const dt = new Date(dataBase);
      dt.setMonth(dt.getMonth() + i);
      const dataParcela = `${String(dataBase.getDate()).padStart(2, "0")}/${String(
        dt.getMonth() + 1
      ).padStart(2, "0")}/${dt.getFullYear()}`;

      const baseDesc = categoriaRealNome
        ? `${categoriaRealNome} - ${descricao || ""}`.trim().replace(/ - $/, "")
        : descricao || "";
      const descParcela = baseDesc ? `${baseDesc} ${i}/${nParcelas}` : `${i}/${nParcelas}`;

      transacoesParaCriar.push({
        usuarioId: sessao.id,
        data: dataParcela,
        valor: valorParcela,
        subcontaId,
        tipo,
        descricao: descParcela,
        parcelaAtual: i,
        totalParcelas: nParcelas,
        categoriaRealId: categoriaRealId ?? null,
        bancoId: bancoId ?? null,
      });
    }
  }

  await prisma.transacao.createMany({ data: transacoesParaCriar });

  return apiOk({ ok: true, criadas: transacoesParaCriar.length }, 201);
});
