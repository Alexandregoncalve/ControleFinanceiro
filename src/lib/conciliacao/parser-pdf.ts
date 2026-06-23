/**
 * Parser de PDF para conciliação bancária.
 * IMPORTANTE: Este módulo usa 'pdf-parse' que só funciona em Node.js (servidor).
 * Nunca importe este arquivo diretamente em componentes client-side.
 */
import "server-only";

import { LinhaExtrato, MapeamentoColunas, ResultadoParsing } from "./tipos";
import { normalizarData, normalizarValor } from "./normalizacao";

/** Linhas que devem ser ignoradas em qualquer extrato (totais, rodapés, etc) */
const LINHAS_IGNORAR = [
  /saldo anterior/i,
  /saldo final/i,
  /saldo inicial/i,
  /saldo da conta/i,
  /total de cr[eé]ditos?/i,
  /total de d[eé]bitos?/i,
  /lan[cç]amentos? futuros?/i,
  /lan[cç]amentos? a conferir/i,
  /limite cheque especial/i,
  /taxa de juros/i,
  /sicredi fone/i,
  /sac [0-9]/i,
  /ouvidoria/i,
  /movimenta[cç][aã]o - conta/i,
  /informa[cç][oõ]es de conta/i,
  /extrato da conta/i,
  /data da consulta/i,
  /assessor/i,
  /cnpj/i,
  /projeções futuras/i,
  /resgates de fundos/i,
  /termos à vencer/i,
  /saldo total projetado/i,
  /^\s*$/, // linhas vazias
];

function deveIgnorar(linha: string): boolean {
  return LINHAS_IGNORAR.some((re) => re.test(linha.trim()));
}

/** Detecta o banco/layout pelo conteúdo do texto */
function detectarLayout(texto: string): "sicredi" | "rico" | "btg" | "generico" {
  const t = texto.toLowerCase();
  if (t.includes("sicredi") || t.includes("cooperativa:")) return "sicredi";
  if (t.includes("rico corretora") || t.includes("rico.com.br")) return "rico";
  if (t.includes("btgpactual") || t.includes("btg pactual")) return "btg";
  return "generico";
}

/**
 * Parser Sicredi: 5 colunas — Data | Descrição | Documento | Valor (R$) | Saldo (R$)
 * Valor negativo = débito, positivo = crédito.
 */
function parsearSicredi(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  for (const linha of linhas) {
    if (deveIgnorar(linha)) continue;

    // Padrão: DD/MM/AAAA + texto + código_doc + -999,99 + 999,99
    const m = linha.match(
      /^(\d{2}\/\d{2}\/\d{4})\s+(.+?)\s+([A-Z0-9_]+)\s+(-?\d[\d.,]+)\s+(-?\d[\d.,]+)\s*$/
    );
    if (!m) continue;

    const [, data, descricao, , valorStr] = m;
    const valor = normalizarValor(valorStr);
    if (!valor || valor === 0) continue;

    resultado.push({
      linhaOriginal: linha.trim(),
      data,
      descricao: descricao.trim(),
      valor: Math.abs(valor),
      tipo: valor < 0 ? "Despesa" : "Receita",
      selecionada: true,
      indice: idx++,
    });
  }

  return resultado;
}

/**
 * Parser Rico: 5 colunas — Liq | Mov | Histórico | Valor | Saldo
 * Valor negativo = débito (saída). Ignora linhas de dividendos/JCP se necessário.
 */
function parsearRico(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  for (const linha of linhas) {
    if (deveIgnorar(linha)) continue;

    // Padrão: DD/MM/AAAA DD/MM/AAAA DESCRIÇÃO R$ 999,99 R$ 999,99
    // ou: DD/MM/AAAA DD/MM/AAAA DESCRIÇÃO -R$ 999,99 R$ 999,99
    const m = linha.match(
      /^(\d{2}\/\d{2}\/\d{4})\s+\d{2}\/\d{2}\/\d{4}\s+(.+?)\s+(-?R?\$?\s*\d[\d.,]+)\s+(-?R?\$?\s*\d[\d.,]+)\s*$/
    );
    if (!m) continue;

    const [, data, descricao, valorStr] = m;
    const valor = normalizarValor(valorStr.replace(/R\$/g, "").trim());
    if (!valor || valor === 0) continue;

    resultado.push({
      linhaOriginal: linha.trim(),
      data,
      descricao: descricao.trim(),
      valor: Math.abs(valor),
      tipo: valor < 0 ? "Despesa" : "Receita",
      selecionada: true,
      indice: idx++,
    });
  }

  return resultado;
}

/**
 * Parser BTG: 5 colunas — Data | Descrição | Débito | Crédito | Saldo
 * Débito e crédito em colunas separadas.
 */
