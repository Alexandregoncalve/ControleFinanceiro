# Finança Simples — Next.js

Reescrita completa do sistema de controle financeiro pessoal (originalmente em
Python/Flet) usando **Next.js 15 (App Router) + TypeScript + Tailwind CSS +
Prisma + PostgreSQL**.

## Stack

- **Next.js 15** (App Router, Server Components, API Routes) — full-stack em um único projeto
- **TypeScript**
- **Tailwind CSS 4**
- **Prisma ORM** + **PostgreSQL**
- **jose** (JWT) + **bcryptjs** — autenticação por cookie httpOnly
- **zod** — validação de payloads das rotas de API
- **lucide-react** — ícones
- **recharts** — gráficos (instalado, pronto para uso se quiser evoluir os gráficos)

## Pré-requisitos

- Node.js 18.18+ (recomendado 20+)
- PostgreSQL 14+ rodando localmente ou em um serviço gerenciado (Supabase, Neon, Railway, RDS etc.)

## Instalação

```bash
# 1. Instalar dependências
npm install

# 2. Configurar variáveis de ambiente
cp .env.example .env
# Edite o .env com sua connection string real do Postgres e um JWT_SECRET forte
```

Edite o arquivo `.env`:

```env
DATABASE_URL="postgresql://usuario:senha@localhost:5432/financas"
JWT_SECRET="gere-uma-string-aleatoria-longa-com-openssl-rand-base64-32"
```

Para gerar um `JWT_SECRET` seguro:

```bash
openssl rand -base64 32
```

```bash
# 3. Criar as tabelas no banco a partir do schema Prisma
npx prisma db push

# 4. (Opcional) Gerar dados de exemplo — cria usuário teste@exemplo.com / senha 123456
npm run db:seed

# 5. Rodar em desenvolvimento
npm run dev
```

Acesse **http://localhost:3000** — você será redirecionado para `/login`.
Crie uma conta nova em "Criar conta", ou use o usuário de seed acima se você
rodou o passo 4.

## Scripts disponíveis

| Comando | Descrição |
|---|---|
| `npm run dev` | Roda o servidor de desenvolvimento |
| `npm run build` | Gera o Prisma Client e cria o build de produção |
| `npm start` | Roda o build de produção (rodar `build` antes) |
| `npm run db:push` | Sincroniza o schema Prisma com o banco (sem migrations versionadas) |
| `npm run db:studio` | Abre o Prisma Studio (interface visual do banco) |
| `npm run db:seed` | Cria um usuário de teste com dados de exemplo |

> Para produção/times, prefira `npx prisma migrate dev` (cria migrations
> versionadas) em vez de `db push`, que é mais adequado para prototipagem.

## Estrutura do projeto

```
src/
├── app/
│   ├── (app)/              # Páginas privadas (com sidebar) — exige login
│   │   ├── dashboard/
│   │   ├── extrato/
│   │   ├── avulso/
│   │   ├── fixas/
│   │   ├── parcelas/
│   │   ├── contas/         # Categorias e subcontas
│   │   ├── bancos/         # Bancos, cartões, transferências
│   │   ├── cartao/         # Fatura do cartão de crédito
│   │   ├── dividas/
│   │   └── perfil/         # Edição de dados pessoais
│   ├── api/                # Todas as rotas de API (Route Handlers)
│   ├── cadastro/           # Criação de conta (pública)
│   ├── login/               # Login (pública)
│   └── layout.tsx
├── components/
│   ├── dashboard/          # Componentes específicos do dashboard
│   ├── forms/               # Formulários reutilizáveis
│   ├── layout/              # Sidebar
│   └── ui/                  # Inputs, seletores genéricos
├── hooks/                   # Hooks de busca de dados (useBancos, useSubcontas)
├── lib/                     # auth.ts, prisma.ts, utils.ts, validações
└── types/                   # Tipos compartilhados (DTOs)

prisma/
├── schema.prisma            # Schema completo do banco
└── seed.ts                  # Script opcional de dados de exemplo
```

## O que foi portado da versão Python

✅ Autenticação (login, cadastro, sessão)
✅ Dashboard completo (cards de resumo, saúde financeira, histórico, top
gastos, orçamento mensal, metas do mês)
✅ Lançamento avulso (com parcelamento de cartão de crédito e categoria real
do gasto)
✅ Contas fixas (listagem de pendentes + baixa em lote)
✅ Parcelas (visão agrupada de compras parceladas)
✅ Cadastro de contas (categorias e subcontas)
✅ Bancos e cartões (CRUD completo + transferências entre bancos)
✅ Cartão de crédito (fatura do mês, limite, parcelas futuras)
✅ Extrato (listagem com filtros e edição)
✅ Controle de dívidas (parceladas com conta fixa automática, ou pagamento livre)

## O que ficou para uma v2

🔲 **Conciliação bancária** com parsing de extratos PDF/OFX (BTG, Sicredi)
— módulo mais complexo do sistema original, propositalmente deixado de fora
desta primeira versão conforme combinado, para focar no restante do sistema.

## Notas técnicas importantes

- **Datas são armazenadas como texto** no formato `DD/MM/AAAA`, exatamente
  como no sistema Python original — isso preserva compatibilidade caso você
  queira migrar dados diretamente do banco Postgres antigo para este, sem
  necessidade de conversão de formato de data.
- **Autenticação via cookie JWT httpOnly** (sete dias de validade),
  substituindo o `page.session` do Flet.
- O middleware (`src/middleware.ts`) protege todas as rotas exceto `/login`
  e `/cadastro`.
