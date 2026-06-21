"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Landmark, Loader2 } from "lucide-react";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [carregando, setCarregando] = useState(false);

  async function fazerLogin(e: FormEvent) {
    e.preventDefault();
    setErro("");

    if (!login.trim() || !senha) {
      setErro("Preencha e-mail e senha.");
      return;
    }

    setCarregando(true);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ login: login.trim(), senha }),
      });
      const data = await res.json();

      if (!res.ok) {
        setErro(data.erro || "E-mail ou senha incorretos.");
        setSenha("");
        setCarregando(false);
        return;
      }

      router.push("/dashboard");
      router.refresh();
    } catch {
      setErro("Erro de conexão. Tente novamente.");
      setCarregando(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F4F7FB] px-4">
      <div className="flex w-full max-w-sm flex-col items-center gap-3">
        <Landmark size={64} className="text-[#0C447C]" />
        <h1 className="text-2xl font-bold tracking-wide text-[#0C447C]">
          FINANÇA SIMPLES
        </h1>
        <p className="text-sm text-gray-500">Acesse sua conta</p>

        <form onSubmit={fazerLogin} className="mt-4 flex w-full flex-col gap-4">
          <input
            type="email"
            placeholder="E-mail ou usuário"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
          />
          <input
            type="password"
            placeholder="Senha"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
          />

          {erro && <p className="text-sm text-red-600">{erro}</p>}

          <div className="flex justify-end">
            <Link href="/esqueci-senha" className="text-xs text-[#0C447C] hover:underline">
              Esqueci minha senha
            </Link>
          </div>

          <button
            type="submit"
            disabled={carregando}
            className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#0C447C] font-semibold text-white transition hover:bg-[#042C53] disabled:opacity-60"
          >
            {carregando ? <Loader2 className="animate-spin" size={18} /> : "ENTRAR"}
          </button>
        </form>

        <p className="mt-2 text-sm text-gray-500">
          Não tem conta?{" "}
          <Link href="/cadastro" className="font-medium text-[#0C447C] hover:underline">
            Criar conta
          </Link>
        </p>
      </div>
    </div>
  );
}
