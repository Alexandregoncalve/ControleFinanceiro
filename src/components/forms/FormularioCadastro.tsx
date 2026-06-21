"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { UserPlus, Save, Briefcase } from "lucide-react";
import { CampoValidado } from "@/components/ui/CampoValidado";
import { InputMoeda } from "@/components/ui/InputMoeda";
import {
  maskCPF,
  maskTelefone,
  maskCEP,
  maskDataNasc,
  validarCpfCampo,
  validarRgCampo,
  validarDataNascCampo,
  validarTelefoneCampo,
  validarCepCampo,
  validarEstadoCampo,
  validarNomeCampo,
  validarObrigatorio,
  validarEmailCampo,
  validarSenhaCampo,
  ValidacaoCampo,
} from "@/lib/validacao-cadastro";

interface PerfilData {
  nome: string;
  cpf: string;
  rg: string;
  email: string;
  dataNasc: string;
  telefone: string;
  cep: string;
  logradouro: string;
  numero: string;
  complemento: string;
  bairro: string;
  cidade: string;
  estado: string;
  empresa: string;
  cargo: string;
  salario: number;
  diaPagamento: number | null;
  vale: number;
  diaVale: number | null;
}

const VAZIO: PerfilData = {
  nome: "",
  cpf: "",
  rg: "",
  email: "",
  dataNasc: "",
  telefone: "",
  cep: "",
  logradouro: "",
  numero: "",
  complemento: "",
  bairro: "",
  cidade: "",
  estado: "",
  empresa: "",
  cargo: "",
  salario: 0,
  diaPagamento: null,
  vale: 0,
  diaVale: null,
};

interface FormularioCadastroProps {
  /** true = criar conta nova (mostra campos de login/senha); false = editar perfil de quem já está logado */
  novoUsuario: boolean;
  /** dados existentes, para o caso de edição de perfil */
  perfilInicial?: Partial<PerfilData> | null;
}

