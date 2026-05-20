'use client';

export function SideMenu({ tool, setTool }: { tool: string; setTool: (tool: 'slideshow' | 'roaster' | 'publishCheck') => void }) {
  return (
    <aside className="side-menu" aria-label="中台菜单">
      <div className="side-brand">
        <span className="brand-mark">DG<span className="brand-dot">.</span></span>
        <span>中台</span>
      </div>
      <nav className="side-nav">
        <button className={`side-nav-btn ${tool === 'slideshow' ? 'active' : ''}`} type="button" onClick={() => setTool('slideshow')}>
          <span className="side-nav-title">Slide Show</span>
          <span className="side-nav-meta">Reel Farm</span>
        </button>
        <button className={`side-nav-btn ${tool === 'roaster' ? 'active' : ''}`} type="button" onClick={() => setTool('roaster')}>
          <span className="side-nav-title">Roaster</span>
          <span className="side-nav-meta">Team Board</span>
        </button>
        <button className={`side-nav-btn ${tool === 'publishCheck' ? 'active' : ''}`} type="button" onClick={() => setTool('publishCheck')}>
          <span className="side-nav-title">发布检查</span>
          <span className="side-nav-meta">Daily Check</span>
        </button>
      </nav>
    </aside>
  );
}
