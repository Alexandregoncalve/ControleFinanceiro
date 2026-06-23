import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const linhaSchema = z.object({
  data: z.string(),
  descricao: z.string(),
  valor: z.number().positive(),
  tipo: z.enum(["Receita", "Despesa"]),
  selecionada: z.boolean(),
});

const bodySchema = z.object({
  bancoId: z.number().int().positive("Banco não identificado."),
  linhas: z.array(linhaSchema),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { bancoId, linhas } = parsed.data;

  // Verifica que o banco pertence ao usuário
  const banco = await prisma.banco.findFirst({ where: { id: bancoId, usuarioId: sessao.id } });
  if (!banco) return apiErro("Banco não encontrado.", 404);

  const linhasParaImportar = linhas.filter((l) => l.selecionada);
  if (linhasParaImportar.length === 0) return apiErro("Nenhuma linha selecionada.");

  // Busca uma subconta padrão do banco (qualquer uma vinculada a ele por transações anteriores)
  // Se não existir, usa a primeira subconta "Outras Receitas/Despesas" como fallback genérico
  let subcontaReceitaId: number | null = null;
  let subcontaDespesaId: number | null = null;

  const transacaoExistente = await prisma.transacao.findFirst({
    where: { usuarioId: sessao.id, bancoId },
    select: { subcontaId: true, tipo: true },
  });

  if (transacaoExistente) {
    if (transacaoExistente.tipo === "Receita") subcontaReceitaId = transacaoExistente.subcontaId;
    else subcontaDespesaId = transacaoExistente.subcontaId;
  }

  // Fallback: busca subcontas genéricas se não encontrou por histórico
  if (!subcontaReceitaId) {
    const sub = await prisma.subconta.findFirst({
      where: { usuarioId: sessao.id, categoria: { tipo: "Receita" } },
      select: { id: true },
    });
    subcontaReceitaId = sub?.id ?? null;
  }
  if (!subcontaDespesaId) {
    const sub = await prisma.subconta.findFirst({
      where: { usuarioId: sessao.id, categoria: { tipo: "Despesa" } },
      select: { id: true },
    });
    subcontaDespesaId = sub?.id ?? null;
  }

  if (!subcontaReceitaId || !subcontaDespesaId) {
    return apiErro("Nenhuma subconta encontrada. Cadastre ao menos uma conta de Receita e uma de Despesa.");
  }

  // Verifica duplicatas pelo conjunto data+valor+descricao
  const existentes = await prisma.transacao.findMany({
    where: { usuarioId: sessao.id, bancoId },
    select: { data: true, valor: true, descricao: true },
  });
  const chaveExistente = new Set(
    existentes.map((t: { data: string; valor: number; descricao: string | null }) =>
      `${t.data}|${t.valor}|${(t.descricao ?? "").toLowerCase().trim()}`
    )
  );

  let importadas = 0;
  let duplicatas = 0;

  for (const l of linhasParaImportar) {
    const chave = `${l.data}|${l.valor}|${l.descricao.toLowerCase().trim()}`;
    if (chaveExistente.has(chave)) { duplicatas++; continue; }

    const subcontaId = l.tipo === "Receita" ? subcontaReceitaId : subcontaDespesaId;

    await prisma.transacao.create({
      data: {
        usuarioId: sessao.id,
        subcontaId,
        bancoId,
        data: l.data,
        descricao: l.descricao,
        valor: l.valor,
        tipo: l.tipo,
        parcelaAtual: 1,
        totalParcelas: 1,
      },
    });

    importadas++;
    chaveExistente.add(chave);
  }

  return apiOk({
    importadas,
    duplicatas,
    mensagem: duplicatas > 0
      ? `${importadas} lançamento(s) importado(s) para ${banco.nomeBanco}. ${duplicatas} ignorado(s) por já existirem.`
      : `${importadas} lançamento(s) importado(s) para ${banco.nomeBanco} com sucesso.`,
  });
});
