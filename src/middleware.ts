import { NextRequest, NextResponse } from "next/server";
import { jwtVerify } from "jose";

// Equivalente a ROTAS_SEM_AUTH em main.py: rotas que não exigem login.
// Nota: "/cadastro" aqui é só para CRIAR conta nova (sem sessão).
// A edição de perfil de um usuário já logado vive em "/perfil" (dentro do grupo autenticado).
const ROTAS_PUBLICAS = ["/login", "/cadastro"];

const JWT_SECRET = new TextEncoder().encode(
  process.env.JWT_SECRET || "dev-secret-troque-em-producao"
);
const COOKIE_NAME = "financa_session";

async function temSessaoValida(req: NextRequest): Promise<boolean> {
  const token = req.cookies.get(COOKIE_NAME)?.value;
  if (!token) return false;
  try {
    await jwtVerify(token, JWT_SECRET);
    return true;
  } catch {
    return false;
  }
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Não interfere em rotas de API, assets estáticos ou arquivos internos do Next
  if (
    pathname.startsWith("/api") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/icons") ||
    pathname === "/favicon.ico"
  ) {
    return NextResponse.next();
  }

  const autenticado = await temSessaoValida(req);
  const ehRotaPublica = ROTAS_PUBLICAS.includes(pathname);

  // Usuário logado tentando acessar /login -> manda para o dashboard
  if (autenticado && pathname === "/login") {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  // Usuário não logado tentando acessar rota privada -> manda para /login
  if (!autenticado && !ehRotaPublica) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
