import bcrypt from "bcryptjs";
import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";
import { prisma } from "./prisma";

const COOKIE_NAME = "financa_session";
const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "dev-secret-troque-em-producao"
);
const SESSION_DURATION = "7d";

export interface SessionUser {
  id: number;
  nome: string;
  login: string;
}

// ── Senhas ──────────────────────────────────────────────────────────────

export async function hashSenha(senha: string): Promise<string> {
  return bcrypt.hash(senha, 10);
}

export async function verificarSenha(senha: string, hash: string): Promise<boolean> {
  try {
    return await bcrypt.compare(senha, hash);
  } catch {
    return false;
  }
}

// ── Criação e autenticação de usuário ──────────────────────────────────
// Traduzido de criar_usuario() e autenticar() em database.py

export async function criarUsuario(
  nome: string,
  login: string,
  senha: string
): Promise<{ ok: true; id: number } | { ok: false; erro: string }> {
  try {
    const existente = await prisma.usuario.findUnique({ where: { login } });
    if (existente) {
      return { ok: false, erro: "Este e-mail já está cadastrado." };
    }

    const senhaHash = await hashSenha(senha);
    const usuario = await prisma.usuario.create({
      data: { nome, login, senha: senhaHash },
    });

    await criarDadosIniciais(usuario.id);

    return { ok: true, id: usuario.id };
  } catch (ex) {
    console.error("[criarUsuario]", ex);
    return { ok: false, erro: "Erro interno ao criar usuário." };
  }
}

export async function autenticar(
  login: string,
  senha: string
): Promise<SessionUser | null> {
  try {
    const usuario = await prisma.usuario.findUnique({ where: { login } });
    if (usuario && (await verificarSenha(senha, usuario.senha))) {
      return { id: usuario.id, nome: usuario.nome, login: usuario.login };
    }
    return null;
  } catch (ex) {
    console.error("[autenticar]", ex);
    return null;
  }
}

// ── Sessão via cookie JWT (equivalente a page.session no Flet) ────────

export async function criarSessao(user: SessionUser): Promise<void> {
  const token = await new SignJWT({ ...user })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(SESSION_DURATION)
    .sign(JWT_SECRET);

  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7, // 7 dias
  });
}

export async function destruirSessao(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(COOKIE_NAME);
}

export async function getSessao(): Promise<SessionUser | null> {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get(COOKIE_NAME)?.value;
    if (!token) return null;

    const { payload } = await jwtVerify(token, JWT_SECRET);
    return {
      id: payload.id as number,
      nome: payload.nome as string,
      login: payload.login as string,
    };
  } catch {
    return null;
  }
}

/** Lança erro 401 se não houver sessão. Usar em rotas de API protegidas. */
export async function exigirSessao(): Promise<SessionUser> {
  const sessao = await getSessao();
  if (!sessao) {
    throw new Error("UNAUTHENTICATED");
  }
  return sessao;
}

// ── Dados iniciais de um novo usuário ──────────────────────────────────
// Traduzido de _criar_dados_iniciais() em database.py

async function criarDadosIniciais(uid: number): Promise<void> {
  const catReceitas = await prisma.categoria.create({
    data: { usuarioId: uid, nome: "RECEITAS", tipo: "Receita" },
  });
  const catFixas = await prisma.categoria.create({
    data: { usuarioId: uid, nome: "DESPESAS FIXAS", tipo: "Despesa" },
  });
  const catVariaveis = await prisma.categoria.create({
    data: { usuarioId: uid, nome: "DESPESAS VARIÁVEIS", tipo: "Despesa" },
  });
  const catTransporte = await prisma.categoria.create({
    data: { usuarioId: uid, nome: "TRANSPORTE", tipo: "Despesa" },
  });
  const catTransferencias = await prisma.categoria.create({
    data: { usuarioId: uid, nome: "TRANSFERÊNCIAS", tipo: "Despesa" },
  });

  const subcontas = [
    { categoriaId: catReceitas.id, nome: "SALÁRIO / PRO-LABORE", fixa: 1 },
    { categoriaId: catReceitas.id, nome: "ALUGUÉIS RECEBIDOS", fixa: 0 },
    { categoriaId: catReceitas.id, nome: "OUTRAS RECEITAS", fixa: 0 },
    { categoriaId: catFixas.id, nome: "ALUGUEL", fixa: 1 },
    { categoriaId: catFixas.id, nome: "CONDOMINIO", fixa: 1 },
    { categoriaId: catFixas.id, nome: "ENERGIA ELÉTRICA", fixa: 1 },
    { categoriaId: catFixas.id, nome: "ÁGUA", fixa: 1 },
    { categoriaId: catFixas.id, nome: "INTERNET", fixa: 1 },
    { categoriaId: catFixas.id, nome: "CELULAR", fixa: 1 },
    { categoriaId: catFixas.id, nome: "SEGUROS / ASSINATURAS", fixa: 1 },
    { categoriaId: catFixas.id, nome: "DAS / MEI", fixa: 1 },
    { categoriaId: catVariaveis.id, nome: "MERCADO", fixa: 0 },
    { categoriaId: catVariaveis.id, nome: "REFEIÇÕES / LAZER", fixa: 0 },
    { categoriaId: catVariaveis.id, nome: "FARMÁCIA / SAÚDE", fixa: 0 },
    { categoriaId: catVariaveis.id, nome: "ACADEMIA", fixa: 0 },
    { categoriaId: catVariaveis.id, nome: "OUTRAS DESPESAS", fixa: 0 },
    { categoriaId: catTransporte.id, nome: "COMBUSTÍVEL", fixa: 0 },
    { categoriaId: catTransporte.id, nome: "MANUTENÇÃO VEÍCULO", fixa: 0 },
    { categoriaId: catTransporte.id, nome: "UBER / TAXI", fixa: 0 },
    { categoriaId: catTransferencias.id, nome: "TRANSFERÊNCIAS", fixa: 0 },
  ];

  await prisma.subconta.createMany({
    data: subcontas.map((s) => ({ usuarioId: uid, ...s })),
  });
}
