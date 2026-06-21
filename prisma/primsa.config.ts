// Prisma 7 moveu a configuração de conexão com o banco para fora do schema.prisma.
// Este arquivo substitui o antigo bloco `url = env("DATABASE_URL")` dentro do
// datasource do schema.prisma. Veja: https://pris.ly/d/config-datasource
//
// IMPORTANTE: a CLI do Prisma não carrega o .env automaticamente — por isso
// usamos dotenv.config() de forma explícita (não apenas "dotenv/config" como import),
// garantindo que process.env.DATABASE_URL já exista antes de defineConfig rodar.
import * as dotenv from "dotenv";
import { defineConfig } from "prisma/config";

dotenv.config();

if (!process.env.DATABASE_URL) {
  throw new Error(
    'DATABASE_URL não encontrada. Verifique se o arquivo ".env" existe na raiz do projeto ' +
      "e contém a linha DATABASE_URL=... (sem espaços antes do =)."
  );
}

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: {
    path: "prisma/migrations",
    seed: "tsx prisma/seed.ts",
  },
  datasource: {
    url: process.env.DATABASE_URL,
  },
});