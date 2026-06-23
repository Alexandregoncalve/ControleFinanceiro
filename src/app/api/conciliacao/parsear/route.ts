import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { processarArquivoExtrato } from "@/lib/conciliacao";

const TERMOS_BANCO: Record<string, string[]> = {
  sicredi: ["sicredi", "cooperativa"],
  btg:     ["btg", "pactual"],
  rico:    ["rico"],
};

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();

  const formData = await req.formData();
  const arquivo = formData.get("arquivo") as File | null;
  if (!arquivo) return apiErro("Nenhum arquivo enviado.");
  if (arquivo.size > 10 * 1024 * 1024) return apiErro("Arquivo muito grande. Limite: 10MB.");

  const buffer = Buffer.from(await arquivo.arrayBuffer());
  const resultado = await processarArquivoExtrato(buffer, arquivo.name);

  const bancoDetectado = resultado.bancoDetectado ?? "generico";
  const termos = TERMOS_BANCO[bancoDetectado] ?? [];

  let bancoId: number | null = null;
  let bancoNome: string | null = null;

  // 1. Busca o banco cadastrado pelo nome
  if (termos.length > 0) {
    for (const termo of termos) {
      const banco = await prisma.banco.findFirst({
        where: { usuarioId: sessao.id, nomeBanco: { contains: termo, mode: "insensitive" } },
        select: { id: true, nomeBanco: true },
      });
      if (banco) { bancoId = banco.id; bancoNome = banco.nomeBanco; break; }
    }
  }

  return apiOk({ ...resultado, bancoId, bancoNome });
});
