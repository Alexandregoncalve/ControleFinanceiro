"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { Landmark, Loader2, Mail, MessageCircle, ArrowLeft } from "lucide-react";
import { apiFetch } from "@/lib/api-fetch";

export default function EsqueciSenhaPage() {
  const [login, setLogin] = useState("");
  const [metodo, setMetodo] = useState<"email" | "whatsapp">("email");
  const [carregando, setCarregando] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [mensagem, setMensagem] = useState("");

  async function solicitar(e: FormEvent) {
    e.preventDefault();
    if (!login.trim()) return;

    setCarregando(true);
    const resultado = await apiFetch<{ mensagem: string }>("/api/auth/esqueci-senha", {
      method: "POST",
      body: JSON.stringify({ login: login.trim(), metodo }),
      toastErro: false, // erro aqui é tratado inline, não como toast
    });
    setCarregando(false);

    if (resultado.ok && resultado.data) {
      setEnviado(true);
      setMensagem(resultado.data.mensagem);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F4F7FB] dark:bg-[#0F172A] px-4">
      <div className="flex w-full max-w-sm flex-col items-center gap-3">
        <Landmark size={56} className="text-[#0C447C] dark:text-blue-300" />
        <h1 className="text-xl font-bold tracking-wide text-[#0C447C] dark:text-blue-300">RECUPERAR SENHA</h1>

        {enviado ? (
          <div className="mt-4 flex flex-col items-center gap-4 text-center">
            <div className="rounded-lg bg-[#EAF3DE] dark:bg-green-900/40 p-4">
              <p className="text-sm text-[#3B6D11] dark:text-green-400">{mensagem}</p>
            </div>
            <Link
              href="/login"
              className="flex items-center gap-1.5 text-sm font-medium text-[#0C447C] hover:underline"
            >
              <ArrowLeft size={14} /> Voltar para o login
            </Link>
          </div>
        ) : (
          <form onSubmit={solicitar} className="mt-4 flex w-full flex-col gap-4">
            <p className="text-center text-sm text-gray-500 dark:text-gray-400 dark:text-gray-500">
              Informe seu e-mail cadastrado para receber as instruções de redefinição de senha.
            </p>

            <input
              type="email"
              placeholder="E-mail cadastrado"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              className="w-full rounded-lg border border-gray-300 dark:border-white/15 px-4 py-3 text-sm outline-none focus:border-[#0C447C] focus:ring-1 focus:ring-[#0C447C]"
            />

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMetodo("email")}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2.5 text-xs font-medium transition ${
                  metodo === "email"
                    ? "border-[#0C447C] bg-[#E6F1FB] dark:bg-blue-900/40 text-[#0C447C] dark:text-blue-300"
                    : "border-gray-300 dark:border-white/15 text-gray-500 dark:text-gray-400 dark:text-gray-500"
                }`}
              >
                <Mail size={14} /> E-mail
              </button>
              <button
                type="button"
                onClick={() => setMetodo("whatsapp")}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2.5 text-xs font-medium transition ${
                  metodo === "whatsapp"
                    ? "border-[#3B6D11] bg-[#EAF3DE] dark:bg-green-900/40 text-[#3B6D11] dark:text-green-400"
                    : "border-gray-300 dark:border-white/15 text-gray-500 dark:text-gray-400 dark:text-gray-500"
                }`}
              >
                <MessageCircle size={14} /> WhatsApp
              </button>
            </div>

            <button
              type="submit"
              disabled={carregando}
              className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-[#0C447C] font-semibold text-white transition hover:bg-[#042C53] disabled:opacity-60"
            >
              {carregando ? <Loader2 className="animate-spin" size={18} /> : "ENVIAR INSTRUÇÕES"}
            </button>

            <Link
              href="/login"
              className="flex items-center justify-center gap-1.5 text-sm text-gray-500 hover:underline"
            >
              <ArrowLeft size={14} /> Voltar para o login
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
