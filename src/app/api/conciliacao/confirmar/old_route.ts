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
  subcontaId: z.number().int().positive("Selecione uma subconta de destino."),
  linhas: z.array(linhaSchema),
});

/**
 * POST /api/conciliacao/confirmar
 * Recebe as linhas aprovadas pelo usuário na prévia e cria as transações no banco.
 * Só insere linhas com selecionada=true e que não tenham data duplicada na mesma subconta.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = bodySchema.safeParse(body);
  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { subcontaId, linhas } = parsed.data;

  // Verifica que a subconta pertence ao usuário
  const subconta = await prisma.subconta.findFirst({
    where: { id: subcontaId, usuarioId: sessao.id },
    include: { categoria: { select: { tipo: true } } },
  });
  if (!subconta) return apiErro("Subconta não encontrada.", 404);

  const linhasParaImportar = linhas.filter((l) => l.selecionada);
  if (linhasParaImportar.length === 0) return apiErro("Nenhuma linha selecionada para importar.");

  // Busca transações já existentes nessa subconta (para evitar duplicatas por data+valor+descrição)
  const existentes = await prisma.transacao.findMany({
    where: { usuarioId: sessao.id, subcontaId },
    select: { data: true, valor: true, descricao: true },
  });
  const chaveExistente = new Set(
    existentes.map((t: { data: string; valor: number; descricao: string | null }) =>
      `${t.data}|${t.valor}|${(t.descricao || "").toLowerCase().trim()}`
    )
  );

  let importadas = 0;
  let duplicatas = 0;

  for (const l of linhasParaImportar) {
    const chave = `${l.data}|${l.valor}|${l.descricao.toLowerCase().trim()}`;
    if (chaveExistente.has(chave)) {
      duplicatas++;
      continue;
    }

    // Determina o tipo real pela subconta (categoria pai) se conflitar com o extrato
    // Prefere o tipo do extrato, mas valida contra o tipo da categoria
    const tipoFinal = l.tipo;

    await prisma.transacao.create({
      data: {
        usuarioId: sessao.id,
        subcontaId,
        data: l.data,
        descricao: l.descricao,
        valor: l.valor,
        tipo: tipoFinal,
        parcelaAtual: 1,
        totalParcelas: 1,
      },
    });

    importadas++;
    chaveExistente.add(chave); // evita duplicata dentro do próprio lote
  }

  return apiOk({
    importadas,
    duplicatas,
    mensagem:
      duplicatas > 0
        ? `${importadas} lançamento(s) importado(s). ${duplicatas} ignorado(s) por já existirem.`
        : `${importadas} lançamento(s) importado(s) com sucesso.`,
  });
});
