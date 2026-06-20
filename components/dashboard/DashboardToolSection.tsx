import type { ReactNode } from 'react';

export function DashboardToolSection({
  active,
  children
}: {
  active: boolean;
  children: ReactNode;
}) {
  return (
    <section className={`tool-page ${active ? 'active' : ''}`}>
      {children}
    </section>
  );
}
