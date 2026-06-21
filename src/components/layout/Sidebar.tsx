"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  List,
  Repeat,
  PlusCircle,
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
      <div className="flex items-center justify-between gap-2 border-b border-white/10 px-4 py-4">
        <div className="flex items-center gap-2">
          <div
            className="flex h-7 w-7 items-center justify-center rounded-lg"
            style={{ background: "linear-gradient(135deg, #0C447C, #3B6D11)" }}
          >
            <TrendingUp size={16} className="text-white" />
          </div>
          <span className="text-[13px] font-semibold text-white">Finança Simples</span>
        </div>
        <button
          onClick={() => setAbertoMobile(false)}
          className="text-white/60 lg:hidden"
          aria-label="Fechar menu"
        >
          <X size={20} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto py-2">
        {GRUPOS.map((grupo) => (
          <div key={grupo.titulo}>
            <p className="px-4 pb-1 pt-2.5 text-[10px] font-medium tracking-wider text-white/35">
              {grupo.titulo}
            </p>
            {grupo.itens.map((item) => {
              const ativo = pathname === item.href;
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href} className="block px-2 py-0.5">
                  <div
                    className={`flex items-center gap-2.5 rounded-lg px-3.5 py-2 text-[13px] transition-colors ${
                      ativo
                        ? "border-l-2 border-[#7CC04A] bg-white/10 font-semibold text-white"
                        : "text-white/65 hover:bg-white/5 hover:text-white"
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

      <div className="flex items-center gap-2 border-t border-white/10 px-3.5 py-3">
        <div
          className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-[11px] font-bold text-white"
          style={{ background: "linear-gradient(135deg, #0C447C, #3B6D11)" }}
        >
          {iniciais}
        </div>
        <span className="flex-1 truncate text-[12px] text-white/70">{nomeUsuario}</span>
        <button
          onClick={sair}
          title="Sair"
          className="flex-shrink-0 text-white/50 transition hover:text-[#F09595]"
        >
          <LogOut size={16} />
        </button>
      </div>
    </>
  );

  return (
    <>
      <div className="flex h-12 flex-shrink-0 items-center gap-2 border-b border-[#E2E8F0] bg-white px-3 lg:hidden">
        <button onClick={() => setAbertoMobile(true)} className="text-[#0C447C]" aria-label="Abrir menu">
          <Menu size={22} />
        </button>
        <span className="text-[13px] font-semibold text-[#0C447C]">Finança Simples</span>
      </div>

      <aside
        className="hidden h-screen w-[210px] flex-shrink-0 flex-col lg:flex"
        style={{ background: "#042C53" }}
      >
        {conteudoMenu}
      </aside>

      {abertoMobile && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={() => setAbertoMobile(false)} aria-hidden="true" />
          <aside className="absolute left-0 top-0 flex h-full w-[260px] flex-col shadow-xl" style={{ background: "#042C53" }}>
            {conteudoMenu}
          </aside>
        </div>
      )}
    </>
  );
}
