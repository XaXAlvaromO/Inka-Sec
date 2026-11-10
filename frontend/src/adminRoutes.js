export const ADMIN_PATHS = {
  inicio: '/admin',
  usuarios: '/admin/usuarios',
  areas: '/admin/areas',
  auditoria: '/admin/auditoria',
  reportes: '/admin/reportes',
};

export function adminViewFromPath(pathname) {
  const path = pathname.replace(/\/$/, '') || '/';
  return Object.keys(ADMIN_PATHS).find((view) => ADMIN_PATHS[view] === path) || 'inicio';
}
