// Panel del superadministrador: lista de empresas, alta de una empresa nueva con su
// administrador, y gestión de cualquier usuario (activar, desactivar, eliminar).
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('../api', async () => (await import('../test/mockApi')).createApiMock());

import { api, ApiError } from '../api';
import { SuperadminViews } from '../superadmin';

const COMPANIES = [
  { id: 1, name: 'Constructora Lima', slug: 'constructora-lima', users: 12, admins: 1, created_at: '2026-01-15T10:00:00Z' },
  { id: 2, name: 'Panadería Andina', slug: 'panaderia-andina', users: 4, admins: 1, created_at: '2026-03-02T10:00:00Z' },
];

describe('Panel del superadministrador', () => {
  it('lista las empresas con sus conteos de usuarios y administradores', () => {
    render(<SuperadminViews companies={COMPANIES} onChanged={vi.fn()}/>);
    expect(screen.getByText('2 EMPRESAS')).toBeInTheDocument();
    const rows = screen.getAllByRole('row').slice(1);
    expect(within(rows[0]).getByText('Constructora Lima')).toBeInTheDocument();
    expect(within(rows[0]).getByText('12')).toBeInTheDocument();
    expect(within(rows[1]).getByText('Panadería Andina')).toBeInTheDocument();
  });

  it('muestra el estado vacío cuando todavía no hay empresas', () => {
    render(<SuperadminViews companies={[]} onChanged={vi.fn()}/>);
    expect(screen.getByText('Todavía no hay empresas')).toBeInTheDocument();
  });

  it('crea una empresa y avisa que el correo de bienvenida se envió', async () => {
    const onChanged = vi.fn();
    api.superadmin.createCompany.mockResolvedValueOnce({
      company: { id: 3, name: 'Nueva Empresa SAC', slug: 'nueva-empresa-sac' },
      id: 9, name: 'Rosa Admin', email: 'rosa@nueva.pe', role: 'Administrador', status: 'Activo', twoFactor: true,
      temporary_password: 'clave-temporal-123', email_sent: true,
    });
    render(<SuperadminViews companies={COMPANIES} onChanged={onChanged}/>);
    await userEvent.click(screen.getByRole('button', { name: '+ Nueva empresa' }));
    const dialog = screen.getByRole('dialog', { name: 'Nueva empresa' });
    await userEvent.type(within(dialog).getByLabelText('Nombre de la empresa'), 'Nueva Empresa SAC');
    await userEvent.type(within(dialog).getByLabelText('Nombre del administrador'), 'Rosa Admin');
    await userEvent.type(within(dialog).getByLabelText('Correo del administrador'), 'rosa@nueva.pe');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear empresa' }));
    expect(api.superadmin.createCompany).toHaveBeenCalledWith({ company_name: 'Nueva Empresa SAC', admin_name: 'Rosa Admin', admin_email: 'rosa@nueva.pe' });
    expect(await screen.findByText('Le enviamos un correo con su contraseña inicial.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Listo' }));
    expect(onChanged).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Empresa creada correctamente.')).toBeInTheDocument();
  });

  it('si el correo de bienvenida falla, muestra la contraseña temporal para entregarla a mano', async () => {
    api.superadmin.createCompany.mockResolvedValueOnce({
      company: { id: 3, name: 'Otra Empresa', slug: 'otra-empresa' },
      id: 9, name: 'Juan Admin', email: 'juan@otra.pe', role: 'Administrador', status: 'Activo', twoFactor: true,
      temporary_password: 'clave-de-respaldo', email_sent: false,
    });
    render(<SuperadminViews companies={COMPANIES} onChanged={vi.fn()}/>);
    await userEvent.click(screen.getByRole('button', { name: '+ Nueva empresa' }));
    const dialog = screen.getByRole('dialog', { name: 'Nueva empresa' });
    await userEvent.type(within(dialog).getByLabelText('Nombre de la empresa'), 'Otra Empresa');
    await userEvent.type(within(dialog).getByLabelText('Nombre del administrador'), 'Juan Admin');
    await userEvent.type(within(dialog).getByLabelText('Correo del administrador'), 'juan@otra.pe');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear empresa' }));
    expect(await screen.findByText('clave-de-respaldo')).toBeInTheDocument();
  });

  it('muestra el error cuando el nombre de la empresa o el correo ya existen', async () => {
    api.superadmin.createCompany.mockRejectedValueOnce(new ApiError('Ya existe una empresa con ese nombre', 409));
    render(<SuperadminViews companies={COMPANIES} onChanged={vi.fn()}/>);
    await userEvent.click(screen.getByRole('button', { name: '+ Nueva empresa' }));
    const dialog = screen.getByRole('dialog', { name: 'Nueva empresa' });
    await userEvent.type(within(dialog).getByLabelText('Nombre de la empresa'), 'Constructora Lima');
    await userEvent.type(within(dialog).getByLabelText('Nombre del administrador'), 'Otro');
    await userEvent.type(within(dialog).getByLabelText('Correo del administrador'), 'otro@lima.pe');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Crear empresa' }));
    expect(await screen.findByText('Ya existe una empresa con ese nombre')).toBeInTheDocument();
    // El formulario sigue abierto para corregir, no se cerró solo.
    expect(screen.getByRole('dialog', { name: 'Nueva empresa' })).toBeInTheDocument();
  });

  it('carga el equipo de una empresa, y activa, desactiva y elimina usuarios', async () => {
    const onChanged = vi.fn();
    api.superadmin.companyUsers.mockResolvedValueOnce([
      { id: 11, name: 'Ana Gestora', email: 'ana@lima.pe', area: 'Finanzas', role: 'Gestor', status: 'Activo', twoFactor: true },
      { id: 12, name: 'Luis Trabajador', email: 'luis@lima.pe', area: 'Finanzas', role: 'Trabajador', status: 'Activo', twoFactor: false },
    ]);
    render(<SuperadminViews companies={COMPANIES} onChanged={onChanged}/>);
    await userEvent.click(screen.getAllByRole('button', { name: 'Ver equipo' })[0]);
    const dialog = await screen.findByRole('dialog', { name: 'Equipo de Constructora Lima' });
    expect(within(dialog).getByText('ana@lima.pe')).toBeInTheDocument();
    const anaRow = within(dialog).getByText('ana@lima.pe').closest('tr');
    const luisRow = within(dialog).getByText('luis@lima.pe').closest('tr');

    api.superadmin.updateUser.mockResolvedValueOnce({ ok: true });
    await userEvent.click(within(anaRow).getByRole('button', { name: 'Desactivar' }));
    expect(api.superadmin.updateUser).toHaveBeenCalledWith(11, { is_active: false });
    expect(await within(anaRow).findByRole('button', { name: 'Activar' })).toBeInTheDocument();
    // La fila de Luis no cambió: sigue activo, y a Ana no la tocamos en esta parte.
    expect(within(luisRow).getByRole('button', { name: 'Desactivar' })).toBeInTheDocument();

    api.superadmin.deleteUser.mockResolvedValueOnce({ ok: true });
    await userEvent.click(within(luisRow).getByRole('button', { name: 'Eliminar' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Sí, eliminar' }));
    expect(api.superadmin.deleteUser).toHaveBeenCalledWith(12);
    expect(within(dialog).queryByText('luis@lima.pe')).not.toBeInTheDocument();
    expect(onChanged).toHaveBeenCalled();
  });

  it('muestra un estado vacío cuando la empresa todavía no tiene usuarios', async () => {
    api.superadmin.companyUsers.mockResolvedValueOnce([]);
    render(<SuperadminViews companies={COMPANIES} onChanged={vi.fn()}/>);
    await userEvent.click(screen.getAllByRole('button', { name: 'Ver equipo' })[1]);
    expect(await screen.findByText('Esta empresa todavía no tiene usuarios.')).toBeInTheDocument();
  });
});
