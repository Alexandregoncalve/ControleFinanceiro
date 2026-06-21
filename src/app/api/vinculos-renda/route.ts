import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { calcularDescontoValeTransporte } from "@/lib/calculos-clt";
import { calcularDASMEI, calcularDASSimplesNacional, calcularFatorR, anexoEfetivoComFatorR } from "@/lib/calculos-tributarios";

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();
  const vinculos = await prisma.vinculoRenda.findMany({
    where: { usuarioId: sessao.id },
    orderBy: { criadoEm: "asc" },
  });
  return apiOk({ vinculos });
});

// ── Schemas por tipo ─────────────────────────────────────────────────────

const detalhesCLTSchema = z.object({
  empresa: z.string().optional().default(""),
  cargo: z.string().optional().default(""),
  salarioBruto: z.number().min(0),
  diaPagamento: z.number().nullable().optional(),
  recebeValeTransporte: z.boolean().default(false),
  recebeValeAlimentacao: z.boolean().default(false),
  valorValeAlimentacao: z.number().min(0).default(0),
  recebeAdiantamento: z.boolean().default(false),
  percentualAdiantamento: z.number().min(0).max(100).default(40),
  diaAdiantamento: z.number().nullable().optional(),
});

const detalhesAutonomoSchema = z.object({
  atividade: z.string().optional().default(""),
  rendaMediaMensal: z.number().min(0),
  planoINSS: z.enum(["simplificado_11", "normal_20", "baixa_renda_5"]).default("simplificado_11"),
  prestaServicoPJ: z.boolean().default(false),
});

const detalhesMEISchema = z.object({
  nomeFantasia: z.string().optional().default(""),
  cnpj: z.string().optional().default(""),
  atividade: z.enum(["comercio", "servico", "ambos"]),
  faturamentoMedioMensal: z.number().min(0),
  diaVencimentoDAS: z.number().default(20),
});

const detalhesSimplesSchema = z.object({
  razaoSocial: z.string().optional().default(""),
  cnpj: z.string().optional().default(""),
  anexo: z.enum(["I", "II", "III", "IV", "V"]),
  faturamento12meses: z.number().min(0),
  faturamentoMedioMensal: z.number().min(0),
  folhaPagamento12meses: z.number().min(0).default(0),
  diaVencimentoDAS: z.number().default(20),
});

const vinculoSchema = z.discriminatedUnion("tipo", [
  z.object({
    tipo: z.literal("CLT"),
    apelido: z.string().min(1, "Dê um apelido para este vínculo."),
    ativo: z.boolean().default(true),
    detalhes: detalhesCLTSchema,
  }),
  z.object({
    tipo: z.literal("AUTONOMO"),
    apelido: z.string().min(1, "Dê um apelido para este vínculo."),
    ativo: z.boolean().default(true),
    detalhes: detalhesAutonomoSchema,
  }),
  z.object({
    tipo: z.literal("MEI"),
    apelido: z.string().min(1, "Dê um apelido para este vínculo."),
    ativo: z.boolean().default(true),
    detalhes: detalhesMEISchema,
  }),
  z.object({
    tipo: z.literal("SIMPLES_NACIONAL"),
    apelido: z.string().min(1, "Dê um apelido para este vínculo."),
    ativo: z.boolean().default(true),
    detalhes: detalhesSimplesSchema,
  }),
]);

// ── Helpers de categorias ───────────────────────────────────────────────

async function obterCategoriasBase(tx: PrismaTransaction, usuarioId: number) {
  let catReceita = await tx.categoria.findFirst({ where: { usuarioId, tipo: "Receita" } });
  if (!catReceita) {
    catReceita = await tx.categoria.create({ data: { usuarioId, nome: "RECEITAS", tipo: "Receita" } });
  }
  let catDespesaFixa = await tx.categoria.findFirst({
    where: { usuarioId, nome: { contains: "FIXA", mode: "insensitive" }, tipo: "Despesa" },
  });
  if (!catDespesaFixa) {
    catDespesaFixa = await tx.categoria.create({ data: { usuarioId, nome: "DESPESAS FIXAS", tipo: "Despesa" } });
  }
  return { catReceita, catDespesaFixa };
}

function extrairPapel(nome: string): string | null {
  const match = nome.match(/^\[([A-Z_]+)\]/);
  return match ? match[1] : null;
}

