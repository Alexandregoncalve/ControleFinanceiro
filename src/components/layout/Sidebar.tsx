"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  List,
  Repeat,
  PlusCircle,
  Layers,
  CreditCard,
  Wallet,
  Landmark,
  AlertTriangle,
  User,
  LogOut,
  TrendingUp,
  Menu,
  X,
  Briefcase,
} from "lucide-react";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

interface NavGroup {
  titulo: string;
  itens: NavItem[];
}

// Traduzido da estrutura de grupos em menu.py
const GRUPOS: NavGroup[] = [
  {
    titulo: "GERAL",
    itens: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Extrato", href: "/extrato", icon: List },
    ],
  },
  {
    titulo: "LANÇAMENTOS",
    itens: [
      { label: "Contas Fixas", href: "/fixas", icon: Repeat },
      { label: "Avulso", href: "/avulso", icon: PlusCircle },
      { label: "Parcelas", href: "/parcelas", icon: Layers },
      { label: "Cartão de Crédito", href: "/cartao", icon: CreditCard },
    ],
  },
  {
    titulo: "FINANCEIRO",
    itens: [
      { label: "Contas", href: "/contas", icon: Wallet },
      { label: "Bancos", href: "/bancos", icon: Landmark },
      { label: "Dívidas", href: "/dividas", icon: AlertTriangle },
    ],
  },
  {
    titulo: "RENDA",
    itens: [{ label: "Vínculos de Renda", href: "/vinculos-renda", icon: Briefcase }],
  },
  {
    titulo: "CONFIGURAÇÕES",
    itens: [{ label: "Meu Cadastro", href: "/perfil", icon: User }],
  },
];

interface SidebarProps {
  nomeUsuario: string;
}

export function Sidebar({ nomeUsuario }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [abertoMobile, setAbertoMobile] = useState(false);

  // Fecha o drawer mobile automaticamente ao navegar para outra rota
  useEffect(() => {
    setAbertoMobile(false);
  }, [pathname]);

  const iniciais = nomeUsuario
    .split(" ")
    .slice(0, 2)
    .map((p) => p[0])
    .join("")
    .toUpperCase();

  async function sair() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  const conteudoMenu = (
    <>
      {/* Logo */}
      <div className="flex items-center justify-between gap-2 border-b border-gray-200 px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#1565C0]">
            <TrendingUp size={16} className="text-white" />
          </div>
          <span className="text-[13px] font-semibold">
            <span className="text-[#1565C0]">Finança</span>{" "}
            <span className="text-[#2E7D32]">Simples</span>
          </span>
        </div>
        <button
          onClick={() => setAbertoMobile(false)}
          className="text-gray-400 lg:hidden"
          aria-label="Fechar menu"
        >
          <X size={20} />
        </button>
      </div>

      {/* Navegação */}
      <nav className="flex-1 overflow-y-auto py-2">
        {GRUPOS.map((grupo) => (
          <div key={grupo.titulo}>
            <p className="px-4 pb-1 pt-2.5 text-[10px] font-medium tracking-wider text-gray-400">
              {grupo.titulo}
            </p>
            {grupo.itens.map((item) => {
              const ativo = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className="block px-2 py-0.5">
                  <div
                    className={`flex items-center gap-2.5 rounded-full px-3.5 py-2 text-[13px] transition-colors ${
                      ativo
                        ? "bg-[#E3F2FD] font-semibold text-[#1565C0]"
                        : "text-gray-600 hover:bg-gray-50"
                    }`}
                  >
                    <Icon size={16} />
                    {item.label}
                  </div>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      {/* Rodapé com usuário */}
      <div className="flex items-center gap-2 border-t border-gray-200 px-3.5 py-3">
        <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#1565C0] text-[11px] font-bold text-white">
          {iniciais}
        </div>
        <span className="flex-1 truncate text-[12px] text-gray-600">{nomeUsuario}</span>
        <button
          onClick={sair}
          title="Sair"
          className="flex-shrink-0 text-gray-400 transition hover:text-red-600"
        >
          <LogOut size={16} />
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Barra superior mobile com botão de menu — só aparece em telas pequenas */}
      <div className="flex h-12 flex-shrink-0 items-center gap-2 border-b border-gray-200 bg-white px-3 lg:hidden">
        <button
          onClick={() => setAbertoMobile(true)}
          className="text-gray-600"
          aria-label="Abrir menu"
        >
          <Menu size={22} />
        </button>
        <span className="text-[13px] font-semibold">
          <span className="text-[#1565C0]">Finança</span> <span className="text-[#2E7D32]">Simples</span>
        </span>
      </div>

      {/* Sidebar fixa — desktop */}
      <aside className="hidden h-screen w-[210px] flex-shrink-0 flex-col border-r border-gray-200 bg-white lg:flex">
        {conteudoMenu}
      </aside>

      {/* Drawer — mobile/tablet */}
      {abertoMobile && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setAbertoMobile(false)}
            aria-hidden="true"
          />
          <aside className="absolute left-0 top-0 flex h-full w-[260px] flex-col bg-white shadow-xl">
            {conteudoMenu}
          </aside>
        </div>
      )}
    </>
  );
}
