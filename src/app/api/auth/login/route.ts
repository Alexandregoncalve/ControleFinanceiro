import { NextRequest } from "next/server";
import { z } from "zod";
import { autenticar, criarSessao } from "@/lib/auth";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const loginSchema = z.object({
  login: z.string().min(1, "Informe o e-mail ou usuário."),
  senha: z.string().min(1, "Informe a senha."),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const body = await req.json();
  const parsed = loginSchema.safeParse(body);

  if (!parsed.success) {
    return apiErro(parsed.error.issues[0].message);
  }

  const { login, senha } = parsed.data;
  const usuario = await autenticar(login.trim(), senha);

  if (!usuario) {
    return apiErro("E-mail ou senha incorretos.", 401);
  }

  await criarSessao(usuario);

  return apiOk({ usuario });
});
