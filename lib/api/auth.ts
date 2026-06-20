import { apiFetch, jsonPostInit } from './client';

export const authApi = {
  login: (username: string, password: string) =>
    apiFetch<{ ok: boolean; authenticated: boolean }>('/api/auth/login', jsonPostInit({ username, password }), '登录失败'),
  logout: () => apiFetch<{ ok: boolean }>('/api/auth/logout', { method: 'POST' }, '退出登录失败')
};
