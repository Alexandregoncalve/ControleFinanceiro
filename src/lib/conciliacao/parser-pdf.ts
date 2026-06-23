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
 * Parser Sicredi: linhas compactas sem separadores entre campos.
 * Formato: DD/MM/AAAADESCRICAODOCUMENTO-VALOR,XXSALDO,XX
 *
 * Quando o código do documento é numérico e fica colado ao valor
 * (ex: "8549561.100,00"), usa o saldo como validador para corrigir.
 */
function parsearSicredi(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  const RE_2_VALORES = /(-?(?:\d{1,3}\.)*\d{1,3},\d{2})(-?(?:\d{1,3}\.)*\d{1,3},\d{2})$/;

  function tentarCorrigirValor(valorStr: string, saldo: number): number {
    const valor = parseFloat(valorStr.replace(/\./g, "").replace(",", "."));
    // Se o valor está dentro de 50x do saldo, está correto
    if (Math.abs(valor) <= Math.abs(saldo) * 50 + 500) return valor;

    // Tenta remover dígitos do início do primeiro grupo até achar valor razoável
    const semSinal = valorStr.replace(/^-/, "");
    const negativo = valorStr.startsWith("-");
    const partes = semSinal.split(".");
    const primeiroGrupo = partes[0];

    for (let i = 1; i < primeiroGrupo.length; i++) {
      const candidato = primeiroGrupo.slice(i) + (partes.length > 1 ? "." + partes.slice(1).join(".") : "");
      if (/^\d{1,3}(?:\.\d{3})*,\d{2}$/.test(candidato)) {
        const v = parseFloat(candidato.replace(/\./g, "").replace(",", "."));
        if (Math.abs(v) <= Math.abs(saldo) * 50 + 500) {
          return negativo ? -v : v;
        }
      }
    }
    return valor; // retorna o original se não achou candidato melhor
  }

  for (const linha of linhas) {
    if (deveIgnorar(linha)) continue;

    const dataMatch = linha.match(/^(\d{2}\/\d{2}\/\d{4})/);
    if (!dataMatch) continue;
    const data = dataMatch[1];
    const resto = linha.slice(10);

    const m = resto.match(RE_2_VALORES);
    if (!m) continue;

    const saldo = parseFloat(m[2].replace(/\./g, "").replace(",", "."));
    const valor = tentarCorrigirValor(m[1], saldo);
    if (isNaN(valor) || valor === 0) continue;

    const antesDoValor = resto.slice(0, resto.length - m[0].length);
    const codigoSobrou = antesDoValor.match(/\d+$/)?.[0] ?? "";
    const desc = antesDoValor
      .slice(0, antesDoValor.length - codigoSobrou.length)
      .replace(/[A-Z][A-Z0-9_]{1,29}$/, "")
      .trim() || antesDoValor.trim();

    resultado.push({
      linhaOriginal: linha,
      data,
      descricao: desc || "(sem descrição)",
      valor: Math.abs(valor),
      tipo: valor < 0 ? "Despesa" : "Receita",
      selecionada: true,
      indice: idx++,
    });
  }

  return resultado;
}

/**
 * Parser Rico Corretora: o PDF extrai as linhas sem espaço entre os campos.
 * Formatos:
 * - Linha simples: "DD/MM/AAAA DD/MM/AAAA DESCRIÇÃO R$ VALOR R$ SALDO"
 *   (tudo junto: "22/06/202622/06/2026JUROS S/...R$ 0,26R$ 0,55")
 * - Linhas multi-linha: data sozinha, depois descrição, depois valores
 *   ("10/06/202610/06/2026", "TED BCO...", "-R$ 389,25R$ 0,00")
 */