async function upsertSubconta(
  tx: PrismaTransaction,
  porPapel: Record<string, { id: number; nome: string } | undefined>,
  papel: string,
  usuarioId: number,
  categoriaId: number,
  vinculoId: number,
  nomeBase: string,
  ativo: boolean,
  orcamento: number,
  diaVencimento: number | null
) {
  const nome = `[${papel}] ${nomeBase}`;
  const existente = porPapel[papel];

  if (!ativo) {
    if (existente) await tx.subconta.update({ where: { id: existente.id }, data: { fixa: 0 } });
    return;
  }
  if (existente) {
    await tx.subconta.update({ where: { id: existente.id }, data: { nome, fixa: 1, orcamento, diaVencimento } });
  } else {
    await tx.subconta.create({
      data: { usuarioId, categoriaId, vinculoRendaId: vinculoId, nome, fixa: 1, orcamento, diaVencimento },
    });
  }
}

// ── Sincronização de contas fixas por tipo ──────────────────────────────

async function sincronizarSubcontas(
  tx: PrismaTransaction,
  usuarioId: number,
  vinculoId: number,
  apelido: string,
  vinculo: z.infer<typeof vinculoSchema>
) {
  const { catReceita, catDespesaFixa } = await obterCategoriasBase(tx, usuarioId);
  const existentes: { id: number; nome: string }[] = await tx.subconta.findMany({
    where: { vinculoRendaId: vinculoId },
  });
  const porPapel: Record<string, { id: number; nome: string } | undefined> = {};
  for (const s of existentes) {
    const papel = extrairPapel(s.nome);
    if (papel) porPapel[papel] = s;
  }

  if (vinculo.tipo === "CLT") {
    const d = vinculo.detalhes;
    await upsertSubconta(tx, porPapel, "SALARIO", usuarioId, catReceita.id, vinculoId, `Salário ${apelido}`, d.salarioBruto > 0, d.salarioBruto, d.diaPagamento ?? null);
    await upsertSubconta(tx, porPapel, "VT", usuarioId, catDespesaFixa.id, vinculoId, `Vale-transporte ${apelido}`, d.recebeValeTransporte, calcularDescontoValeTransporte(d.salarioBruto), d.diaPagamento ?? null);
    await upsertSubconta(tx, porPapel, "VA", usuarioId, catReceita.id, vinculoId, `Vale-alimentação ${apelido}`, d.recebeValeAlimentacao, d.valorValeAlimentacao, d.diaPagamento ?? null);
    await upsertSubconta(tx, porPapel, "ADIANTAMENTO", usuarioId, catReceita.id, vinculoId, `Adiantamento ${apelido}`, d.recebeAdiantamento, Math.round(((d.salarioBruto * d.percentualAdiantamento) / 100) * 100) / 100, d.diaAdiantamento ?? null);
    return;
  }

  if (vinculo.tipo === "MEI") {
    const d = vinculo.detalhes;
    const dasValor = calcularDASMEI(d.atividade);
    await upsertSubconta(tx, porPapel, "DAS_MEI", usuarioId, catDespesaFixa.id, vinculoId, `DAS MEI ${apelido}`, true, dasValor, d.diaVencimentoDAS);
    return;
  }

  if (vinculo.tipo === "SIMPLES_NACIONAL") {
    const d = vinculo.detalhes;
    const fatorR = calcularFatorR(d.folhaPagamento12meses, d.faturamento12meses);
    const anexoEfetivo = anexoEfetivoComFatorR(d.anexo, fatorR);
    const dasEstimado = calcularDASSimplesNacional(anexoEfetivo, d.faturamento12meses, d.faturamentoMedioMensal);
    await upsertSubconta(tx, porPapel, "DAS_SIMPLES", usuarioId, catDespesaFixa.id, vinculoId, `DAS ${apelido}`, true, dasEstimado, d.diaVencimentoDAS);
    return;
  }

  // AUTONOMO: renda variável, sem conta fixa de "salário" — o usuário lança cada
  // recebimento manualmente no Avulso. Não cria subconta fixa de receita.
  // Pode futuramente criar conta fixa de "INSS a recolher" se desejado.
}

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = vinculoSchema.safeParse(body);
  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const dados = parsed.data;

  const resultado = await prisma.$transaction(async (tx: PrismaTransaction) => {
    const vinculo = await tx.vinculoRenda.create({
      data: {
        usuarioId: sessao.id,
        tipo: dados.tipo,
        apelido: dados.apelido.trim(),
        ativo: dados.ativo,
        detalhes: dados.detalhes,
      },
    });

    if (dados.ativo) {
      await sincronizarSubcontas(tx, sessao.id, vinculo.id, dados.apelido.trim(), dados);
    }

    return vinculo;
  });

  return apiOk(
    {
      vinculo: resultado,
      aviso:
        dados.tipo === "AUTONOMO"
          ? null
          : "Conta(s) fixa(s) criada(s)/atualizada(s) automaticamente para este vínculo.",
    },
    201
  );
});
