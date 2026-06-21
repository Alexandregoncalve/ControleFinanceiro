import { redirect } from "next/navigation";
import { getSessao } from "@/lib/auth";
import { Sidebar } from "@/components/layout/Sidebar";

export const dynamic = "force-dynamic";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const sessao = await getSessao();

  // Camada extra de proteção além do middleware (defesa em profundidade)
  if (!sessao) {
    redirect("/login");
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#F0F4FA]">
      <Sidebar nomeUsuario={sessao.nome} />
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
