import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from './AuthContext';
import { ADMIN_PATHS } from './adminRoutes';
import './inka-sec.css';

export function Icon({ name, size = 20 }) {
  const common = { width: size, height: size, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };
  const icons = {
    shield: <><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8.7 12 2.2 2.2 4.7-5"/></>,
    home: <><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></>,
    book: <><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/></>,
    target: <><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/></>,
    chart: <><path d="M4 19V9M10 19V5M16 19v-7M22 19H2"/></>,
    award: <><circle cx="12" cy="8" r="5"/><path d="m8.5 12-1 9 4.5-2 4.5 2-1-9"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
    layers: <><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/></>,
    audit: <><path d="M9 5H5a2 2 0 0 0-2 2v12h14v-4"/><path d="M9 3h6v4H9zM14 12l2 2 5-5"/></>,
    report: <><path d="M4 3h16v18H4z"/><path d="M8 15v2M12 11v6M16 7v10"/></>,
    bell: <><path d="M18 8a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M14 3h7v18h-7"/></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    lock: <><rect x="4" y="10" width="16" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
  };
  return <svg {...common}>{icons[name] || icons.shield}</svg>;
}

const NAV = {
  worker: [
    { id: 'inicio', label: 'Inicio', icon: 'home' },
    { id: 'modulos', label: 'Mis módulos', icon: 'book' },
    { id: 'retos', label: 'Retos', icon: 'target' },
    { id: 'progreso', label: 'Mi progreso', icon: 'chart' },
    { id: 'certificados', label: 'Certificados', icon: 'award' },
  ],
  manager: [
    { id: 'inicio', label: 'Resumen', icon: 'home' },
    { id: 'contenido', label: 'Contenido', icon: 'book' },
    { id: 'retos', label: 'Retos', icon: 'target' },
    { id: 'asignaciones', label: 'Asignaciones', icon: 'layers' },
    { id: 'estadisticas', label: 'Estadísticas', icon: 'chart' },
  ],
  admin: [
    { id: 'inicio', label: 'Resumen', icon: 'home' },
    { id: 'usuarios', label: 'Usuarios', icon: 'users' },
    { id: 'areas', label: 'Áreas y roles', icon: 'layers' },
    { id: 'auditoria', label: 'Auditoría', icon: 'audit' },
    { id: 'reportes', label: 'Reportes', icon: 'report' },
  ],
};

const ROLE_LABEL = { worker: 'Trabajador', manager: 'Gestor de contenido', admin: 'Administrador' };

