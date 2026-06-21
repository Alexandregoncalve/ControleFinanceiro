import { PrismaClient, Prisma } from "@prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";

// Prisma 7 exige um "driver adapter" explícito para conectar ao banco em runtime
// (não basta mais só a connection string no schema). Veja: https://pris.ly/d/client-constructor
const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL });

// Evita criar múltiplas instâncias do PrismaClient durante hot-reload em desenvolvimento.
// Padrão recomendado oficialmente pela Vercel/Prisma para Next.js.
const globalForPrisma = global as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    adapter,
    log: process.env.NODE_ENV === "development" ? ["error", "warn"] : ["error"],
  });

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

/**
 * Tipo correto para o parâmetro recebido dentro de prisma.$transaction(async (tx) => ...).
 * Não é o mesmo tipo de `PrismaClient` (não tem $connect/$disconnect/$on/$extends),
 * por isso usar `typeof prisma` ali dá erro de tipo no build.
 */
export type PrismaTransaction = Prisma.TransactionClient;
