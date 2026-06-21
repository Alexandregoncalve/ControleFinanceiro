import { Loader2 } from "lucide-react";

/** Spinner centralizado para ocupar uma área de página inteira durante carregamento. */
export function LoadingPagina({ texto }: { texto?: string }) {
  return (
    <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-3">
      <Loader2 className="animate-spin text-[#1565C0]" size={28} />
      {texto && <p className="text-sm text-gray-400">{texto}</p>}
    </div>
  );
}

/** Spinner pequeno inline, para usar dentro de botões durante uma ação. */
export function LoadingBotao({ size = 16 }: { size?: number }) {
  return <Loader2 className="animate-spin" size={size} />;
}

/** Skeleton genérico (placeholder cinza pulsante) para qualquer bloco de conteúdo. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-gray-200 ${className}`} />;
}

/** Skeleton de um card de resumo (estilo dos cards do dashboard). */
export function SkeletonCard() {
  return (
    <div className="flex h-32 flex-1 flex-col gap-2 rounded-xl bg-white p-3.5 shadow-sm">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-6 w-32" />
      <Skeleton className="h-2 w-20" />
    </div>
  );
}

/** Skeleton de uma linha de tabela/lista. */
export function SkeletonLinha() {
  return (
    <div className="flex items-center gap-3 border-b border-gray-100 py-2.5">
      <Skeleton className="h-3 w-1/4" />
      <Skeleton className="h-3 flex-1" />
      <Skeleton className="h-3 w-16" />
    </div>
  );
}

/** Conjunto de skeletons dos cards do topo do dashboard (5 cards). */
export function SkeletonCardsResumo() {
  return (
    <div className="flex flex-wrap gap-2.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
