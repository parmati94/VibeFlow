// Thin fetch wrapper. All calls are same-origin (nginx proxies /api + /auth/* to uvicorn),
// so credentials: 'include' keeps the session cookie flowing without CORS.
async function request(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      detail = (await res.json()).detail || detail;
    } catch (e) {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request('/api/health'),
  session: () => request('/api/session'),
  spotifyPlaylists: () => request('/api/playlists/spotify'),
  startSync: (playlistIds, mode = 'add') =>
    request('/api/sync', { method: 'POST', body: JSON.stringify({ playlist_ids: playlistIds, mode }) }),
  activeRuns: () => request('/api/sync/active'),
  recentRuns: (limit = 20) => request(`/api/sync/runs?limit=${limit}`),
  disconnect: (provider) => request(`/auth/${provider}/logout`, { method: 'POST' }),

  // App login gate
  authStatus: () => request('/api/auth/status'),
  logout: () => request('/api/auth/logout', { method: 'POST' }),

  // Scheduled-sync mappings
  listMappings: () => request('/api/mappings'),
  createMapping: (body) => request('/api/mappings', { method: 'POST', body: JSON.stringify(body) }),
  updateMapping: (id, body) => request(`/api/mappings/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteMapping: (id) => request(`/api/mappings/${id}`, { method: 'DELETE' }),
  runMapping: (id) => request(`/api/mappings/${id}/run`, { method: 'POST' }),
};
