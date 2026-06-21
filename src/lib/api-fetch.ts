import { toast } from "sonner";

interface ApiFetchOptions extends RequestInit {
  /** Mensagem de sucesso a exibir como toast. Se omitida, não mostra toast de sucesso. */
  mensagemSucesso?: string;
  /** Mensagem de erro padrão, usada quando a API não retorna um campo "erro" específico. */
  mensagemErroPadrao?: string;
  /** Se true (padrão), mostra toast automaticamente em caso de erro. */
  toastErro?: boolean;
}

interface ApiFetchResult<T> {
  ok: boolean;
  status: number;
  data: T | null;
  erro: string | null;
}

/**
 * Wrapper sobre fetch() para chamadas à nossa própria API interna, com:
 * - Content-Type JSON automático quando há body
 * - Parse de erro padronizado (campo "erro" retornado pelas rotas via apiErro())
 * - Toast de sucesso/erro automático (pode ser desligado)
 *
 * Substitui o padrão repetido em quase toda página de "fetch + if (res.ok) setMsg(...) else setMsg(...)".
 */
export async function apiFetch<T = unknown>(
  url: string,
  options: ApiFetchOptions = {}
): Promise<ApiFetchResult<T>> {
  const { mensagemSucesso, mensagemErroPadrao, toastErro = true, ...fetchOptions } = options;

  const headers: HeadersInit = { ...(fetchOptions.headers || {}) };
  if (fetchOptions.body && typeof fetchOptions.body === "string") {
    (headers as Record<string, string>)["Content-Type"] = "application/json";
  }

  try {
    const res = await fetch(url, { ...fetchOptions, headers });
    const data = await res.json().catch(() => null);

    if (!res.ok) {
      const mensagem = data?.erro || mensagemErroPadrao || "Ocorreu um erro. Tente novamente.";
      if (toastErro) toast.error(mensagem);
      return { ok: false, status: res.status, data: null, erro: mensagem };
    }

    if (mensagemSucesso) toast.success(mensagemSucesso);
    return { ok: true, status: res.status, data: data as T, erro: null };
  } catch {
    const mensagem = "Erro de conexão. Verifique sua internet e tente novamente.";
    if (toastErro) toast.error(mensagem);
    return { ok: false, status: 0, data: null, erro: mensagem };
  }
}
