import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

/**
 * GET /api/dashboard/comparativo?inicio=MM/AAAA&fim=MM/AAAA
 * Traduzido de carregar_comparativo() em views/dashboard.py: cruza despesas por
 * conta (considerando categoria_real quando houver) com os meses do período,
 * para montar uma tabela "conta x mês".
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const { searchParams } = new URL(req.url);
  const inicio = searchParams.get("inicio");
  const fim = searchParams.get("fim");

  if (!inicio || !fim) return apiErro("Informe os parâmetros 'inicio' e 'fim'.");

  function mesesEntre(ini: string, fimStr: string): string[] {
    const resultado: string[] = [];
    let [m, a] = ini.split("/").map(Number);
    const [mf, af] = fimStr.split("/").map(Number);
    let guard = 0;
    while ((a < af || (a === af && m <= mf)) && guard < 60) {
      resultado.push(`${String(m).padStart(2, "0")}/${a}`);
      m += 1;
      if (m > 12) {
        m = 1;
        a += 1;
      }
      guard++;
    }
    return resultado;
  }

  const meses = mesesEntre(inicio, fim);
  if (meses.length === 0) return apiErro("Período inválido.");

  const transacoes = await prisma.transacao.findMany({
    where: { usuarioId: sessao.id, tipo: "Despesa" },
    include: {
      subconta: { select: { nome: true } },
      categoriaReal: { select: { nome: true } },
    },
  });

  // Estrutura: { nomeConta: { "MM/AAAA": valor } }
  const dados = new Map<string, Map<string, number>>();
  const mesesComDados = new Set<string>();

  for (const t of transacoes) {
    const partes = t.data.split("/");
    const mesT = `${partes[1]}/${partes[2]}`;
    if (!meses.includes(mesT)) continue;

    const nome = t.categoriaReal?.nome ?? t.subconta.nome;
    if (!dados.has(nome)) dados.set(nome, new Map());
    const porMes = dados.get(nome)!;
    porMes.set(mesT, (porMes.get(mesT) ?? 0) + t.valor);
    mesesComDados.add(mesT);
  }

  const mesesOrdenados = meses.filter((m) => mesesComDados.has(m));

  if (mesesOrdenados.length === 0) {
    return apiOk({ contas: [], meses: [], mensagem: "Sem dados no período selecionado." });
  }

  const contas = Array.from(dados.keys())
    .sort()
    .map((nome) => {
      const porMes = dados.get(nome)!;
      const valores = mesesOrdenados.map((m) => ({
        mes: m,
        valor: porMes.has(m) ? porMes.get(m)! : null,
      }));
      return { nome, valores };
    });

  return apiOk({
    contas,
    meses: mesesOrdenados,
    mensagem: `Exibindo ${mesesOrdenados.length} mês(es) com dados.`,
  });
});
