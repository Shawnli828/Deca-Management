'use client';

export function SideMenu({
  tool,
  setTool,
  collapsed,
  onToggle
}: {
  tool: string;
  setTool: (tool: 'growth' | 'dashboard' | 'slideshow' | 'cloneSlideshow' | 'publishCheck' | 'apiKeys') => void;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const items = [
    { id: 'growth' as const, title: 'Growth', meta: 'Daily Metrics', icon: 'G' },
    { id: 'dashboard' as const, title: 'Dashboard', meta: 'Overview', icon: 'D' },
    { id: 'slideshow' as const, title: 'Slide Show', meta: 'Reel Farm', icon: 'S' },
    { id: 'cloneSlideshow' as const, title: 'Clone Slide Show', meta: 'Museon', icon: 'C' },
    { id: 'publishCheck' as const, title: '发布检查', meta: 'Daily Check', icon: 'P' },
    { id: 'apiKeys' as const, title: 'API Key', meta: 'Access Tokens', icon: 'K' }
  ];

  return (
    <aside className={`side-menu ${collapsed ? 'collapsed' : ''}`} aria-label="中台菜单">
      <div className="side-brand">
        <span className="brand-mark">DG<span className="brand-dot">.</span></span>
        <span className="side-brand-text">中台</span>
        <button className="side-collapse-btn" type="button" onClick={onToggle} aria-label={collapsed ? '展开菜单' : '收起菜单'}>
          {collapsed ? '›' : '‹'}
        </button>
      </div>
      <nav className="side-nav">
        {items.map(item => (
          <button className={`side-nav-btn ${tool === item.id ? 'active' : ''}`} type="button" onClick={() => setTool(item.id)} title={collapsed ? item.title : undefined} key={item.id}>
            <span className="side-nav-icon">{item.icon}</span>
            <span className="side-nav-copy">
              <span className="side-nav-title">{item.title}</span>
              <span className="side-nav-meta">{item.meta}</span>
            </span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
