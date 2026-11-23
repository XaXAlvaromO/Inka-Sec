// Panel del administrador: usuarios, áreas, auditoría, reportes y menú de la cuenta.
// Los datos de ejemplo son respuestas reales de la API con el seed de demostración.
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import App from '../App';
import { api, ApiError } from '../api';
import fixtures from '../test/fixtures/admin.json';

const ADMIN = { id: 3, name: 'Diego Vargas', email: 'admin@inkasec.pe', role: 'admin', area: 'TI' };

beforeEach(() => {
  api.auth.me.mockResolvedValue({ user: ADMIN });
  api.admin.dashboard.mockResolvedValue(fixtures.dashboard);
  api.admin.users.mockResolvedValue(fixtures.users);
  api.admin.areas.mockResolvedValue(fixtures.areas);
  api.admin.audit.mockResolvedValue(fixtures.audit);
  api.admin.reportSummary.mockResolvedValue(fixtures.report);
});

async function openAdmin(path = '/admin') {
  window.history.replaceState(null, '', path);
  render(<App/>);
  return screen.findByRole('main');
}

describe('administrador', () => {
  it('muestra el resumen y busca usuarios', async () => {
    await openAdmin();
    expect(await screen.findByText(/La seguridad de tu equipo/)).toBeInTheDocument();
    const table = screen.getByRole('table');
    await userEvent.type(screen.getByLabelText('Buscar usuario'), 'gestor@');
    expect(within(table).getByText('Lucía Torres')).toBeInTheDocument();
    expect(within(table).queryByText('María López')).not.toBeInTheDocument();
  });

  it('crea un usuario y muestra la contraseña inicial una sola vez', async () => {
    api.admin.createUser.mockResolvedValueOnce({ id: 9, name: 'Nueva Persona', email: 'nueva@inkasec.pe', temporary_password: 'Temporal-1234' });
    await openAdmin();
    await userEvent.click(await screen.findByRole('button', { name: 'Crear usuario' }));
    const dialog = screen.getByRole('dialog', { name: 'Crear usuario' });
    await userEvent.type(within(dialog).getByLabelText('Nombre completo'), ' Nueva Persona ');
    await userEvent.type(within(dialog).getByLabelText('Correo corporativo'), 'nueva@inkasec.pe');
    await userEvent.selectOptions(within(dialog).getByLabelText('Rol'), 'manager');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear usuario' }));
    expect(api.admin.createUser).toHaveBeenCalledWith(expect.objectContaining({ name: 'Nueva Persona', email: 'nueva@inkasec.pe', role: 'manager' }));
    expect(await screen.findByText('Temporal-1234')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ya guardé los datos' }));
    expect(screen.queryByText('Temporal-1234')).not.toBeInTheDocument();
    expect(await screen.findByText('Usuario creado correctamente.')).toBeInTheDocument();
  });

  it('muestra el error al crear un usuario repetido', async () => {
    api.admin.createUser.mockRejectedValueOnce(new ApiError('El correo ya está registrado', 409));
    await openAdmin();
    await userEvent.click(await screen.findByRole('button', { name: 'Crear usuario' }));
    const dialog = screen.getByRole('dialog', { name: 'Crear usuario' });
    await userEvent.type(within(dialog).getByLabelText('Nombre completo'), 'Repetida');
    await userEvent.type(within(dialog).getByLabelText('Correo corporativo'), 'gestor@inkasec.pe');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear usuario' }));
    expect(await within(dialog).findByRole('alert')).toHaveTextContent('El correo ya está registrado');
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('cambia el rol de una cuenta y elimina otra', async () => {
    api.admin.updateUser.mockResolvedValueOnce({});
    api.admin.deleteUser.mockResolvedValueOnce({ ok: true });
    await openAdmin('/admin/usuarios');
    await userEvent.click(await screen.findByRole('button', { name: 'Editar María López' }));
    const edit = screen.getByRole('dialog', { name: 'Editar acceso de María López' });
    const save = within(edit).getByRole('button', { name: 'Guardar cambios' });
    expect(save).toBeDisabled();                                    // sin cambios no se guarda
    await userEvent.selectOptions(within(edit).getByLabelText('Rol'), 'manager');
    await userEvent.click(within(edit).getByLabelText('Cuenta activa'));
    await userEvent.click(save);
    expect(api.admin.updateUser).toHaveBeenCalledWith(1, { role: 'manager', is_active: false });
    expect(await screen.findByText('Acceso actualizado correctamente.')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Eliminar María López' }));
    const del = screen.getByRole('dialog', { name: 'Eliminar usuario' });
    await userEvent.click(within(del).getByRole('button', { name: 'Eliminar cuenta' }));
    expect(api.admin.deleteUser).toHaveBeenCalledWith(1);
    expect(await screen.findByText('Usuario eliminado correctamente.')).toBeInTheDocument();
  });

  it('no deja quitarse el rol ni eliminarse a sí mismo', async () => {
    await openAdmin('/admin/usuarios');
    await userEvent.click(await screen.findByRole('button', { name: 'Editar Diego Vargas' }));
    const edit = screen.getByRole('dialog', { name: 'Editar acceso de Diego Vargas' });
    expect(within(edit).getByLabelText('Rol')).toBeDisabled();
    expect(screen.queryByRole('button', { name: 'Eliminar Diego Vargas' })).not.toBeInTheDocument();
    await userEvent.click(within(edit).getByRole('button', { name: 'Cancelar' }));
  });

  it('crea un área y filtra usuarios por área', async () => {
    api.admin.createArea.mockResolvedValueOnce({ id: 20, name: 'Legal' });
    await openAdmin('/admin/areas');
    await userEvent.click(await screen.findByRole('button', { name: 'Crear área' }));
    const dialog = screen.getByRole('dialog', { name: 'Crear área' });
    await userEvent.type(within(dialog).getByLabelText('Nombre del área'), 'Legal');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear área' }));
    expect(api.admin.createArea).toHaveBeenCalledWith({ name: 'Legal' });
    expect(await screen.findByText('Área creada correctamente.')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText(/Filtrar área/), 'Finanzas');
    const table = screen.getByRole('table');
    expect(within(table).getByText('María López')).toBeInTheDocument();
    expect(within(table).queryByText('Lucía Torres')).not.toBeInTheDocument();
  });

  it('busca en la auditoría y pagina', async () => {
    api.admin.audit.mockResolvedValue({ ...fixtures.audit, total: 45 });
    await openAdmin('/admin/auditoria');
    expect(await screen.findByRole('heading', { name: 'Historial de actividades' })).toBeInTheDocument();
    expect(screen.getAllByText('Inicio de sesión con 2FA').length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
    expect(api.admin.audit).toHaveBeenLastCalledWith({ limit: 20, offset: 20, q: '' });
    await userEvent.type(screen.getByLabelText('Buscar evento'), 'x');
    expect(api.admin.audit).toHaveBeenLastCalledWith({ limit: 20, offset: 0, q: 'x' });
  });

  it('exporta el reporte en CSV', async () => {
    api.admin.exportReport.mockResolvedValueOnce(new Blob(['area,usuarios'], { type: 'text/csv' }));
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    await openAdmin('/admin/reportes');
    await userEvent.click(await screen.findByRole('button', { name: 'Exportar CSV' }));
    expect(await screen.findByText('Se descargó el reporte por área.')).toBeInTheDocument();
    api.admin.exportReport.mockRejectedValueOnce(new ApiError('No se pudo exportar el reporte.', 500));
    await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }));
    expect(await screen.findByText('No se pudo exportar el reporte.')).toBeInTheDocument();
  });

  it('cambia de sección con la barra y muestra el error de carga', async () => {
    await openAdmin();
    await userEvent.click(await screen.findByRole('link', { name: /Auditoría/ }));
    expect(window.location.pathname).toBe('/admin/auditoria');
    api.admin.reportSummary.mockRejectedValueOnce(new ApiError('Servicio no disponible', 503));
    await userEvent.click(screen.getByRole('link', { name: /Reportes/ }));
    expect(await screen.findByText('Servicio no disponible')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('button', { name: 'Exportar CSV' })).toBeInTheDocument();
  });

  it('abre notificaciones y cierra sesión', async () => {
    api.auth.logout.mockResolvedValueOnce(null);
    await openAdmin();
    await screen.findByText(/La seguridad de tu equipo/);
    await userEvent.click(screen.getByRole('button', { name: 'Notificaciones' }));
    expect(screen.getByText('Notificaciones')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Abrir menú de usuario' }));
    expect(document.querySelector('.inka-profile-popover')).toHaveTextContent('admin@inkasec.pe');
    await userEvent.click(screen.getByRole('button', { name: /Cerrar sesión/ }));
    expect(await screen.findByRole('heading', { name: 'Inicia sesión' })).toBeInTheDocument();
  });
});
