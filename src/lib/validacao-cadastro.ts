// Máscaras e validações de campo — traduzido das funções on_blur_* em cadastro.py

import { validarCPF } from "./utils";

export function maskCPF(digits: string): string {
  const d = digits.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 3) return d;
  if (d.length <= 6) return `${d.slice(0, 3)}.${d.slice(3)}`;
  if (d.length <= 9) return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6)}`;
  return `${d.slice(0, 3)}.${d.slice(3, 6)}.${d.slice(6, 9)}-${d.slice(9)}`;
}

export function maskTelefone(digits: string): string {
  const d = digits.replace(/\D/g, "").slice(0, 11);
  if (d.length <= 2) return d;
  if (d.length <= 6) return `(${d.slice(0, 2)}) ${d.slice(2)}`;
  if (d.length <= 10) return `(${d.slice(0, 2)}) ${d.slice(2, 6)}-${d.slice(6)}`;
  return `(${d.slice(0, 2)}) ${d.slice(2, 7)}-${d.slice(7)}`;
}

export function maskCEP(digits: string): string {
  const d = digits.replace(/\D/g, "").slice(0, 8);
  if (d.length <= 5) return d;
  return `${d.slice(0, 5)}-${d.slice(5)}`;
}

export function maskDataNasc(digits: string): string {
  const d = digits.replace(/\D/g, "").slice(0, 8);
  if (d.length <= 2) return d;
  if (d.length <= 4) return `${d.slice(0, 2)}/${d.slice(2)}`;
  return `${d.slice(0, 2)}/${d.slice(2, 4)}/${d.slice(4)}`;
}

export interface ValidacaoCampo {
  valido: boolean | null; // null = ainda não validado
  erro: string;
}

export function validarCpfCampo(valor: string): ValidacaoCampo {
  const digits = valor.replace(/\D/g, "");
  if (digits.length === 0) return { valido: false, erro: "CPF obrigatório" };
  if (digits.length !== 11) return { valido: false, erro: `CPF incompleto (${digits.length}/11)` };
  if (!validarCPF(digits)) return { valido: false, erro: "CPF inválido" };
  return { valido: true, erro: "" };
}

export function validarRgCampo(valor: string): ValidacaoCampo {
  const digits = valor.replace(/\D/g, "");
  if (digits.length < 7) return { valido: false, erro: "RG inválido (mín. 7 dígitos)" };
  return { valido: true, erro: "" };
}

export function validarDataNascCampo(valor: string): ValidacaoCampo {
  const digits = valor.replace(/\D/g, "");
  if (digits.length !== 8) return { valido: false, erro: "Use DD/MM/AAAA" };
  const dia = parseInt(digits.slice(0, 2));
  const mes = parseInt(digits.slice(2, 4));
  const ano = parseInt(digits.slice(4));
  const data = new Date(ano, mes - 1, dia);
  if (data.getDate() !== dia || data.getMonth() !== mes - 1) {
    return { valido: false, erro: "Data inválida" };
  }
  if (data > new Date()) return { valido: false, erro: "Data futura" };
  return { valido: true, erro: "" };
}

export function validarTelefoneCampo(valor: string): ValidacaoCampo {
  const digits = valor.replace(/\D/g, "");
  if (digits.length < 10) return { valido: false, erro: "WhatsApp inválido" };
  return { valido: true, erro: "" };
}

export function validarCepCampo(valor: string): ValidacaoCampo {
  const digits = valor.replace(/\D/g, "");
  if (digits.length !== 8) return { valido: false, erro: "CEP inválido" };
  return { valido: true, erro: "" };
}

export function validarEstadoCampo(valor: string): ValidacaoCampo {
  const v = valor.trim().toUpperCase();
  if (v.length === 2 && /^[A-Z]{2}$/.test(v)) return { valido: true, erro: "" };
  return { valido: false, erro: "UF inválida (ex: RS)" };
}

export function validarNomeCampo(valor: string): ValidacaoCampo {
  if (valor.trim().split(/\s+/).length < 2) {
    return { valido: false, erro: "Digite nome e sobrenome" };
  }
  return { valido: true, erro: "" };
}

export function validarObrigatorio(valor: string, label: string): ValidacaoCampo {
  if (valor.trim().length < 2) return { valido: false, erro: `${label} obrigatório` };
  return { valido: true, erro: "" };
}

export function validarEmailCampo(valor: string): ValidacaoCampo {
  const ok = /^[\w.-]+@[\w.-]+\.(com|com\.br|net|org)$/.test(valor.trim().toLowerCase());
  return ok ? { valido: true, erro: "" } : { valido: false, erro: "E-mail inválido" };
}

export function validarSenhaCampo(valor: string): ValidacaoCampo {
  if (valor.length < 6) return { valido: false, erro: "Mínimo 6 caracteres" };
  return { valido: true, erro: "" };
}
