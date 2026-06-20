import './styles/base/globals.css';
import './styles/layout/side-menu.css';
import './styles/features/auth.css';
import './styles/features/database-api.css';
import './styles/features/product-country.css';
import './styles/features/reelfarm-dashboard.css';
import './styles/features/account-pool.css';
import './styles/themes/dark-theme.css';
import './styles/themes/light-theme.css';
import './styles/features/cloud-phone.css';
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
