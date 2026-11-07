const API_BASE_URL = (
  import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
).replace(/\/$/, '');

function getCookie(name) {
  const match = document.cookie.match(
    new RegExp(`(?:^|; )${name.replace(/[.$?*|{}()[\]\\/+^]/g, '\\$&')}=([^;]*)`),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiError extends Error {
  constructor(message, status = 0, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

async function request(path, options = {}) {
  const { body, headers = {}, ...rest } = options;
  const csrf = getCookie('inka_csrf');

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    cache: 'no-store',
    ...rest,
    headers: {
      Accept: 'application/json',
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
      ...headers,
    },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  if (response.status === 204) return null;

  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : null;

  if (!response.ok) {
    const detail = Array.isArray(data?.detail)
      ? data.detail.map((issue) => issue.msg).join(' ') : data?.detail;
    const safeMessage =
      response.status === 401 && !['/auth/login', '/auth/2fa/verify'].includes(path)
        ? 'La sesión no es válida o ha expirado.'
        : detail || data?.message || 'No se pudo completar la solicitud.';
    throw new ApiError(safeMessage, response.status, data);
  }

  return data;
}

export const api = {
  config: {
    baseUrl: API_BASE_URL,
  },

  auth: {
    login: (payload) => request('/auth/login', { method: 'POST', body: payload }),
    verify2FA: (payload) => request('/auth/2fa/verify', { method: 'POST', body: payload }),
    me: () => request('/auth/me'),
    logout: () => request('/auth/logout', { method: 'POST' }),
  },

  worker: {
  dashboard: () => request('/worker/dashboard'),

  module: (id) =>
    request(`/worker/modules/${id}`),

  saveComb: (id, payload) =>
    request(`/worker/modules/${id}/comb`, {
      method: 'POST',
      body: payload,
    }),

  completeModule: (id, score) =>
    request(`/worker/modules/${id}/complete`, {
      method: 'POST',
      body: { score },
    }),
},

  manager: {
    dashboard: () => request('/manager/dashboard'),
    createContent: (payload) => request('/manager/content', { method: 'POST', body: payload }),
  },

  admin: {
    dashboard: () => request('/admin/dashboard'),
    users: () => request('/admin/users'),
    areas: () => request('/admin/areas'),
    createArea: (payload) => request('/admin/areas', { method: 'POST', body: payload }),
    audit: ({ limit = 20, offset = 0, q = '' } = {}) => request(`/admin/audit?${new URLSearchParams({ limit, offset, q })}`),
    reportSummary: () => request('/admin/reports/summary'),
    createUser: (payload) => request('/admin/users', { method: 'POST', body: payload }),
    updateUser: (id, payload) => request(`/admin/users/${encodeURIComponent(id)}`, { method: 'PATCH', body: payload }),
    deleteUser: (id) => request(`/admin/users/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    exportReport: async () => {
      const csrf = getCookie('inka_csrf');
      const response = await fetch(`${API_BASE_URL}/admin/reports/export`, {
        method: 'GET',
        credentials: 'include',
        cache: 'no-store',
        headers: {
          ...(csrf ? { 'X-CSRF-Token': csrf } : {}),
        },
      });

      if (!response.ok) {
        throw new ApiError('No se pudo exportar el reporte.', response.status);
      }
      return response.blob();
    },
  },
};
