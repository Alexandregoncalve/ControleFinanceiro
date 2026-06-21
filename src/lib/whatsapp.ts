/**
 * Módulo de envio de WhatsApp via Twilio.
 *
 * STATUS: estrutura pronta, mas DESLIGADA até as credenciais Twilio serem configuradas
 * no .env (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM).
 *
 * Para ativar:
 * 1. Criar conta em https://www.twilio.com (tem trial grátis com crédito)
 * 2. Ativar o "WhatsApp Sandbox" (para testes) ou solicitar número comercial aprovado (produção)
 * 3. Rodar: npm install twilio
 * 4. Preencher as 3 variáveis no .env
 * 5. Descomentar o código de envio real abaixo
 *
 * Enquanto isso, qualquer chamada a essas funções retorna erro amigável e loga no console,
 * sem quebrar o restante do fluxo (o app continua funcionando normalmente via e-mail).
 */

interface EnvioResultado {
  ok: boolean;
  erro?: string;
}

function twilioConfigurado(): boolean {
  return !!(
    process.env.TWILIO_ACCOUNT_SID &&
    process.env.TWILIO_AUTH_TOKEN &&
    process.env.TWILIO_WHATSAPP_FROM
  );
}

export async function enviarWhatsappCodigoVerificacao(
  telefone: string,
  codigo: string
): Promise<EnvioResultado> {
  if (!twilioConfigurado()) {
    console.warn(
      "[whatsapp] Twilio não configurado ainda. Configure TWILIO_ACCOUNT_SID, " +
        "TWILIO_AUTH_TOKEN e TWILIO_WHATSAPP_FROM no .env para ativar o envio por WhatsApp."
    );
    return {
      ok: false,
      erro: "Verificação por WhatsApp ainda não está disponível. Use e-mail por enquanto.",
    };
  }

  // ── Quando o Twilio estiver configurado, descomente este bloco ──────────
  //
  // const twilio = require("twilio")(
  //   process.env.TWILIO_ACCOUNT_SID,
  //   process.env.TWILIO_AUTH_TOKEN
  // );
  //
  // try {
  //   await twilio.messages.create({
  //     from: `whatsapp:${process.env.TWILIO_WHATSAPP_FROM}`,
  //     to: `whatsapp:${telefone}`,
  //     body: `Seu código de verificação Finança Simples é: ${codigo}\n\nVálido por 10 minutos.`,
  //   });
  //   return { ok: true };
  // } catch (ex) {
  //   console.error("[whatsapp] erro ao enviar:", ex);
  //   return { ok: false, erro: "Não foi possível enviar o código por WhatsApp." };
  // }

  return { ok: false, erro: "WhatsApp ainda não está disponível." };
}

export async function enviarWhatsappRecuperacaoSenha(
  telefone: string,
  linkRecuperacao: string
): Promise<EnvioResultado> {
  if (!twilioConfigurado()) {
    console.warn("[whatsapp] Twilio não configurado ainda.");
    return {
      ok: false,
      erro: "Recuperação por WhatsApp ainda não está disponível. Use e-mail por enquanto.",
    };
  }

  // Mesma estrutura de enviarWhatsappCodigoVerificacao — implementar quando o Twilio estiver pronto.
  return { ok: false, erro: "WhatsApp ainda não está disponível." };
}
