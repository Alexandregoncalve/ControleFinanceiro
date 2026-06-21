import { Resend } from "resend";

/**
 * Cliente Resend para envio de e-mails transacionais (recuperação de senha,
 * verificação de conta). Veja https://resend.com — plano grátis até 3000 e-mails/mês.
 *
 * Por padrão (sem domínio próprio verificado), o Resend só permite enviar a partir
 * de "onboarding@resend.dev" e apenas PARA o e-mail da conta que criou a chave de API.
 * Para enviar a qualquer destinatário, é preciso verificar um domínio próprio no
 * painel do Resend e trocar EMAIL_REMETENTE no .env.
 *
 * A instância é criada sob demanda (lazy) em vez de no carregamento do módulo,
 * porque o construtor do SDK lança erro se RESEND_API_KEY não existir — isso
 * quebraria o build/dev mesmo em rotas que não chegam a enviar e-mail de fato
 * (ex: quando a variável ainda não foi configurada em ambiente de desenvolvimento).
 */
let _resend: Resend | null = null;
function getResend(): Resend | null {
  if (!process.env.RESEND_API_KEY) return null;
  if (!_resend) _resend = new Resend(process.env.RESEND_API_KEY);
  return _resend;
}

const REMETENTE = process.env.EMAIL_REMETENTE || "Finança Simples <onboarding@resend.dev>";

interface EnvioResultado {
  ok: boolean;
  erro?: string;
}

export async function enviarEmailRecuperacaoSenha(
  destino: string,
  nomeUsuario: string,
  linkRecuperacao: string
): Promise<EnvioResultado> {
  const resend = getResend();
  if (!resend) {
    console.error("[email] RESEND_API_KEY não configurada no .env");
    return { ok: false, erro: "Serviço de e-mail não configurado." };
  }

  try {
    const { error } = await resend.emails.send({
      from: REMETENTE,
      to: destino,
      subject: "Redefinir sua senha — Finança Simples",
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
          <h2 style="color: #1565C0;">Finança Simples</h2>
          <p>Olá, ${nomeUsuario}!</p>
          <p>Recebemos uma solicitação para redefinir sua senha. Clique no botão abaixo para criar uma nova senha:</p>
          <p style="text-align: center; margin: 24px 0;">
            <a href="${linkRecuperacao}"
               style="background: #1565C0; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">
              Redefinir senha
            </a>
          </p>
          <p style="color: #888; font-size: 13px;">Este link expira em 1 hora. Se você não solicitou isso, pode ignorar este e-mail com segurança.</p>
        </div>
      `,
    });

    if (error) {
      console.error("[email] erro ao enviar:", error);
      return { ok: false, erro: "Não foi possível enviar o e-mail." };
    }
    return { ok: true };
  } catch (ex) {
    console.error("[email] erro inesperado:", ex);
    return { ok: false, erro: "Erro ao enviar e-mail." };
  }
}

export async function enviarEmailCodigoVerificacao(
  destino: string,
  nomeUsuario: string,
  codigo: string
): Promise<EnvioResultado> {
  const resend = getResend();
  if (!resend) {
    console.error("[email] RESEND_API_KEY não configurada no .env");
    return { ok: false, erro: "Serviço de e-mail não configurado." };
  }

  try {
    const { error } = await resend.emails.send({
      from: REMETENTE,
      to: destino,
      subject: `${codigo} é o seu código de verificação — Finança Simples`,
      html: `
        <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;">
          <h2 style="color: #1565C0;">Finança Simples</h2>
          <p>Olá, ${nomeUsuario}!</p>
          <p>Seu código de verificação é:</p>
          <p style="text-align: center; margin: 24px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #1565C0;">${codigo}</span>
          </p>
          <p style="color: #888; font-size: 13px;">Este código expira em 10 minutos.</p>
        </div>
      `,
    });

    if (error) {
      console.error("[email] erro ao enviar:", error);
      return { ok: false, erro: "Não foi possível enviar o e-mail." };
    }
    return { ok: true };
  } catch (ex) {
    console.error("[email] erro inesperado:", ex);
    return { ok: false, erro: "Erro ao enviar e-mail." };
  }
}
