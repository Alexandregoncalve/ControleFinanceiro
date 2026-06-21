import { redirect } from "next/navigation";
import { getSessao } from "@/lib/auth";

export default async function HomePage() {
  const sessao = await getSessao();
  redirect(sessao ? "/dashboard" : "/login");
}
