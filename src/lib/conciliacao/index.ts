import "server-only";

/**
 * Dispatcher central do módulo de conciliação.
 * Recebe o arquivo (como Buffer) + nome e chama o parser correto.
 */

import { ResultadoParsing } from "./tipos";
import { parsearCSVOuExcel } from "./parser-csv-excel";
import { parsearOFX } from "./parser-ofx";
import { parsearPDF } from "./parser-pdf";

export type FormatoSuportado = "csv" | "xlsx" | "xls" | "ofx" | "pdf";

export function detectarFormato(nomeArquivo: string): FormatoSuportado | null {
  const ext = nomeArquivo.toLowerCase().split(".").pop();
  if (ext === "csv") return "csv";
  if (ext === "xlsx") return "xlsx";
  if (ext === "xls") return "xls";
  if (ext === "ofx" || ext === "qfx") return "ofx";
  if (ext === "pdf") return "pdf";
  return null;
}

/** Processa um arquivo de extrato bancário e retorna as transações detectadas */
export async function processarArquivoExtrato(
  buffer: Buffer,
  nomeArquivo: string
): Promise<ResultadoParsing> {
  const formato = detectarFormato(nomeArquivo);

  if (!formato) {
    return {
      linhas: [],
      mapeamento: { data: null, descricao: null, valor: null, debito: null, credito: null, tipo: null },
      headers: [],
      linhasBrutas: [],
      avisos: [
        `Formato ".${nomeArquivo.split(".").pop()}" não suportado. ` +
          "Use: CSV, Excel (.xlsx/.xls), OFX ou PDF.",
      ],
      formato: "csv",
    };
  }

  if (formato === "pdf") {
    return parsearPDF(buffer);
  }

  if (formato === "ofx") {
    const texto = buffer.toString("latin1"); // OFX geralmente é ANSI/Latin-1
    return parsearOFX(texto);
  }

  // CSV, XLS, XLSX
  return parsearCSVOuExcel(buffer, nomeArquivo);
}

export { processarArquivoExtrato as default };
