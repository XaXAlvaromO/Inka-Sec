// Panel del superadministrador: alta de empresas con su primer administrador, y gestión de
// cualquier usuario de cualquier empresa. Cada empresa sigue viendo solo sus propios datos
// (eso no cambia); este panel es la única vista que ve todas a la vez.
import { useEffect, useState } from 'react';
import { api, ApiError } from './api';
import { EmptyState, GenericPage, Modal } from './ui';

function errorMessage(err, fallback) {
  return err instanceof ApiError ? err.message : fallback;
}

function CreateCompanyModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ company_name: '', admin_name: '', admin_email: '' });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      setResult(await api.superadmin.createCompany(form));
    } catch (err) {
      setError(errorMessage(err, 'No se pudo crear la empresa.'));
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Modal title="Empresa creada" onClose={onCreated}>
        <div className="modal-form">
          <p><strong>{result.company.name}</strong> ya existe, con <strong>{result.name}</strong> ({result.email}) como su primer administrador.</p>
          {result.email_sent ? (
            <p>Le enviamos un correo con su contraseña inicial.</p>
          ) : (
            <p className="form-error" role="alert">No pudimos enviarle el correo de bienvenida. Entrégale esta contraseña temporal por otro medio: <code>{result.temporary_password}</code></p>
          )}
          <p className="admin-hint">Desde ahí, el administrador gestiona sus propias áreas, gestores y trabajadores.</p>
          <div className="modal-actions"><button type="button" className="btn btn-primary" onClick={onCreated}>Listo</button></div>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Nueva empresa" onClose={onClose}>
      <form className="modal-form" onSubmit={submit}>
        <label>Nombre de la empresa<input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} required minLength={2} maxLength={120}/></label>
        <label>Nombre del administrador<input value={form.admin_name} onChange={(e) => setForm({ ...form, admin_name: e.target.value })} required minLength={2} maxLength={120}/></label>
        <label>Correo del administrador<input type="email" value={form.admin_email} onChange={(e) => setForm({ ...form, admin_email: e.target.value })} required/></label>
        <p className="form-note">El nombre distingue a esta empresa de las demás en este panel. El administrador recibirá su contraseña inicial por correo y, desde entonces, solo verá y gestionará su propia empresa.</p>
        {error && <div className="form-error" role="alert">{error}</div>}
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Creando…' : 'Crear empresa'}</button>
        </div>
      </form>
    </Modal>
  );
}

function CompanyTeamModal({ company, onClose, onChanged }) {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  useEffect(() => {
    let active = true;
    api.superadmin.companyUsers(company.id)
      .then((rows) => { if (active) setUsers(rows); })
      .catch((err) => { if (active) setError(errorMessage(err, 'No se pudo cargar el equipo.')); });
    return () => { active = false; };
  }, [company.id]);

  async function toggleActive(user) {
    setBusyId(user.id);
    setError('');
    try {
      await api.superadmin.updateUser(user.id, { is_active: user.status !== 'Activo' });
      setUsers((rows) => rows.map((u) => (u.id === user.id ? { ...u, status: u.status === 'Activo' ? 'Inactivo' : 'Activo' } : u)));
      onChanged();
    } catch (err) {
      setError(errorMessage(err, 'No se pudo actualizar el usuario.'));
    } finally {
      setBusyId(null);
    }
  }

  async function confirmAndDelete() {
    setBusyId(confirmDelete.id);
    setError('');
    try {
      await api.superadmin.deleteUser(confirmDelete.id);
      setUsers((rows) => rows.filter((u) => u.id !== confirmDelete.id));
      setConfirmDelete(null);
      onChanged();
    } catch (err) {
      setError(errorMessage(err, 'No se pudo eliminar el usuario.'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <Modal title={`Equipo de ${company.name}`} onClose={onClose}>
      <div className="modal-form">
        {error && <div className="form-error" role="alert">{error}</div>}
        {!users ? (
          <p className="admin-hint">Cargando…</p>
        ) : users.length === 0 ? (
          <p className="admin-hint">Esta empresa todavía no tiene usuarios.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th></th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.name}</td>
                    <td>{u.email}</td>
                    <td>{u.role}</td>
                    <td>{u.status}</td>
                    <td>
                      <button type="button" className="text-button" disabled={busyId === u.id} onClick={() => toggleActive(u)}>{u.status === 'Activo' ? 'Desactivar' : 'Activar'}</button>{' '}
                      <button type="button" className="text-button danger-text" disabled={busyId === u.id} onClick={() => setConfirmDelete(u)}>Eliminar</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {confirmDelete && (
          <div className="form-error" role="alert">
            <p>¿Eliminar a <strong>{confirmDelete.name}</strong>? Esta acción no se puede deshacer.</p>
            <div className="modal-actions">
              <button type="button" className="btn btn-secondary" onClick={() => setConfirmDelete(null)}>Cancelar</button>
              <button type="button" className="btn btn-primary" onClick={confirmAndDelete} disabled={busyId === confirmDelete.id}>Sí, eliminar</button>
            </div>
          </div>
        )}
        <div className="modal-actions"><button type="button" className="btn btn-secondary" onClick={onClose}>Cerrar</button></div>
      </div>
    </Modal>
  );
}

export function SuperadminViews({ companies, onChanged }) {
  const [modal, setModal] = useState(null); // 'create' | { company }
  const [notice, setNotice] = useState(null);

  function refresh(message) {
    setNotice({ type: 'success', message });
    onChanged();
  }

  return (
    <GenericPage eyebrow="PLATAFORMA" title="Empresas" description="Crea una empresa con su primer administrador, o revisa y gestiona a cualquier usuario de cualquier empresa. Cada empresa solo ve sus propios datos.">
      {notice && <div className={`admin-notice ${notice.type === 'error' ? 'is-error' : ''}`} role="status">{notice.message}</div>}
      <div className="panel-head">
        <div><span className="eyebrow">{companies.length} {companies.length === 1 ? 'EMPRESA' : 'EMPRESAS'}</span></div>
        <button type="button" className="btn btn-primary" onClick={() => setModal('create')}>+ Nueva empresa</button>
      </div>
      {companies.length === 0 ? (
        <EmptyState title="Todavía no hay empresas" description="Crea la primera empresa y su administrador para empezar."/>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Empresa</th><th>Usuarios</th><th>Administradores</th><th>Creada</th><th></th></tr></thead>
            <tbody>
              {companies.map((c) => (
                <tr key={c.id}>
                  <td><strong>{c.name}</strong></td>
                  <td>{c.users}</td>
                  <td>{c.admins}</td>
                  <td>{new Date(c.created_at).toLocaleDateString('es-PE')}</td>
                  <td><button type="button" className="text-button" onClick={() => setModal({ company: c })}>Ver equipo</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {modal === 'create' && <CreateCompanyModal onClose={() => setModal(null)} onCreated={() => { setModal(null); refresh('Empresa creada correctamente.'); }}/>}
      {modal?.company && <CompanyTeamModal company={modal.company} onClose={() => setModal(null)} onChanged={() => refresh('Usuario actualizado correctamente.')}/>}
    </GenericPage>
  );
}
