import { getSessao } from "@/lib/auth";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";

export const GET = comTratamentoErro(async () => {
  const sessao = await getSessao();
  return apiOk({ usuario: sessao });
});