export function FormularioCadastro({ novoUsuario, perfilInicial }: FormularioCadastroProps) {
  const router = useRouter();

  const [dados, setDados] = useState<PerfilData>({ ...VAZIO, ...perfilInicial });
  const [login, setLogin] = useState("");
  const [senha, setSenha] = useState("");
  const [senha2, setSenha2] = useState("");

  const [valid, setValid] = useState<Record<string, ValidacaoCampo>>({});
  const [msg, setMsg] = useState<{ texto: string; cor: "red" | "green" } | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (perfilInicial) setDados((prev) => ({ ...prev, ...perfilInicial }));
  }, [perfilInicial]);

  function set<K extends keyof PerfilData>(campo: K, valor: PerfilData[K]) {
    setDados((prev) => ({ ...prev, [campo]: valor }));
  }

  function validar(campo: string, fn: () => ValidacaoCampo) {
    setValid((prev) => ({ ...prev, [campo]: fn() }));
  }

  function validarTudo(): string[] {
    const erros: string[] = [];
    const novoValid: Record<string, ValidacaoCampo> = {};

    if (novoUsuario) {
      novoValid.login = /^[\w.-]+@[\w.-]+\.(com|com\.br|net|org)$/.test(login.trim().toLowerCase())
        ? { valido: true, erro: "" }
        : { valido: false, erro: "E-mail inválido" };
      novoValid.senha = validarSenhaCampo(senha);
      novoValid.senha2 =
        senha2 === senha ? { valido: true, erro: "" } : { valido: false, erro: "Senhas não coincidem" };

      if (!novoValid.login.valido) erros.push("E-mail de login");
      if (!novoValid.senha.valido) erros.push("Senha");
      if (!novoValid.senha2.valido) erros.push("Confirmação de senha");
    }

    novoValid.nome = validarNomeCampo(dados.nome);
    novoValid.cpf = validarCpfCampo(dados.cpf);
    novoValid.rg = validarRgCampo(dados.rg);
    novoValid.dataNasc = validarDataNascCampo(dados.dataNasc);
    novoValid.telefone = validarTelefoneCampo(dados.telefone);
    novoValid.cep = validarCepCampo(dados.cep);
    novoValid.logradouro = validarObrigatorio(dados.logradouro, "Endereço");
    novoValid.bairro = validarObrigatorio(dados.bairro, "Bairro");
    novoValid.cidade = validarObrigatorio(dados.cidade, "Cidade");
    novoValid.estado = validarEstadoCampo(dados.estado);

    const labels: Record<string, string> = {
      nome: "Nome",
      cpf: "CPF",
      rg: "RG",
      dataNasc: "Data de nascimento",
      telefone: "WhatsApp",
      cep: "CEP",
      logradouro: "Endereço",
      bairro: "Bairro",
      cidade: "Cidade",
      estado: "UF",
    };
    for (const campo of Object.keys(labels)) {
      if (!novoValid[campo].valido) erros.push(labels[campo]);
    }

    setValid((prev) => ({ ...prev, ...novoValid }));
    return erros;
  }

  async function salvar() {
    setMsg(null);
    const erros = validarTudo();
    if (erros.length > 0) {
      const nomes = erros.slice(0, 3).join(", ");
      const extra = erros.length > 3 ? ` e mais ${erros.length - 3}...` : "";
      setMsg({ texto: `⚠️ Corrija: ${nomes}${extra}`, cor: "red" });
      return;
    }

    setSalvando(true);

    try {
      if (novoUsuario) {
        const res = await fetch("/api/auth/cadastro", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ nome: dados.nome.trim(), login: login.trim(), senha }),
        });
        const data = await res.json();
        if (!res.ok) {
          setMsg({ texto: `❌ ${data.erro}`, cor: "red" });
          setSalvando(false);
          return;
        }
      }

      const resPerfil = await fetch("/api/perfil", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...dados, email: novoUsuario ? login.trim() : dados.email }),
      });

      if (!resPerfil.ok) {
        const data = await resPerfil.json();
        setMsg({ texto: `❌ ${data.erro}`, cor: "red" });
        setSalvando(false);
        return;
      }

      setMsg({ texto: "✅ Cadastro salvo com sucesso!", cor: "green" });
      setSalvando(false);

      if (novoUsuario) {
        router.push("/dashboard");
        router.refresh();
      }
    } catch {
      setMsg({ texto: "❌ Erro ao salvar. Tente novamente.", cor: "red" });
      setSalvando(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 p-6">
      <h1 className="text-xl font-bold text-[#1565C0]">
        {novoUsuario ? "CRIAR CONTA" : "MEU CADASTRO"}
      </h1>
      <hr />

      {novoUsuario && (
        <section className="rounded-xl bg-[#E8F5E9] p-4">
          <h2 className="mb-3 text-sm font-bold text-[#2E7D32]">🔐 DADOS DE ACESSO</h2>
          <div className="flex flex-wrap gap-3">
            <CampoValidado
              label="E-mail (será seu login)"
              value={login}
              onChange={setLogin}
              onBlur={() =>
                validar("login", () =>
                  /^[\w.-]+@[\w.-]+\.(com|com\.br|net|org)$/.test(login.trim().toLowerCase())
                    ? { valido: true, erro: "" }
                    : { valido: false, erro: "E-mail inválido" }
                )
              }
              validacao={valid.login}
              className="w-72"
            />
            <CampoValidado
              label="Senha (mín. 6 caracteres)"
              type="password"
              value={senha}
              onChange={setSenha}
              onBlur={() => validar("senha", () => validarSenhaCampo(senha))}
              validacao={valid.senha}
              className="w-56"
            />
            <CampoValidado
              label="Confirmar senha"
              type="password"
              value={senha2}
              onChange={setSenha2}
              onBlur={() =>
                validar("senha2", () =>
                  senha2 === senha ? { valido: true, erro: "" } : { valido: false, erro: "Senhas não coincidem" }
                )
              }
              validacao={valid.senha2}
              className="w-56"
            />
          </div>
        </section>
      )}

      <section className="rounded-xl bg-[#E3F2FD] p-4">
        <h2 className="mb-3 text-sm font-bold text-[#1565C0]">👤 1. IDENTIFICAÇÃO E CONTATO</h2>
        <div className="flex flex-wrap gap-3">
          <CampoValidado
            label="Nome Completo"
            value={dados.nome}
            onChange={(v) => set("nome", v)}
            onBlur={() => validar("nome", () => validarNomeCampo(dados.nome))}
            validacao={valid.nome}
            className="w-full max-w-md"
          />
          {!novoUsuario && (
            <label className="flex w-72 flex-col gap-1">
              <span className="text-xs font-medium text-gray-600">E-mail de login</span>
              <input
                type="email"
                value={dados.email}
                disabled
                className="w-full cursor-not-allowed rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500"
              />
              <span className="text-[10px] text-gray-400">
                Para alterar o e-mail de login, entre em contato com o suporte.
              </span>
            </label>
          )}
        </div>
        <div className="mt-3 flex flex-wrap gap-3">
          <CampoValidado
            label="CPF"
            value={dados.cpf}
            onChange={(v) => set("cpf", maskCPF(v))}
            onBlur={() => validar("cpf", () => validarCpfCampo(dados.cpf))}
            validacao={valid.cpf}
            maxLength={14}
            className="w-44"
          />
          <CampoValidado
            label="RG"
            value={dados.rg}
            onChange={(v) => set("rg", v)}
            onBlur={() => validar("rg", () => validarRgCampo(dados.rg))}
            validacao={valid.rg}
            maxLength={12}
            className="w-40"
          />
          <CampoValidado
            label="Nascimento (DD/MM/AAAA)"
            value={dados.dataNasc}
            onChange={(v) => set("dataNasc", maskDataNasc(v))}
            onBlur={() => validar("dataNasc", () => validarDataNascCampo(dados.dataNasc))}
            validacao={valid.dataNasc}
            maxLength={10}
            className="w-44"
          />
          <CampoValidado
            label="WhatsApp"
            value={dados.telefone}
            onChange={(v) => set("telefone", maskTelefone(v))}
            onBlur={() => validar("telefone", () => validarTelefoneCampo(dados.telefone))}
            validacao={valid.telefone}
            maxLength={15}
            className="w-44"
          />
        </div>
      </section>

      <section className="rounded-xl bg-[#FFF3E0] p-4">
        <h2 className="mb-1 text-sm font-bold text-[#E65100]">🏠 2. ENDEREÇO RESIDENCIAL</h2>
        <p className="mb-3 text-[11px] italic text-gray-500">💡 Preencha o endereço manualmente.</p>
        <div className="flex flex-wrap gap-3">
          <CampoValidado
            label="CEP"
            value={dados.cep}
            onChange={(v) => set("cep", maskCEP(v))}
            onBlur={() => validar("cep", () => validarCepCampo(dados.cep))}
            validacao={valid.cep}
            maxLength={9}
            className="w-32"
          />
          <CampoValidado
            label="Endereço"
            value={dados.logradouro}
            onChange={(v) => set("logradouro", v)}
            onBlur={() => validar("logradouro", () => validarObrigatorio(dados.logradouro, "Endereço"))}
            validacao={valid.logradouro}
            className="w-72"
          />
          <CampoValidado label="Número" value={dados.numero} onChange={(v) => set("numero", v)} className="w-24" />
          <CampoValidado
            label="Complemento"
            value={dados.complemento}
            onChange={(v) => set("complemento", v)}
            className="w-44"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-3">
          <CampoValidado
            label="Bairro"
            value={dados.bairro}
            onChange={(v) => set("bairro", v)}
            onBlur={() => validar("bairro", () => validarObrigatorio(dados.bairro, "Bairro"))}
            validacao={valid.bairro}
            className="w-52"
          />
          <CampoValidado
            label="Cidade"
            value={dados.cidade}
            onChange={(v) => set("cidade", v)}
            onBlur={() => validar("cidade", () => validarObrigatorio(dados.cidade, "Cidade"))}
            validacao={valid.cidade}
            className="w-52"
          />
          <CampoValidado
            label="UF"
            value={dados.estado}
            onChange={(v) => set("estado", v.toUpperCase())}
            onBlur={() => validar("estado", () => validarEstadoCampo(dados.estado))}
            validacao={valid.estado}
            maxLength={2}
            className="w-20"
          />
        </div>
      </section>

      <div className="flex items-center gap-2 rounded-lg bg-[#FFF3E0] px-3 py-2.5">
        <Briefcase size={16} className="flex-shrink-0 text-[#E65100]" />
        <p className="text-xs text-[#E65100]">
          Salário, vale-transporte, vale-alimentação e outros vínculos de renda agora ficam em{" "}
          <Link href="/vinculos-renda" className="font-semibold underline">
            Vínculos de Renda
          </Link>
          .
        </p>
      </div>

      {msg && (
        <div
          className={`rounded-lg p-3 text-sm font-medium ${
            msg.cor === "red" ? "bg-[#FFEBEE] text-red-700" : "bg-[#E8F5E9] text-green-700"
          }`}
        >
          {msg.texto}
        </div>
      )}

      <div className="flex justify-center">
        <button
          onClick={salvar}
          disabled={salvando}
          className="flex h-12 items-center gap-2 rounded-lg bg-[#1565C0] px-8 font-semibold text-white transition hover:bg-[#1257A8] disabled:opacity-60"
        >
          {novoUsuario ? <UserPlus size={18} /> : <Save size={18} />}
          {novoUsuario ? "CRIAR CONTA" : "SALVAR ALTERAÇÕES"}
        </button>
      </div>
    </div>
  );
}
