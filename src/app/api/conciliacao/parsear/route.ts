import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { processarArquivoExtrato } from "@/lib/conciliacao";

/**
 * POST /api/conciliacao/parsear
 * Recebe um arquivo de extrato (multipart/form-data) e retorna as
 * transações detectadas + mapeamento de colunas para confirmação na UI.
 *
 * Body (FormData):
 *   arquivo: File — o arquivo do extrato (CSV, XLS, XLSX, OFX, PDF)
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  await exigirSessao();

  const formData = await req.formData();
  const arquivo = formData.get("arquivo") as File | null;

  if (!arquivo) return apiErro("Nenhum arquivo enviado.");
  if (arquivo.size > 10 * 1024 * 1024) {
    return apiErro("Arquivo muito grande. Limite: 10MB.");
  }

  const buffer = Buffer.from(await arquivo.arrayBuffer());
  const resultado = await processarArquivoExtrato(buffer, arquivo.name);

  return apiOk(resultado);
});
