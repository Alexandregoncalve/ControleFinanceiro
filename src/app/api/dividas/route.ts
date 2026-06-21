import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

/**
 * GET /api/dividas
 * Traduzido de carregar_tudo() em views/dividas.py: lista dívidas com seus
 * pagamentos, calculando total pago, saldo devedor e status (atrasado/em dia/sem pagto).
 */
export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();

  const dividas = await prisma.divida.findMany({
    where: { usuarioId: sessao.id },
    include: { pagamentos: { orderBy: { data: "asc" } } },
    orderBy: [{ status: "asc" }, { nome: "asc" }],
  });

  let totalPagoGeral = 0;
  let saldoTotalGeral = 0;
  let qtdAtivas = 0;
  let qtdQuitadas = 0;

  const resultado = dividas.map((d: (typeof dividas)[number]) => {
    const totalPago = d.pagamentos.reduce((acc: number, p: { valor: number }) => acc + p.valor, 0);
    const saldo = Math.max(d.valorTotal - totalPago, 0);
    totalPagoGeral += totalPago;
    saldoTotalGeral += saldo;
    if (d.status === "ativa") qtdAtivas++;
    else qtdQuitadas++;

    return {
      id: d.id,
      nome: d.nome,
      tipoControle: d.tipoControle,
      valorTotal: d.valorTotal,
      valorParcela: d.valorParcela,
      totalParcelas: d.totalParcelas,
      diaVencimento: d.diaVencimento,
      dataInicio: d.dataInicio,
      taxaJuros: d.taxaJuros,
      status: d.status,
      dataQuitacao: d.dataQuitacao,
      totalPago,
      saldo,
      pagamentos: d.pagamentos,
    };
  });

  return apiOk({
    dividas: resultado,
    resumo: { totalPagoGeral, saldoTotalGeral, qtdAtivas, qtdQuitadas },
  });
});

const dividaSchema = z
  .object({
    nome: z.string().min(1, "Informe o nome da dívida."),
    tipoControle: z.enum(["parcelada", "livre"]),
    valorTotal: z.number().positive("Informe o valor total."),
    valorParcela: z.number().optional(),
    totalParcelas: z.number().optional(),
    diaVencimento: z.number().optional(),
    dataInicio: z.string().optional(),
    taxaJuros: z.number().default(0),
  })
  .refine(
    (d) => d.tipoControle !== "parcelada" || (d.valorParcela && d.valorParcela > 0),
    { message: "Informe o valor da parcela.", path: ["valorParcela"] }
  )
  .refine((d) => d.tipoControle !== "parcelada" || !!d.totalParcelas, {
    message: "Informe o número de parcelas.",
    path: ["totalParcelas"],
  })
  .refine((d) => d.tipoControle !== "parcelada" || !!d.diaVencimento, {
    message: "Informe o dia de vencimento.",
    path: ["diaVencimento"],
  });

/**
 * POST /api/dividas
 * Traduzido de registrar_divida() em views/dividas.py: se for dívida "parcelada",
 * cria automaticamente uma categoria "DÍVIDAS" (se não existir) e uma subconta
 * fixa vinculada, que passa a aparecer em Contas Fixas todo mês.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = dividaSchema.safeParse(body);

  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const d = parsed.data;

  const divida = await prisma.$transaction(async (tx: PrismaTransaction) => {
    const novaDivida = await tx.divida.create({
      data: {
        usuarioId: sessao.id,
        nome: d.nome.trim(),
        tipoControle: d.tipoControle,
        valorTotal: d.valorTotal,
        valorParcela: d.tipoControle === "parcelada" ? d.valorParcela : null,
        totalParcelas: d.tipoControle === "parcelada" ? d.totalParcelas : null,
        diaVencimento: d.tipoControle === "parcelada" ? d.diaVencimento : null,
        dataInicio: d.tipoControle === "parcelada" ? d.dataInicio ?? null : null,
        taxaJuros: d.taxaJuros,
        status: "ativa",
      },
    });

    if (d.tipoControle === "parcelada") {
      let categoria = await tx.categoria.findFirst({
        where: { usuarioId: sessao.id, nome: { contains: "DÍVIDA", mode: "insensitive" } },
      });
      if (!categoria) {
        categoria = await tx.categoria.create({
          data: { usuarioId: sessao.id, nome: "DÍVIDAS", tipo: "Despesa" },
        });
      }

      const subconta = await tx.subconta.create({
        data: {
          usuarioId: sessao.id,
          categoriaId: categoria.id,
          nome: d.nome.trim(),
          fixa: 1,
          diaVencimento: d.diaVencimento ?? null,
          orcamento: d.valorParcela ?? 0,
        },
      });

      await tx.divida.update({ where: { id: novaDivida.id }, data: { subcontaId: subconta.id } });
    }

    return novaDivida;
  });

  return apiOk(
    {
      divida,
      aviso: d.tipoControle === "parcelada" ? "Conta fixa criada automaticamente." : null,
    },
    201
  );
});
