import { NextRequest } from "next/server";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { processarArquivoExtrato } from "@/lib/conciliacao";

/**
 * Termos de busca por banco detectado — usados para encontrar automaticamente
 * a subconta cadastrada que corresponde ao extrato importado.
 */
const TERMOS_BUSCA: Record<string, string[]> = {
  sicredi: ["sicredi", "cooperativa"],
  btg: ["btg", "pactual"],
  rico: ["rico"],
  ofx: [], // OFX genérico — não tenta auto-detectar
  generico: [],
};

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();

  const formData = await req.formData();
  const arquivo = formData.get("arquivo") as File | null;

  if (!arquivo) return apiErro("Nenhum arquivo enviado.");
  if (arquivo.size > 10 * 1024 * 1024) return apiErro("Arquivo muito grande. Limite: 10MB.");

  const buffer = Buffer.from(await arquivo.arrayBuffer());
  const resultado = await processarArquivoExtrato(buffer, arquivo.name);

  // Tenta encontrar automaticamente a subconta que corresponde ao banco detectado
  const banco = resultado.bancoDetectado ?? "generico";
  const termos = TERMOS_BUSCA[banco] ?? [];

  let subcontaSugeridaId: number | null = null;
  let subcontaSugeridaNome: string | null = null;

  if (termos.length > 0) {
    // Busca a subconta do usuário cujo nome contenha algum dos termos do banco
    for (const termo of termos) {
      const subconta = await prisma.subconta.findFirst({
        where: {
          usuarioId: sessao.id,
          nome: { contains: termo, mode: "insensitive" },
        },
        select: { id: true, nome: true },
      });
      if (subconta) {
        subcontaSugeridaId = subconta.id;
        subcontaSugeridaNome = subconta.nome;
        break;
      }
    }

    // Se não achou pelo nome da subconta, tenta pelo nome do banco vinculado
    if (!subcontaSugeridaId) {
      const banco_obj = await prisma.banco.findFirst({
        where: {
          usuarioId: sessao.id,
          nomeBanco: { contains: termos[0], mode: "insensitive" },
        },
        select: { id: true, nomeBanco: true },
      });

      if (banco_obj) {
        // Pega a primeira subconta vinculada a este banco via transações
        const transacao = await prisma.transacao.findFirst({
          where: { usuarioId: sessao.id, bancoId: banco_obj.id },
          select: { subcontaId: true, subconta: { select: { nome: true } } },
        });
        if (transacao) {
          subcontaSugeridaId = transacao.subcontaId;
          subcontaSugeridaNome = transacao.subconta.nome;
        }
      }
    }
  }

  return apiOk({
    ...resultado,
    subcontaSugeridaId,
    subcontaSugeridaNome,
  });
});
