import { NextRequest } from "next/server";
import { z } from "zod";
import crypto from "crypto";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";
import { enviarEmailRecuperacaoSenha } from "@/lib/email";
import { enviarWhatsappRecuperacaoSenha } from "@/lib/whatsapp";

const schema = z.object({
  login: z.string().min(1, "Informe seu e-mail."),
  metodo: z.enum(["email", "whatsapp"]).default("email"),
});

/**
 * POST /api/auth/esqueci-senha
 * Gera um token de uso único válido por 1 hora e envia o link de redefinição
 * por e-mail (ou WhatsApp, quando disponível).
 *
 * Por segurança, SEMPRE retorna sucesso, mesmo se o e-mail não existir no banco —
 * isso evita que alguém descubra quais e-mails estão cadastrados testando aqui.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const body = await req.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { login, metodo } = parsed.data;
  const usuario = await prisma.usuario.findUnique({ where: { login: login.trim().toLowerCase() } });

  // Resposta genérica sempre, independente de o usuário existir ou não
  const respostaGenerica = {
    ok: true,
    mensagem:
      metodo === "email"
        ? "Se este e-mail estiver cadastrado, você receberá um link de redefinição em instantes."
        : "Se este número estiver cadastrado, você receberá um código por WhatsApp em instantes.",
  };

  if (!usuario) return apiOk(respostaGenerica);

  const token = crypto.randomBytes(32).toString("hex");
  const expiraEm = new Date(Date.now() + 60 * 60 * 1000); // 1 hora

  await prisma.tokenRecuperacao.create({
    data: { usuarioId: usuario.id, token, expiraEm },
  });

  const baseUrl = process.env.NEXT_PUBLIC_APP_URL || req.nextUrl.origin;
  const link = `${baseUrl}/redefinir-senha?token=${token}`;

  if (metodo === "whatsapp" && usuario.telefone) {
    const resultado = await enviarWhatsappRecuperacaoSenha(usuario.telefone, link);
    if (!resultado.ok) {
      // WhatsApp ainda não disponível — cai para e-mail automaticamente como fallback
      await enviarEmailRecuperacaoSenha(usuario.login, usuario.nome, link);
    }
  } else {
    await enviarEmailRecuperacaoSenha(usuario.login, usuario.nome, link);
  }

  return apiOk(respostaGenerica);
});
