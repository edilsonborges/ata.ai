import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'ata.ai',
  description: 'Analise automatizada de reunioes',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
