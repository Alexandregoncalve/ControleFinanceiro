import type { Metadata } from "next";
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
    <html lang="pt-BR">
      <body className="antialiased bg-[#F0F4FA] text-gray-800">{children}</body>
    </html>
  );
}
