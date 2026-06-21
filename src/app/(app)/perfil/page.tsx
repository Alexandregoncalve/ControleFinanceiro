import { exigirSessao } from "@/lib/auth";
import { prisma } from "@/lib/prisma";
import { FormularioCadastro } from "@/components/forms/FormularioCadastro";

export const dynamic = "force-dynamic";

export default async function PerfilPage() {
  const sessao = await exigirSessao();
  const perfil = await prisma.perfil.findUnique({ where: { usuarioId: sessao.id } });

  return (
    <div className="mx-auto max-w-4xl">
      <FormularioCadastro
        novoUsuario={false}
        perfilInicial={
          perfil
            ? {
                nome: perfil.nome ?? "",
                cpf: perfil.cpf ?? "",
                rg: perfil.rg ?? "",
                email: perfil.email ?? "",
                dataNasc: perfil.dataNasc ?? "",
                telefone: perfil.telefone ?? "",
                cep: perfil.cep ?? "",
                logradouro: perfil.logradouro ?? "",
                numero: perfil.numero ?? "",
                complemento: perfil.complemento ?? "",
                bairro: perfil.bairro ?? "",
                cidade: perfil.cidade ?? "",
                estado: perfil.estado ?? "",
                empresa: perfil.empresa ?? "",
                cargo: perfil.cargo ?? "",
                salario: perfil.salario ?? 0,
                diaPagamento: perfil.diaPagamento,
                vale: perfil.vale ?? 0,
                diaVale: perfil.diaVale,
              }
            : null
        }
      />
    </div>
  );
}
