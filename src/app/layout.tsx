import type { Metadata } from "next";
import { Toaster } from "sonner";
import { TemaProvider } from "@/components/providers/TemaProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Finança Simples",
  description: "Controle financeiro pessoal",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <body className="antialiased bg-[var(--app-bg)] text-[var(--app-texto)]">
        <TemaProvider>
          {children}
          <Toaster
            position="top-right"
            richColors
            closeButton
            toastOptions={{
              style: { fontSize: "13px" },
            }}
          />
        </TemaProvider>
      </body>
    </html>
  );
}
