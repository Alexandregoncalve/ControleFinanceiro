import { NextRequest } from "next/server";
import { z } from "zod";
import { criarUsuario, criarSessao } from "@/lib/auth";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

const cadastroSchema = z.object({
  nome: z.string().min(2, "Digite nome e sobrenome."),
  login: z.string().email("E-mail inválido."),
  senha: z.string().min(6, "A senha deve ter ao menos 6 caracteres."),
});

export const POST = comTratamentoErro(async (req: NextRequest) => {
  const body = await req.json();
  const parsed = cadastroSchema.safeParse(body);

  if (!parsed.success) {
    return apiErro(parsed.error.issues[0].message);
  }

  const { nome, login, senha } = parsed.data;
  const resultado = await criarUsuario(nome.trim(), login.trim().toLowerCase(), senha);

  if (!resultado.ok) {
    return apiErro(resultado.erro);
  }

  await criarSessao({ id: resultado.id, nome: nome.trim(), login: login.trim().toLowerCase() });

  return apiOk({ id: resultado.id }, 201);
});
