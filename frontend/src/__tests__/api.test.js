// Cliente de la API: cookies, cabecera CSRF y mensajes de error que ve la persona.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from '../api';

function respond(status, body, type = 'application/json') {
  return Promise.resolve(new Response(body === null ? null : (type === 'application/json' ? JSON.stringify(body) : body),
    { status, headers: body === null ? {} : { 'content-type': type } }));
}

let fetchMock;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  document.cookie = 'inka_csrf=token-de-prueba; path=/';
});
afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = 'inka_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
});

describe('request', () => {
  it('envía la cookie, la cabecera CSRF y el JSON', async () => {
    fetchMock.mockReturnValueOnce(respond(200, { id: 1 }));
    await expect(api.manager.createModule({ title: 'X' })).resolves.toEqual({ id: 1 });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/manager\/modules$/);
    expect(options).toMatchObject({ method: 'POST', credentials: 'include', cache: 'no-store', body: '{"title":"X"}' });
    expect(options.headers).toMatchObject({ 'Content-Type': 'application/json', 'X-CSRF-Token': 'token-de-prueba' });
  });

  it('un GET no manda cuerpo y un 204 devuelve null', async () => {
    fetchMock.mockReturnValueOnce(respond(204, null));
    await expect(api.auth.me()).resolves.toBeNull();
    expect(fetchMock.mock.calls[0][1].body).toBeUndefined();
    expect(fetchMock.mock.calls[0][1].headers['Content-Type']).toBeUndefined();
  });

  it('usa el detalle de la API como mensaje de error', async () => {
    fetchMock.mockReturnValueOnce(respond(409, { detail: 'El correo ya está registrado' }));
    const error = await api.admin.createUser({}).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toBe('El correo ya está registrado');
    expect(error.status).toBe(409);
  });

  it('une los errores de validación en un solo mensaje', async () => {
    fetchMock.mockReturnValueOnce(respond(422, { detail: [{ msg: 'Falta el título.' }, { msg: 'Falta el tema.' }] }));
    await expect(api.manager.createChallenge({})).rejects.toThrow('Falta el título. Falta el tema.');
  });

  it('una sesión vencida no muestra el detalle técnico', async () => {
    fetchMock.mockReturnValueOnce(respond(401, { detail: 'Token expirado' }));
    await expect(api.worker.dashboard()).rejects.toThrow('La sesión no es válida o ha expirado.');
    fetchMock.mockReturnValueOnce(respond(401, { detail: 'Credenciales inválidas' }));
    await expect(api.auth.login({})).rejects.toThrow('Credenciales inválidas');   // en el login sí importa el motivo
  });

  it('da un mensaje genérico si la respuesta no es JSON', async () => {
    fetchMock.mockReturnValueOnce(respond(500, '<html>error</html>', 'text/html'));
    await expect(api.admin.dashboard()).rejects.toThrow('No se pudo completar la solicitud.');
  });

  it('escapa el id en la ruta y arma la consulta de auditoría', async () => {
    fetchMock.mockImplementation(() => respond(200, {}));
    await api.manager.getModule('1/../2');
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/manager\/modules\/1%2F\.\.%2F2$/);
    await api.admin.audit({ q: 'login fallido' });
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/admin\/audit\?limit=20&offset=0&q=login\+fallido$/);
    await api.certificates.verify('INKA-AAAA-BBBB-CCCC');
    expect(fetchMock.mock.calls[2][0]).toMatch(/\/certificates\/verify\/INKA-AAAA-BBBB-CCCC$/);
  });

  it('cada función llama a la ruta y al método correctos', async () => {
    fetchMock.mockImplementation(() => respond(200, {}));
    const calls = [
      [() => api.auth.verify2FA({}), 'POST', '/auth/2fa/verify'],
      [() => api.auth.logout(), 'POST', '/auth/logout'],
      [() => api.worker.module(3), undefined, '/worker/modules/3'],
      [() => api.worker.saveComb(3, {}), 'POST', '/worker/modules/3/comb'],
      [() => api.worker.gradeCapacity(3, {}), 'POST', '/worker/modules/3/capacity'],
      [() => api.worker.saveReflections(3, {}), 'POST', '/worker/modules/3/reflections'],
      [() => api.worker.completeModule(3), 'POST', '/worker/modules/3/complete'],
      [() => api.worker.answerChallenge(4, {}), 'POST', '/worker/challenges/4/answer'],
      [() => api.worker.checkStep(4, {}), 'POST', '/worker/challenges/4/check'],
      [() => api.worker.certificates(), undefined, '/worker/certificates'],
      [() => api.worker.renewalQuiz(5), undefined, '/worker/certificates/5/renewal'],
      [() => api.worker.renew(5, {}), 'POST', '/worker/certificates/5/renewal'],
      [() => api.manager.dashboard(), undefined, '/manager/dashboard'],
      [() => api.manager.topics(), undefined, '/manager/topics'],
      [() => api.manager.updateModule(1, {}), 'PUT', '/manager/modules/1'],
      [() => api.manager.getChallenge(2), undefined, '/manager/challenges/2'],
      [() => api.manager.updateChallenge(2, {}), 'PUT', '/manager/challenges/2'],
      [() => api.manager.assignable(), undefined, '/manager/assignable'],
      [() => api.manager.assignments(), undefined, '/manager/assignments'],
      [() => api.manager.createAssignment({}), 'POST', '/manager/assignments'],
      [() => api.manager.deleteAssignment(7), 'DELETE', '/manager/assignments/7'],
      [() => api.manager.stats(), undefined, '/manager/stats'],
      [() => api.admin.users(), undefined, '/admin/users'],
      [() => api.admin.areas(), undefined, '/admin/areas'],
      [() => api.admin.createArea({}), 'POST', '/admin/areas'],
      [() => api.admin.reportSummary(), undefined, '/admin/reports/summary'],
      [() => api.admin.updateUser(8, {}), 'PATCH', '/admin/users/8'],
      [() => api.admin.deleteUser(8), 'DELETE', '/admin/users/8'],
    ];
    for (const [call, method, path] of calls) {
      fetchMock.mockClear();
      await call();
      expect(fetchMock.mock.calls[0][0].endsWith(path)).toBe(true);
      expect(fetchMock.mock.calls[0][1].method).toBe(method);
    }
  });
});

describe('descargas', () => {
  it('devuelve el archivo del certificado y del reporte', async () => {
    fetchMock.mockReturnValueOnce(respond(200, '%PDF', 'application/pdf'));
    expect((await api.worker.certificatePdf(5)).type).toBe('application/pdf');
    fetchMock.mockReturnValueOnce(respond(200, 'area,usuarios', 'text/csv'));
    expect((await api.admin.exportReport()).type).toBe('text/csv');
  });

  it('avisa si la descarga falla', async () => {
    fetchMock.mockReturnValueOnce(respond(404, { detail: 'No' }));
    await expect(api.worker.certificatePdf(5)).rejects.toThrow('No se pudo descargar el certificado.');
    fetchMock.mockReturnValueOnce(respond(403, { detail: 'No' }));
    await expect(api.admin.exportReport()).rejects.toThrow('No se pudo exportar el reporte.');
  });
});