function parsearBTG(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  for (const linha of linhas) {
    if (deveIgnorar(linha)) continue;

    // Padrão com débito e crédito separados: DD/MM/AAAA DESCRIÇÃO 999,99 999,99 999,99
    // ou: DD/MM/AAAA DESCRIÇÃO [débito vazio] 999,99 999,99
    const m = linha.match(
      /^(\d{2}\/\d{2}\/\d{4})\s+(.+?)\s+(\d[\d.,]+)?\s+(\d[\d.,]+)?\s+\d[\d.,]+\s*$/
    );
    if (!m) continue;

    const [, data, descricao, debitoStr, creditoStr] = m;

    let valor: number;
    let tipo: "Receita" | "Despesa";

    const debito = debitoStr ? normalizarValor(debitoStr) : null;
    const credito = creditoStr ? normalizarValor(creditoStr) : null;

    if (credito && credito > 0) {
      valor = credito;
      tipo = "Receita";
    } else if (debito && debito > 0) {
      valor = debito;
      tipo = "Despesa";
    } else {
      continue;
    }

    resultado.push({
      linhaOriginal: linha.trim(),
      data,
      descricao: descricao.trim(),
      valor,
      tipo,
      selecionada: true,
      indice: idx++,
    });
  }

  return resultado;
}

/**
 * Parser genérico: tenta encontrar linhas que começam com data DD/MM/AAAA
 * e extrai valor do final da linha.
 */
function parsearGenerico(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  for (const linha of linhas) {
    if (deveIgnorar(linha)) continue;

    const m = linha.match(/^(\d{2}\/\d{2}\/\d{4})\s+(.+?)\s+(-?\d[\d.,]+)\s*$/);
    if (!m) continue;

    const [, data, descricao, valorStr] = m;
    const valor = normalizarValor(valorStr);
    if (!valor || valor === 0) continue;

    resultado.push({
      linhaOriginal: linha.trim(),
      data,
      descricao: descricao.trim(),
      valor: Math.abs(valor),
      tipo: valor < 0 ? "Despesa" : "Receita",
      selecionada: true,
      indice: idx++,
    });
  }

  return resultado;
}

/**
 * Parseia um Buffer de PDF e retorna as linhas de extrato encontradas.
 * Detecta automaticamente o banco e aplica o parser correspondente.
 *
 * Nota: pdf-parse extrai o texto bruto do PDF em ordem linear —
 * funciona bem para PDFs digitais (como os dos 3 bancos analisados),
 * mas pode falhar em PDFs escaneados (imagens sem camada de texto).
 */
export async function parsearPDF(buffer: Buffer): Promise<ResultadoParsing> {
  const avisos: string[] = [];

  let texto: string;
  try {
    // Usa o módulo interno diretamente — evita bug do Next.js onde pdf-parse
    // tenta ler test/version.pdf ao ser importado via require("pdf-parse") normal
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const pdfParse = require("pdf-parse/lib/pdf-parse");
    const data = await pdfParse(buffer);
    texto = data.text;
  } catch (ex) {
    return {
      linhas: [],
      mapeamento: { data: null, descricao: null, valor: null, debito: null, credito: null, tipo: null },
      headers: [],
      linhasBrutas: [],
      avisos: ["Não foi possível extrair texto deste PDF. Pode ser um arquivo escaneado (imagem). Tente exportar o extrato em formato OFX, CSV ou XLS."],
      formato: "pdf",
    };
  }

  const layout = detectarLayout(texto);
  const linhas = texto.split("\n").map((l) => l.trim()).filter(Boolean);

  let resultado: LinhaExtrato[];
  switch (layout) {
    case "sicredi":
      resultado = parsearSicredi(linhas);
      break;
    case "rico":
      resultado = parsearRico(linhas);
      break;
    case "btg":
      resultado = parsearBTG(linhas);
      break;
    default:
      resultado = parsearGenerico(linhas);
      avisos.push("Banco não reconhecido automaticamente — usando parser genérico. Verifique se os dados estão corretos.");
  }

  if (resultado.length === 0) {
    avisos.push(
      `Nenhuma transação pôde ser extraída automaticamente do PDF (layout: ${layout}). ` +
        "Tente exportar o extrato em formato OFX ou XLS — é mais confiável que PDF."
    );
  }

  return {
    linhas: resultado,
    mapeamento: { data: 0, descricao: 1, valor: 2, debito: null, credito: null, tipo: null },
    headers: ["Data", "Descrição", "Valor"],
    linhasBrutas: resultado.slice(0, 5).map((l) => [l.data, l.descricao, String(l.valor)]),
    avisos,
    formato: "pdf",
  };
}
