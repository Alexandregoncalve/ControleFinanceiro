import { NextRequest } from "next/server";
import { z } from "zod";
import { prisma, PrismaTransaction } from "@/lib/prisma";
import { hashSenha } from "@/lib/auth";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const schema = z.object({
  token: z.string().min(1, "Token inválido."),
  novaSenha: z.string().min(6, "A senha deve ter ao menos 6 caracteres."),
});

/**
 * POST /api/auth/redefinir-senha
 * Valida o token (existe, não expirou, não foi usado ainda) e troca a senha.
 * Marca o token como usado para impedir reuso do mesmo link.
 */
export const POST = comTratamentoErro(async (req: NextRequest) => {
  const body = await req.json();
  const parsed = schema.safeParse(body);
  if (!parsed.success) return apiErro(parsed.error.issues[0].message);

  const { token, novaSenha } = parsed.data;

  const registro = await prisma.tokenRecuperacao.findUnique({ where: { token } });

  if (!registro) return apiErro("Link inválido ou expirado.", 400);
  if (registro.usadoEm) return apiErro("Este link já foi utilizado.", 400);
  if (registro.expiraEm < new Date()) return apiErro("Este link expirou. Solicite um novo.", 400);

  const senhaHash = await hashSenha(novaSenha);

  await prisma.$transaction(async (tx: PrismaTransaction) => {
    await tx.usuario.update({ where: { id: registro.usuarioId }, data: { senha: senhaHash } });
    await tx.tokenRecuperacao.update({ where: { id: registro.id }, data: { usadoEm: new Date() } });
  });

  return apiOk({ ok: true, mensagem: "Senha redefinida com sucesso! Você já pode fazer login." });
});

/**
 * GET /api/auth/redefinir-senha?token=...
 * Usado pela página de redefinição para checar se o token ainda é válido
 * ANTES de mostrar o formulário de nova senha (evita formulário inútil para link expirado).
 */
export const GET = comTratamentoErro(async (req: NextRequest) => {
  const token = req.nextUrl.searchParams.get("token");
  if (!token) return apiErro("Token não informado.", 400);

  const registro = await prisma.tokenRecuperacao.findUnique({ where: { token } });

  if (!registro) return apiOk({ valido: false, motivo: "Link inválido." });
  if (registro.usadoEm) return apiOk({ valido: false, motivo: "Este link já foi utilizado." });
  if (registro.expiraEm < new Date()) return apiOk({ valido: false, motivo: "Este link expirou." });

  return apiOk({ valido: true });
});
