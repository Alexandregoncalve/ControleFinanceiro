"use client";

import { useState, useEffect, FormEvent, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Landmark, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { apiFetch } from "@/lib/api-fetch";

function RedefinirSenhaConteudo() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [verificando, setVerificando] = useState(true);
  const [tokenValido, setTokenValido] = useState(false);
  const [motivoInvalido, setMotivoInvalido] = useState("");

  const [senha, setSenha] = useState("");
  const [senha2, setSenha2] = useState("");
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [sucesso, setSucesso] = useState(false);

  useEffect(() => {
    if (!token) {
      setVerificando(false);
      setTokenValido(false);
      setMotivoInvalido("Link inválido.");
      return;
    }
    apiFetch<{ valido: boolean; motivo?: string }>(
      `/api/auth/redefinir-senha?token=${encodeURIComponent(token)}`,
      { toastErro: false }
    ).then((resultado) => {
      setVerificando(false);
      if (resultado.ok && resultado.data) {
        setTokenValido(resultado.data.valido);
        setMotivoInvalido(resultado.data.motivo || "");
      } else {
        setTokenValido(false);
        setMotivoInvalido("Não foi possível validar o link.");
      }
    });
  }, [token]);

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");

    if (senha.length < 6) {
      setErro("A senha deve ter ao menos 6 caracteres.");
      return;
    }
    if (senha !== senha2) {
      setErro("As senhas não coincidem.");
      return;
    }

    setSalvando(true);
    const resultado = await apiFetch("/api/auth/redefinir-senha", {
      method: "POST",
      body: JSON.stringify({ token, novaSenha: senha }),
      toastErro: false,
    });
    setSalvando(false);

    if (resultado.ok) {
      setSucesso(true);
      setTimeout(() => router.push("/login"), 2500);
    } else {
      setErro(resultado.erro || "Erro ao redefinir senha.");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F4F7FB] dark:bg-[#0F172A] px-4">
      <div className="flex w-full max-w-sm flex-col items-center gap-3">
        <Landmark size={56} className="text-[#0C447C] dark:text-blue-300" />
        <h1 className="text-xl font-bold tracking-wide text-[#0C447C] dark:text-blue-300">NOVA SENHA</h1>

        {verificando ? (
          <div className="mt-6">
            <Loader2 className="animate-spin text-[#0C447C] dark:text-blue-300" size={28} />
          </div>
        ) : sucesso ? (
          <div className="mt-4 flex flex-col items-center gap-3 text-center">
            <CheckCircle2 size={40} className="text-[#3B6D11] dark:text-green-400" />
            <p className="text-sm text-gray-600 dark:text-gray-300">Senha redefinida com sucesso! Redirecionando para o login...</p>
          </div>
        ) : !tokenValido ? (
          <div className="mt-4 flex flex-col items-center gap-4 text-center">
            <XCircle size={40} className="text-[#A32D2D]" />
            <p className="text-sm text-gray-600 dark:text-gray-300">{motivoInvalido}</p>
            <Link href="/esqueci-senha" className="text-sm font-medium text-[#0C447C] hover:underline">
              Solicitar um novo link
            </Link>
          </div>
        ) : (
          <form onSubmit={salvar} className="mt-4 flex w-full flex-col gap-4">
            <input
              type="password"
              placeholder="Nova senha"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-white/15 px-4 py-3 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
            />
            <input
              type="password"
              placeholder="Confirmar nova senha"
              value={senha2}
              onChange={(e) => setSenha2(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-white/15 px-4 py-3 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
            />

            {erro && <p className="text-sm text-red-600">{erro}</p>}

            <button
              type="submit"
              disabled={salvando}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#0C447C] font-semibold text-white transition hover:bg-[#042C53] disabled:opacity-60"
            >
              {salvando ? <Loader2 className="animate-spin" size={18} /> : "REDEFINIR SENHA"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function RedefinirSenhaPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center"><Loader2 className="animate-spin text-[#0C447C] dark:text-blue-300" size={28} /></div>}>
      <RedefinirSenhaConteudo />
    </Suspense>
  );
}
