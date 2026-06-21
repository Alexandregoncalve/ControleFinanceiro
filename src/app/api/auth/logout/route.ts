import { destruirSessao } from "@/lib/auth";
import { apiOk, comTratamentoErro } from "@/lib/api-helpers";

export const POST = comTratamentoErro(async () => {
  await destruirSessao();
  return apiOk({ ok: true });
});
