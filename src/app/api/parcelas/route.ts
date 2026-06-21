import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";
import { parseDataBR } from "@/lib/utils";

/**
 * GET /api/parcelas
 * Traduzido de parcelas_view() em views/parcelas.py: agrupa transações parceladas
 * pela descrição-base (sem o sufixo "N/M"), conta + número total de parcelas,
 * calcula quantas já foram pagas (data <= hoje) e a próxima a vencer.
 */
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

export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();

  const transacoes = await prisma.transacao.findMany({
    where: { usuarioId: sessao.id, totalParcelas: { gt: 1 } },
    include: { subconta: { select: { nome: true } } },
    orderBy: { data: "asc" },
  });

  const grupos = new Map<
    string,
    {
      descBase: string;
      conta: string;
      totalParcelas: number;
      valorParcela: number;
      datas: string[];
    }
  >();

  for (const t of transacoes) {
    const base = descBase(t.descricao);
    const chave = `${base}||${t.subconta.nome}||${t.totalParcelas}`;
    if (!grupos.has(chave)) {
      grupos.set(chave, {
        descBase: base,
        conta: t.subconta.nome,
        totalParcelas: t.totalParcelas,
        valorParcela: t.valor,
        datas: [],
      });
    }
    grupos.get(chave)!.datas.push(t.data);
  }

  const hoje = new Date();
  let totalEmAberto = 0;
  let totalPago = 0;

  const resultado = Array.from(grupos.values()).map((g) => {
    const datasOrd = [...g.datas].sort(
      (a, b) => parseDataBR(a).getTime() - parseDataBR(b).getTime()
    );
    const pagas = datasOrd.filter((d) => parseDataBR(d) <= hoje).length;
    const restantes = g.totalParcelas - pagas;
    const proxima = datasOrd.find((d) => parseDataBR(d) > hoje) ?? null;

    totalEmAberto += g.valorParcela * restantes;
    totalPago += g.valorParcela * pagas;

    let status: "quitado" | "nao_iniciado" | "em_andamento";
    if (restantes === 0) status = "quitado";
    else if (pagas === 0) status = "nao_iniciado";
    else status = "em_andamento";

    return {
      descBase: g.descBase,
      conta: g.conta,
      valorParcela: g.valorParcela,
      valorTotal: g.valorParcela * g.totalParcelas,
      pagas,
      totalParcelas: g.totalParcelas,
      proximaData: proxima,
      status,
    };
  });

  return apiOk({
    parcelas: resultado,
    resumo: { totalPago, totalEmAberto, totalGeral: totalPago + totalEmAberto },
  });
});
