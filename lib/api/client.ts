type ApiErrorPayload = {
  ok?: boolean;
  error?: unknown;
  detail?: unknown;
  message?: unknown;
};

function stringFromPayloadValue(value: unknown) {
  return typeof value === 'string' && value.trim() ? value : '';
}

export function getErrorMessage(error: unknown, fallback = 'Request failed') {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === 'string' && error.trim()) return error;
  return fallback;
}

export async function parseApiResponse<T>(response: Response, fallback = 'Request failed'): Promise<T> {
  const text = await response.text();
  let payload: ApiErrorPayload = {};
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      throw new Error(fallback);
    }
  }
  if (!response.ok || payload.ok === false) {
    throw new Error(
      stringFromPayloadValue(payload.error) ||
      stringFromPayloadValue(payload.detail) ||
      stringFromPayloadValue(payload.message) ||
      fallback
    );
  }
  return payload as T;
}

export async function apiFetch<T>(url: string, init?: RequestInit, fallback?: string) {
  try {
    return await parseApiResponse<T>(await fetch(url, { cache: 'no-store', ...init }), fallback);
  } catch (error: unknown) {
    if (error instanceof Error && error.message === 'Failed to fetch') {
      throw new Error(`${fallback || 'Request failed'}: API 连接失败，请检查部署或网络。`);
    }
    throw error;
  }
}

export function jsonPostInit(body?: unknown): RequestInit {
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) })
  };
}

export function withQuery(path: string, params: URLSearchParams) {
  const query = params.toString();
  return query ? `${path}?${query}` : path;
}
