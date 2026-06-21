/**
 * Script opcional de seed: cria um usuário de teste com categorias/subcontas padrão,
 * útil para começar a explorar o sistema sem precisar passar pela tela de cadastro.
 *
 * Rodar com: npm run db:seed
 */
import "dotenv/config";
import { PrismaClient } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import bcrypt from "bcryptjs";

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL });
const prisma = new PrismaClient({ adapter });

async function main() {
  const login = "teste@exemplo.com";
  const senha = "123456";

  const existente = await prisma.usuario.findUnique({ where: { login } });
  if (existente) {
    console.log(`Usuário de teste já existe: ${login}`);
    return;
  }

  const senhaHash = await bcrypt.hash(senha, 10);
  const usuario = await prisma.usuario.create({
    data: { nome: "Usuário Teste", login, senha: senhaHash },
  });

  const catReceitas = await prisma.categoria.create({
    data: { usuarioId: usuario.id, nome: "RECEITAS", tipo: "Receita" },
  });
  const catFixas = await prisma.categoria.create({
    data: { usuarioId: usuario.id, nome: "DESPESAS FIXAS", tipo: "Despesa" },
  });
  const catVariaveis = await prisma.categoria.create({
    data: { usuarioId: usuario.id, nome: "DESPESAS VARIÁVEIS", tipo: "Despesa" },
  });

  await prisma.subconta.createMany({
    data: [
      { usuarioId: usuario.id, categoriaId: catReceitas.id, nome: "SALÁRIO / PRO-LABORE", fixa: 1 },
      { usuarioId: usuario.id, categoriaId: catFixas.id, nome: "ALUGUEL", fixa: 1, orcamento: 1500 },
      { usuarioId: usuario.id, categoriaId: catFixas.id, nome: "INTERNET", fixa: 1, orcamento: 100 },
      { usuarioId: usuario.id, categoriaId: catVariaveis.id, nome: "MERCADO", fixa: 0 },
      { usuarioId: usuario.id, categoriaId: catVariaveis.id, nome: "CARTAO DE CREDITO", fixa: 0 },
    ],
  });

  await prisma.banco.create({
    data: {
      usuarioId: usuario.id,
      nomeBanco: "Banco Exemplo",
      saldoInicial: 1000,
      dataCriacao: "01/01/2026",
      agencia: "0001",
      numeroConta: "123456",
    },
  });

  console.log(`✅ Usuário de teste criado: ${login} / senha: ${senha}`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });