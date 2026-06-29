import type { ReactNode } from 'react';

type WorkspaceHeaderProps = {
  kicker: string;
  title: string;
  description: string;
  actions: ReactNode;
  className?: string;
};

export function WorkspaceHeader({
  kicker,
  title,
  description,
  actions,
  className = ''
}: WorkspaceHeaderProps) {
  return (
    <header className={`workspace-header ${className}`.trim()}>
      <div>
        <p className="dashboard-kicker">{kicker}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {actions}
    </header>
  );
}