export default function InkaSecLayout({ activeView, onViewChange, notifications = [], children }) {
  const { user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const navItems = NAV[user?.role] || [];

  useEffect(() => {
    setSidebarOpen(false);
    setNotificationsOpen(false);
    setProfileOpen(false);
  }, [activeView]);

  const initials = useMemo(() => (user?.name || 'U').split(' ').slice(0, 2).map((part) => part[0]).join('').toUpperCase(), [user?.name]);

  return (
    <div className="inka-app">
      <a className="inka-skip" href="#main-content">Saltar al contenido</a>
      <aside className={`inka-sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="inka-brand-row">
          <button className="inka-brand" type="button" onClick={() => onViewChange('inicio')} aria-label="Ir al inicio">
            <span className="inka-brand-mark"><Icon name="shield" size={19}/></span>
            <span className="inka-brand-word">Inka<span>Sec</span></span>
          </button>
          <button className="inka-mobile-close" type="button" onClick={() => setSidebarOpen(false)} aria-label="Cerrar menú"><Icon name="close"/></button>
        </div>

        <div className="inka-workspace">
          <span className="inka-workspace-label">Espacio de trabajo</span>
          <div className="inka-workspace-card">
            <span className="inka-company-badge">IS</span>
            <div><strong>InkaSec</strong><small>{ROLE_LABEL[user?.role] || 'Usuario'}</small></div>
          </div>
        </div>

        <nav className="inka-sidebar-nav" aria-label="Navegación del panel">
          <span className="inka-nav-caption">Principal</span>
          {navItems.map((item) => user?.role === 'admin' ? (
            <a key={item.id} href={ADMIN_PATHS[item.id]} aria-current={activeView === item.id ? 'page' : undefined} className={activeView === item.id ? 'is-active' : ''} onClick={(event) => { if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return; event.preventDefault(); onViewChange(item.id); }}>
              <Icon name={item.icon} size={19}/><span>{item.label}</span>
              {activeView === item.id && <Icon name="chevron" size={16}/>}
            </a>
          ) : (
            <button key={item.id} type="button" className={activeView === item.id ? 'is-active' : ''} onClick={() => onViewChange(item.id)}>
              <Icon name={item.icon} size={19}/><span>{item.label}</span>
              {activeView === item.id && <Icon name="chevron" size={16}/>}
            </button>
          ))}
        </nav>

        <div className="inka-sidebar-security">
          <span className="inka-security-icon"><Icon name="lock" size={17}/></span>
          <div><strong>Sesión protegida</strong><small>{user?.role === 'worker' ? 'Acceso corporativo' : '2FA obligatorio'}</small></div>
        </div>
      </aside>

      {sidebarOpen && <button className="inka-overlay" aria-label="Cerrar menú" onClick={() => setSidebarOpen(false)} />}

      <div className="inka-main-column">
        <header className="inka-topbar">
          <div className="inka-topbar-left">
            <button className="inka-mobile-menu" type="button" onClick={() => setSidebarOpen(true)} aria-label="Abrir menú"><Icon name="menu"/></button>
            <div><span className="inka-topbar-kicker">{ROLE_LABEL[user?.role]}</span><strong>{navItems.find((item) => item.id === activeView)?.label || 'Inicio'}</strong></div>
          </div>

          <div className="inka-topbar-actions">
            <div className="inka-popover-wrap">
              <button className="inka-top-icon" type="button" aria-label="Notificaciones" onClick={() => { setNotificationsOpen((v) => !v); setProfileOpen(false); }}>
                <Icon name="bell"/>{notifications.length > 0 && <span className="inka-badge">{Math.min(notifications.length, 9)}</span>}
              </button>
              {notificationsOpen && (
                <div className="inka-popover inka-notifications-popover">
                  <div className="inka-popover-head"><strong>Notificaciones</strong><span>{notifications.length} nuevas</span></div>
                  {notifications.length ? notifications.map((item) => <div className="inka-notification-item" key={item.id}><span className="inka-notification-dot"/><div><strong>{item.title}</strong><p>{item.body}</p><small>{item.time}</small></div></div>) : <p className="inka-empty-small">No tienes notificaciones nuevas.</p>}
                </div>
              )}
            </div>

            <div className="inka-popover-wrap">
              <button className="inka-user-menu" type="button" onClick={() => { setProfileOpen((v) => !v); setNotificationsOpen(false); }} aria-label="Abrir menú de usuario">
                <span className="inka-avatar">{initials}</span><span className="inka-user-copy"><strong>{user?.name}</strong><small>{user?.area || ROLE_LABEL[user?.role]}</small></span><Icon name="chevron" size={16}/>
              </button>
              {profileOpen && (
                <div className="inka-popover inka-profile-popover">
                  <div className="inka-profile-summary"><span className="inka-avatar inka-avatar-large">{initials}</span><div><strong>{user?.name}</strong><small>{user?.email}</small></div></div>
                  <div className="inka-profile-role"><span>Rol</span><strong>{ROLE_LABEL[user?.role]}</strong></div>
                  <button type="button" className="inka-logout" onClick={logout}><Icon name="logout" size={17}/> Cerrar sesión</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main id="main-content" className="inka-content" tabIndex={-1}>{children}</main>
      </div>
    </div>
  );
}
