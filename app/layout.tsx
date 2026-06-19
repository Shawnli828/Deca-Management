import './globals.css';
import './dark-theme.css';
import './light-theme.css';
import './cloud-phone.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'DECAGROWTH中台',
  description: 'Deca Growth central dashboard'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
