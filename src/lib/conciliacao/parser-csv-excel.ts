/**
 * Parser de CSV e Excel para conciliação bancária.
 *
 * Fluxo:
 * 1. Lê o arquivo e extrai todas as linhas como arrays de strings
 * 2. Detecta automaticamente qual linha é o header e quais colunas são
 *    data, descrição, valor/débito/crédito
 * 3. Retorna as linhas normalizadas + o mapeamento detectado para
 *    o usuário confirmar na UI
 */

import "server-only";
import * as XLSX from "xlsx";
import { LinhaExtrato, MapeamentoColunas, ResultadoParsing, PADROES_COLUNA } from "./tipos";
import { normalizarData, normalizarValor, detectarTipoPeloConteudo, pareceCom } from "./normalizacao";

/** Detecta automaticamente o mapeamento de colunas pelo nome do header */
function detectarMapeamento(headers: string[]): MapeamentoColunas {
  const m: MapeamentoColunas = {
    data: null, descricao: null, valor: null, debito: null, credito: null, tipo: null,
  };

  headers.forEach((h, i) => {
    if (m.data === null && pareceCom(h, PADROES_COLUNA.data)) m.data = i;
    else if (m.descricao === null && pareceCom(h, PADROES_COLUNA.descricao)) m.descricao = i;
    else if (m.debito === null && pareceCom(h, PADROES_COLUNA.debito)) m.debito = i;
    else if (m.credito === null && pareceCom(h, PADROES_COLUNA.credito)) m.credito = i;
    else if (m.valor === null && pareceCom(h, PADROES_COLUNA.valor)) m.valor = i;
    else if (m.tipo === null && pareceCom(h, PADROES_COLUNA.tipo)) m.tipo = i;
  });

  return m;
}

/** Converte linhas brutas + mapeamento em LinhaExtrato[] */
function linhasBrutasParaExtrato(
  linhasBrutas: string[][],
  mapeamento: MapeamentoColunas,
  avisos: string[]
): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let ignoradas = 0;

  linhasBrutas.forEach((linha, indice) => {
    const dataStr = mapeamento.data !== null ? linha[mapeamento.data] : "";
    const descStr = mapeamento.descricao !== null ? linha[mapeamento.descricao] : linha.join(" ");

    const data = normalizarData(dataStr);
    if (!data) { ignoradas++; return; }

    let valor: number | null = null;
    let tipo: "Receita" | "Despesa" = "Despesa";

    if (mapeamento.debito !== null && mapeamento.credito !== null) {
      // Débito e crédito em colunas separadas
      const vDebito = normalizarValor(linha[mapeamento.debito] ?? "");
      const vCredito = normalizarValor(linha[mapeamento.credito] ?? "");
      if (vCredito && Math.abs(vCredito) > 0) {
        valor = Math.abs(vCredito);
        tipo = "Receita";
      } else if (vDebito && Math.abs(vDebito) > 0) {
        valor = Math.abs(vDebito);
        tipo = "Despesa";
      }
    } else if (mapeamento.valor !== null) {
      // Valor único: sinal negativo = despesa
      const v = normalizarValor(linha[mapeamento.valor] ?? "");
      if (v !== null) {
        valor = Math.abs(v);
        tipo = v < 0 ? "Despesa" : "Receita";
      }
      // Coluna de tipo opcional
      if (mapeamento.tipo !== null) {
        const t = detectarTipoPeloConteudo(linha[mapeamento.tipo] ?? "");
        if (t) tipo = t;
      }
    }

    if (valor === null || valor === 0) { ignoradas++; return; }

    resultado.push({
      linhaOriginal: linha.join(" | "),
      data,
      descricao: descStr?.trim() || "(sem descrição)",
      valor,
      tipo,
      selecionada: true,
      indice,
    });
  });

  if (ignoradas > 0) {
    avisos.push(`${ignoradas} linha(s) ignorada(s) por não ter data ou valor válidos.`);
  }

  return resultado;
}

/**
 * Detecta a linha de header: a primeira linha que tem texto em pelo menos
 * 3 células é tratada como header. Extrai e retorna as linhas de dados separadas.
 */
function separarHeaderEDados(linhas: string[][]): { headers: string[]; dados: string[][] } {
  let headerIdx = 0;
  for (let i = 0; i < Math.min(10, linhas.length); i++) {
    const celulasComTexto = linhas[i].filter((c) => c && c.trim().length > 0).length;
    if (celulasComTexto >= 3) {
      headerIdx = i;
      break;
    }
  }
  return {
    headers: linhas[headerIdx].map((c) => c?.toString() ?? ""),
    dados: linhas.slice(headerIdx + 1).filter((l) => l.some((c) => c && c.trim())),
  };
}

/** Parseia um Buffer de arquivo CSV ou Excel e retorna ResultadoParsing */
export function parsearCSVOuExcel(buffer: Buffer, nomeArquivo: string): ResultadoParsing {
  const avisos: string[] = [];
  const formato = nomeArquivo.toLowerCase().endsWith(".csv") ? "csv" : "xlsx";

  const workbook = XLSX.read(buffer, {
    type: "buffer",
    raw: false,
    cellDates: false,
    cellText: true,
    codepage: 65001, // UTF-8
  });

  const planilha = workbook.Sheets[workbook.SheetNames[0]];
  const linhasRaw: string[][] = XLSX.utils.sheet_to_json(planilha, {
    header: 1,
    defval: "",
    raw: false,
  }) as string[][];

  if (linhasRaw.length < 2) {
    return {
      linhas: [], mapeamento: { data: null, descricao: null, valor: null, debito: null, credito: null, tipo: null },
      headers: [], linhasBrutas: [], avisos: ["Arquivo vazio ou com poucas linhas."], formato,
    };
  }

  const { headers, dados } = separarHeaderEDados(linhasRaw);
  const mapeamento = detectarMapeamento(headers);

  if (mapeamento.data === null) {
    avisos.push("Não foi possível detectar automaticamente a coluna de data. Selecione manualmente.");
  }
  if (mapeamento.valor === null && mapeamento.debito === null && mapeamento.credito === null) {
    avisos.push("Não foi possível detectar automaticamente a coluna de valor. Selecione manualmente.");
  }

  const linhas = linhasBrutasParaExtrato(dados, mapeamento, avisos);

  return { linhas, mapeamento, headers, linhasBrutas: dados.slice(0, 5), avisos, formato };
}
