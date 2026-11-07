import { useState } from 'react';
import { AdminHome } from './App.jsx';
import { Icon } from './InkaSecLayout.jsx';
import './inka-sec.css';

const data = {
  stats: [
    { label: 'Usuarios activos', value: '128', helper: 'De 134 registrados', icon: 'users', tone: 'blue' },
    { label: 'Cumplimiento global', value: '76%', helper: 'Últimos 30 días', icon: 'chart', tone: 'green' },
    { label: '2FA en roles críticos', value: '100%', helper: 'Gestores y administradores', icon: 'lock', tone: 'blue' },
    { label: 'Eventos de auditoría', value: '24', helper: 'Actividad reciente', icon: 'audit', tone: 'amber' },
  ],
  users: [
    { id: 1, name: 'Ana Torres', email: 'ana@ejemplo.pe', area: 'Tecnología', role: 'Administrador', status: 'Activo', progress: 92, twoFactor: true },
    { id: 2, name: 'Luis Ramos', email: 'luis@ejemplo.pe', area: 'Finanzas', role: 'Trabajador', status: 'Activo', progress: 68, twoFactor: false },
    { id: 3, name: 'María López', email: 'maria@ejemplo.pe', area: 'Ventas', role: 'Gestor', status: 'Activo', progress: 85, twoFactor: true },
  ],
  audit: [
    { id: 1, type: 'success', action: 'Usuario creado', detail: 'María López · Ventas', time: 'Hoy, 09:42' },
    { id: 2, type: 'role', action: 'Rol actualizado', detail: 'Luis Ramos · Finanzas', time: 'Ayer, 16:20' },
  ],
  areas: [
    { name: 'Tecnología', users: 32, compliance: 88 },
    { name: 'Finanzas', users: 26, compliance: 74 },
    { name: 'Ventas', users: 38, compliance: 67 },
  ],
};

export default function AdminPreview() {
  const [search, setSearch] = useState('');
  const demoAction = () => window.alert('Esta es una vista de diseño. Las acciones reales requieren iniciar sesión.');
  return <div className="inka-app admin-design-preview">
    <aside className="inka-sidebar">
      <div className="inka-brand-row"><span className="inka-brand"><span className="inka-brand-mark"><Icon name="shield" size={19}/></span><span className="inka-brand-word">Inka<span>Sec</span></span></span></div>
      <div className="inka-workspace"><span className="inka-workspace-label">Espacio de trabajo</span><div className="inka-workspace-card"><span className="inka-company-badge">IS</span><div><strong>InkaSec</strong><small>Administrador</small></div></div></div>
      <nav className="inka-sidebar-nav" aria-label="Secciones de muestra"><span className="inka-nav-caption">Principal</span><span className="preview-nav-item is-active"><Icon name="home" size={19}/> Resumen</span><span className="preview-nav-item"><Icon name="users" size={19}/> Usuarios</span><span className="preview-nav-item"><Icon name="layers" size={19}/> Áreas y roles</span><span className="preview-nav-item"><Icon name="audit" size={19}/> Auditoría</span></nav>
      <div className="inka-sidebar-security"><span className="inka-security-icon"><Icon name="lock" size={17}/></span><div><strong>Vista de diseño</strong><small>Datos de ejemplo</small></div></div>
    </aside>
    <div className="inka-main-column"><header className="inka-topbar"><div className="inka-topbar-left"><div><span className="inka-topbar-kicker">ADMINISTRADOR</span><strong>Resumen</strong></div></div><span className="preview-badge">VISTA DE DISEÑO · DATOS DE EJEMPLO</span></header><main className="inka-content"><div className="inka-page-shell"><AdminHome data={data} search={search} setSearch={setSearch} onCreateUser={demoAction} onExport={demoAction}/></div></main></div>
  </div>;
}
