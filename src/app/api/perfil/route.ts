import { NextRequest } from "next/server";
import { z } from "zod";
import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { apiOk, apiErro, comTratamentoErro } from "@/lib/api-helpers";

// Traduzido de carregar_perfil_db() em cadastro.py
export const GET = comTratamentoErro(async () => {
  const sessao = await exigirSessao();
  const perfil = await prisma.perfil.findUnique({ where: { usuarioId: sessao.id } });
  return apiOk({ perfil });
});

const perfilSchema = z.object({
  nome: z.string().min(2),
  cpf: z.string().optional(),
  rg: z.string().optional(),
  email: z.string().optional(),
  dataNasc: z.string().optional(),
  telefone: z.string().optional(),
  cep: z.string().optional(),
  logradouro: z.string().optional(),
  numero: z.string().optional(),
  complemento: z.string().optional(),
  bairro: z.string().optional(),
  cidade: z.string().optional(),
  estado: z.string().optional(),
  empresa: z.string().optional(),
  cargo: z.string().optional(),
  salario: z.number().optional(),
  diaPagamento: z.number().nullable().optional(),
  vale: z.number().optional(),
  diaVale: z.number().nullable().optional(),
});

// Traduzido de salvar_perfil_db() em cadastro.py (faz UPSERT)
export const PUT = comTratamentoErro(async (req: NextRequest) => {
  const sessao = await exigirSessao();
  const body = await req.json();
  const parsed = perfilSchema.safeParse(body);

  if (!parsed.success) {
    return apiErro(parsed.error.issues[0].message);
  }

  const dados = parsed.data;

  const perfil = await prisma.perfil.upsert({
    where: { usuarioId: sessao.id },
    update: dados,
    create: { usuarioId: sessao.id, ...dados },
  });

  return apiOk({ perfil });
});