function parsearRico(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  // Regex para linha simples: duas datas coladas + descrição + R$ valor + R$ saldo
  const RE_LINHA_COMPLETA = /^(\d{2}\/\d{2}\/\d{4})\d{2}\/\d{2}\/\d{4}(.+?)(-?R\$\s*[\d.,]+)(R\$\s*[\d.,]+)$/;
  // Regex para linha de valores: "-R$ 999,99R$ 999,99" ou "R$ 999,99R$ 999,99"
  const RE_VALORES = /^(-?R\$\s*[\d.,]+)(R\$\s*[\d.,]+)$/;
  // Regex para linha que é só datas coladas: "DD/MM/AAAA DD/MM/AAAA" (sem descrição)
  const RE_SO_DATAS = /^(\d{2}\/\d{2}\/\d{4})\d{2}\/\d{2}\/\d{4}$/;

  let pendente: { data: string; descricao: string } | null = null;
  let descPendente: string[] = [];

  for (const linha of linhas) {
    if (deveIgnorar(linha)) { pendente = null; descPendente = []; continue; }
    // Ignora cabeçalho da tabela
    if (/^LiqMovHistórico/i.test(linha)) continue;

    // Linha simples completa: tudo numa linha
    const mCompleto = linha.match(RE_LINHA_COMPLETA);
    if (mCompleto) {
      const data = mCompleto[1];
      const descricao = mCompleto[2].trim().replace(/\s+\d+\s*$/, "").trim(); // remove número de cota do final
      const valorStr = mCompleto[3].replace(/R\$\s*/, "").trim();
      const valor = normalizarValor(valorStr);
      if (valor !== null && valor !== 0) {
        resultado.push({
          linhaOriginal: linha,
          data,
          descricao: descricao || "(sem descrição)",
          valor: Math.abs(valor),
          tipo: valor < 0 ? "Despesa" : "Receita",
          selecionada: true,
          indice: idx++,
        });
      }
      pendente = null; descPendente = [];
      continue;
    }

    // Linha só com datas: início de registro multi-linha
    const mSoDatas = linha.match(RE_SO_DATAS);
    if (mSoDatas) {
      pendente = { data: mSoDatas[1], descricao: "" };
      descPendente = [];
      continue;
    }

    // Linha de valores: fecha o registro multi-linha
    const mValores = linha.match(RE_VALORES);
    if (mValores && pendente) {
      const valorStr = mValores[1].replace(/R\$\s*/, "").trim();
      const valor = normalizarValor(valorStr);
      const descricao = descPendente.join(" ").replace(/\s+\d+\s*$/, "").trim();
      if (valor !== null && valor !== 0) {
        resultado.push({
          linhaOriginal: `${pendente.data} ${descricao} | ${linha}`,
          data: pendente.data,
          descricao: descricao || "(sem descrição)",
          valor: Math.abs(valor),
          tipo: valor < 0 ? "Despesa" : "Receita",
          selecionada: true,
          indice: idx++,
        });
      }
      pendente = null; descPendente = [];
      continue;
    }

    // Linha de descrição intermediária (multi-linha)
    if (pendente) {
      descPendente.push(linha.trim());
    }
  }

  return resultado;
}

/**
 * Parser BTG Pactual: o PDF extrai em 2 linhas por transação.
 * Linha 1: "DD/MM/AAAA DESCRIÇÃO"
 * Linha 2: "SALDO,XXVALOR,XX" (saldo e valor sem separador, valor pode ser débito ou crédito)
 *
 * Para saber se é débito ou crédito, compara o saldo com o saldo anterior:
 * - Se saldo diminuiu → débito (despesa)
 * - Se saldo aumentou → crédito (receita)
 */
function parsearBTG(linhas: string[]): LinhaExtrato[] {
  const resultado: LinhaExtrato[] = [];
  let idx = 0;

  const RE_DATA_DESC = /^(\d{2}\/\d{2}\/\d{4})\s+(.+)$/;
  const RE_2_VALORES = /^(-?(?:\d{1,3}\.)*\d{1,3},\d{2})(\d{1,3}(?:\.\d{3})*,\d{2})$/;

  let saldoAnterior: number | null = null;
  let pendente: { data: string; descricao: string } | null = null;

  for (const linha of linhas) {
    // Linha de saldo inicial do BTG: "Saldo Inicial996,00" (sem espaço entre texto e valor)
    // Precisa ser verificada ANTES do filtro deveIgnorar pois o filtro a ignoraria
    const saldoIni = linha.match(/Saldo\s*Inicial\s*(-?[\d.,]+)/i);
    if (saldoIni) {
      saldoAnterior = normalizarValor(saldoIni[1]);
      pendente = null;
      continue;
    }

    if (deveIgnorar(linha)) {
      pendente = null;
      continue;
    }

    // Linha 1: data + descrição
    const mDesc = linha.match(RE_DATA_DESC);
    if (mDesc) {
      pendente = { data: mDesc[1], descricao: mDesc[2].trim() };
      continue;
    }

    // Linha 2: saldo+valor colados (ex: "836,00160,00" ou "37,901.100,00")
    if (pendente) {
      const mVal = linha.match(RE_2_VALORES);
      if (mVal) {
        const novoSaldo = normalizarValor(mVal[1]);
        const valor = normalizarValor(mVal[2]);

        if (novoSaldo !== null && valor !== null && valor > 0) {
          // Tipo: se saldo caiu → débito, se subiu → crédito
          const tipo: "Receita" | "Despesa" =
            saldoAnterior !== null && novoSaldo < saldoAnterior ? "Despesa" : "Receita";

          resultado.push({
            linhaOriginal: `${pendente.data} ${pendente.descricao} | ${linha}`,
            data: pendente.data,
            descricao: pendente.descricao,
            valor,
            tipo,
            selecionada: true,
            indice: idx++,
          });

          saldoAnterior = novoSaldo;
        }
      }
      pendente = null;
    }
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
    // Importa lib/pdf-parse.js diretamente (não index.js) para evitar o código
    // de teste que pdf-parse v1.x executa quando é o módulo raiz — isso causava
    // "Unexpected token ':'" durante o build do Next.js
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const pdfParse = require("pdf-parse/lib/pdf-parse");
    const data = await pdfParse(buffer);
    texto = data.text || "";
    if (!texto.trim()) {
      return {
        linhas: [],
        mapeamento: { data: null, descricao: null, valor: null, debito: null, credito: null, tipo: null },
        headers: [],
        linhasBrutas: [],
        avisos: ["O PDF não contém texto extraível. Pode ser um arquivo escaneado (imagem). Tente exportar em formato OFX, CSV ou XLS."],
        formato: "pdf",
      };
    }
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
