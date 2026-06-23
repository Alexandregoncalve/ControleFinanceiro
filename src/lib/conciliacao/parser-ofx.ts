/**
 * Parser OFX (Open Financial Exchange) — formato XML estruturado
 * exportado pelo Sicredi e muitos outros bancos brasileiros.
 * É o formato mais confiável de todos porque já vem estruturado
 * — sem necessidade de detectar colunas ou lidar com layouts variados.
 */

import { LinhaExtrato, MapeamentoColunas, ResultadoParsing } from "./tipos";
import { normalizarValor } from "./normalizacao";

/** Extrai o conteúdo de uma tag XML, tolerando quebras de linha e espaços */
function extrairTag(xml: string, tag: string): string | null {
  const m = xml.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`, "i"));
  return m ? m[1].trim() : null;
}

/** Converte data OFX (YYYYMMDDHHMMSS) para DD/MM/AAAA */
function converterDataOFX(dtStr: string): string | null {
  const limpo = dtStr.replace(/\[.*\]/, "").trim();
  const m = limpo.match(/^(\d{4})(\d{2})(\d{2})/);
  if (!m) return null;
  return `${m[3]}/${m[2]}/${m[1]}`;
}

export function parsearOFX(conteudo: string): ResultadoParsing {
  const avisos: string[] = [];
  const linhas: LinhaExtrato[] = [];
  const mapeamento: MapeamentoColunas = {
    data: 0, descricao: 1, valor: 2, debito: null, credito: null, tipo: null,
  };

  // Encontra todos os blocos de transação <STMTTRN>...</STMTTRN>
  const blocos = conteudo.match(/<STMTTRN>([\s\S]*?)<\/STMTTRN>/gi) ?? [];

  if (blocos.length === 0) {
    avisos.push("Nenhuma transação encontrada no arquivo OFX. Verifique se é um extrato válido.");
    return { linhas: [], mapeamento, headers: ["Data", "Descrição", "Valor"], linhasBrutas: [], avisos, formato: "csv" };
  }

  blocos.forEach((bloco, idx) => {
    const dtPosted = extrairTag(bloco, "DTPOSTED");
    const memo = extrairTag(bloco, "MEMO") || extrairTag(bloco, "NAME") || "(sem descrição)";
    const trnAmt = extrairTag(bloco, "TRNAMT");
    const trnType = extrairTag(bloco, "TRNTYPE"); // CREDIT / DEBIT / OTHER

    if (!dtPosted || !trnAmt) return;

    const data = converterDataOFX(dtPosted);
    if (!data) return;

    const valor = normalizarValor(trnAmt);
    if (valor === null) return;

    // OFX: positivo = crédito, negativo = débito (sinal já indica o tipo)
    let tipo: "Receita" | "Despesa";
    if (trnType?.toUpperCase() === "CREDIT") {
      tipo = "Receita";
    } else if (trnType?.toUpperCase() === "DEBIT") {
      tipo = "Despesa";
    } else {
      tipo = valor >= 0 ? "Receita" : "Despesa";
    }

    // Limpa o memo de caracteres estranhos vindos do charset OFX
    const descricao = memo
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .trim();

    linhas.push({
      linhaOriginal: `${data} | ${descricao} | ${trnAmt}`,
      data,
      descricao,
      valor: Math.abs(valor),
      tipo,
      selecionada: true,
      indice: idx,
    });
  });

  if (linhas.length === 0) {
    avisos.push("Arquivo OFX lido, mas nenhuma transação pôde ser processada.");
  }

  return {
    linhas,
    mapeamento,
    headers: ["Data", "Descrição", "Valor"],
    linhasBrutas: linhas.slice(0, 5).map((l) => [l.data, l.descricao, String(l.valor)]),
    avisos,
    formato: "csv", // OFX não precisa de mapeamento — tratamos como "já processado"
  };
}
