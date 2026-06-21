import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */

  // Libera o domínio do túnel ngrok para acessar recursos internos de
  // desenvolvimento (hot reload etc). Sem isso o Next bloqueia por segurança
  // qualquer origem que não seja localhost. Ajuste/adicione outros domínios
  // aqui se o endereço do ngrok mudar no futuro.
  allowedDevOrigins: ["precut-random-depress.ngrok-free.dev"],
};

export default nextConfig;