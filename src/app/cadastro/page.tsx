import { FormularioCadastro } from "@/components/forms/FormularioCadastro";

export default function CadastroPage() {
  return (
    <div className="min-h-screen bg-[#F0F4FA]">
      <div className="mx-auto max-w-4xl">
        <FormularioCadastro novoUsuario={true} />
      </div>
    </div>
  );
}
