'use client';

import { FormEvent, useState } from 'react';

export function AuthGate({ onLogin }: { onLogin: (username: string, password: string) => Promise<void> }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await onLogin(username.trim(), password);
      setPassword('');
    } catch (err: any) {
      setError(err?.message || '登录失败，请重新输入。');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-overlay is-visible" aria-labelledby="authTitle">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-brand-stage" aria-hidden="true">
          <span className="auth-brand-word">Deca Growth</span>
          <span className="auth-dot dot-one" />
          <span className="auth-dot dot-two" />
          <span className="auth-dot dot-three" />
        </div>
        <div className="auth-hero">
          <div className="auth-copy">
            <p className="auth-kicker">
              <span className="brand-mark">DECAGROWTH<span className="brand-dot">.</span></span>
            </p>
            <h1 id="authTitle" className="auth-title">欢迎回家，主人</h1>
            <p className="auth-subtitle">请输入管理员账号和密码后进入工作台。</p>
          </div>
        </div>
        <label className="auth-field">
          <span>管理员账号</span>
          <input value={username} onChange={event => setUsername(event.target.value)} type="text" autoComplete="username" required />
        </label>
        <label className="auth-field">
          <span>管理员密码</span>
          <input value={password} onChange={event => setPassword(event.target.value)} type="password" autoComplete="current-password" required />
        </label>
        <div className={`auth-error ${error ? 'is-visible' : ''}`} role="alert">{error}</div>
        <button className="btn primary auth-submit" type="submit" disabled={loading}>{loading ? '正在进入...' : '进入中台'}</button>
      </form>
    </section>
  );
}
