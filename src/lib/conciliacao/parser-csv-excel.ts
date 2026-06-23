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
 * Detecta a linha de header em extratos bancários.
 * Prioriza linhas que contêm palavras-chave típicas de cabeçalho de extrato,
 * depois cai para a heurística de "primeiro linha com 3+ células".
 */
function separarHeaderEDados(linhas: string[][]): { headers: string[]; dados: string[][] } {
  const PALAVRAS_HEADER = [
    "data", "descrição", "descricao", "histórico", "historico", "valor",
    "saldo", "débito", "debito", "crédito", "credito", "movimentação",
    "movimentacao", "liquidação", "liquidacao", "lançamento", "lancamento",
  ];

  let headerIdx = -1;

  // 1ª tentativa: linha com pelo menos 2 palavras-chave de header
  for (let i = 0; i < Math.min(20, linhas.length); i++) {
    const textos = linhas[i].map((c) => (c ?? "").toString().toLowerCase().trim());
    const matches = textos.filter((t) =>
      PALAVRAS_HEADER.some((p) => t.includes(p))
    ).length;
    if (matches >= 2) {
      headerIdx = i;
      break;
    }
  }

  // 2ª tentativa: primeira linha com 3+ células não vazias
  if (headerIdx === -1) {
    for (let i = 0; i < Math.min(20, linhas.length); i++) {
      const celulasComTexto = linhas[i].filter((c) => c && c.toString().trim().length > 0).length;
      if (celulasComTexto >= 3) {
        headerIdx = i;
        break;
      }
    }
  }

  if (headerIdx === -1) headerIdx = 0;

  return {
    headers: linhas[headerIdx].map((c) => c?.toString() ?? ""),
    dados: linhas.slice(headerIdx + 1).filter((l) => l.some((c) => c && c.toString().trim())),
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
