"""Constantes compartidas entre el bootstrap y el servicio de superadministrador.

Viven aparte (y no dentro de bootstrap_admin.py) para que app/services/superadmin_service.py
no tenga que importar el script de arranque solo para leer dos cadenas.
"""

# Empresa interna que agrupa las cuentas de superadministrador. No es una empresa cliente:
# se excluye de los listados que ve el propio superadministrador (app/services/superadmin_service.py).
PLATFORM_COMPANY_NAME = "InkaSec · Plataforma"
PLATFORM_COMPANY_SLUG = "inkasec-plataforma"
