// Thin fetch wrapper. All calls are same-origin (nginx proxies /api + /auth/* to uvicorn),
// so credentials: 'include' keeps the session cookie flowing without CORS.
async function request(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`${options.method || 'GET'} ${path} → ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request('/api/health'),
  session: () => request('/api/session'),
};
