"""Simulaciones de ataque contra la API.

Cada prueba reproduce lo que haría un atacante y comprueba que la defensa responde.
Las secciones siguen el orden: credenciales, 2FA, sesión, CSRF, autorización,
inyección, cabeceras y configuración.
"""
import importlib
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app import bootstrap_admin, dev_seed_challenges, dev_totp, seed
from app.core.config import Settings, settings
from app.core.security import totp_code
from app.main import app
from app.models.models import Area, AuditLog, AuthChallenge, CombResponse, User
from conftest import API, csrf, start_login, wrong_code

UNKNOWN = "nadie@x.pe"


def verify(client, challenge_id, code):
    return client.post(f"{API}/auth/2fa/verify", json={"challenge_id": challenge_id, "code": code})


# ---------------------------------------------------------------- credenciales

def test_password_bruteforce_locks_the_account(world, db):
    attacker = TestClient(app)
    for _ in range(3):
        assert start_login(attacker, world.w1, "adivinanza").status_code == 401
    # Aunque ahora acierte, la cuenta está bloqueada 15 minutos.
    assert start_login(attacker, world.w1).status_code == 423
    failed = db.scalars(select(AuditLog).where(AuditLog.action == "LOGIN_FAILED")).all()
    assert len(failed) == 3


def test_login_flood_is_rate_limited(world):
    attacker = TestClient(app)
    for _ in range(10):
        assert attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}).status_code == 401
    r = attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"})
    assert r.status_code == 429 and r.headers["retry-after"] == "60"


def test_spoofed_x_forwarded_for_does_not_bypass_rate_limit(world):
    attacker = TestClient(app)
    for i in range(10):
        attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}, headers={"x-forwarded-for": f"10.0.0.{i}"})
    r = attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}, headers={"x-forwarded-for": "10.0.0.99"})
    assert r.status_code == 429


def test_behind_trusted_proxy_only_the_proxy_hop_counts(world, db, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    attacker = TestClient(app)
    # El atacante inventa la parte izquierda; el proxy (Render) agrega la IP real al final.
    for i in range(10):
        attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}, headers={"x-forwarded-for": f"1.2.3.{i}, 203.0.113.7"})
    blocked = attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}, headers={"x-forwarded-for": "6.6.6.6, 203.0.113.7"})
    assert blocked.status_code == 429
    other_client = attacker.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}, headers={"x-forwarded-for": "203.0.113.8"})
    assert other_client.status_code == 401
    ips = set(db.scalars(select(AuditLog.ip_address)).all())
    assert ips == {"203.0.113.7", "203.0.113.8"}


def test_giant_forwarded_ip_is_truncated_not_a_500(world, db, monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    r = TestClient(app).post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"}, headers={"x-forwarded-for": "a" * 5000})
    assert r.status_code == 401
    assert len(db.scalar(select(AuditLog.ip_address))) <= 64   # la columna es VARCHAR(64) en Postgres


def test_huge_password_is_rejected_before_hashing(world):
    r = TestClient(app).post(f"{API}/auth/login", json={"email": world.w1.email, "password": "a" * 100_000})
    assert r.status_code == 422


def test_unknown_email_and_wrong_password_look_identical(world, monkeypatch):
    client = TestClient(app)
    unknown = client.post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"})
    wrong = start_login(client, world.w1, "x")
    assert (unknown.status_code, unknown.json()) == (wrong.status_code, wrong.json())


def test_unknown_email_still_pays_the_hashing_cost(world, monkeypatch):
    """Sin el hash de relleno, un correo inexistente responde más rápido y se puede enumerar."""
    import app.services.auth_service as auth_service
    calls = []
    real = auth_service.verify_password
    monkeypatch.setattr(auth_service, "verify_password", lambda p, h: calls.append(h) or real(p, h))
    TestClient(app).post(f"{API}/auth/login", json={"email": UNKNOWN, "password": "x"})
    assert len(calls) == 1 and calls[0].startswith("$argon2")


def test_inactive_account_is_only_revealed_with_the_right_password(world, db):
    world.w1.is_active = False; db.merge(world.w1); db.commit()
    client = TestClient(app)
    assert start_login(client, world.w1, "x").json()["detail"] == "Credenciales inválidas"
    assert start_login(client, world.w1).status_code == 403


def test_sql_injection_in_login_is_inert(world):
    r = TestClient(app).post(f"{API}/auth/login", json={"email": "' OR '1'='1' --", "password": "' OR '1'='1"})
    assert r.status_code == 401


# ------------------------------------------------------------------------- 2FA

def test_2fa_bruteforce_locks_the_account_and_burns_the_challenge(world):
    attacker = TestClient(app)
    challenge_id = start_login(attacker, world.mgr).json()["challenge_id"]   # supongamos que robó la contraseña
    bad = wrong_code(world.mgr.totp_secret)
    for _ in range(3):
        assert verify(attacker, challenge_id, bad).status_code == 401
    # El desafío quedó inutilizado: ni con el código correcto entra.
    assert verify(attacker, challenge_id, totp_code(world.mgr.totp_secret)).status_code == 401
    assert start_login(attacker, world.mgr).status_code == 423


def test_logging_in_again_does_not_reset_the_2fa_failures(world):
    attacker = TestClient(app)
    bad = wrong_code(world.mgr.totp_secret)
    first = start_login(attacker, world.mgr).json()["challenge_id"]
    verify(attacker, first, bad); verify(attacker, first, bad)
    second = start_login(attacker, world.mgr).json()["challenge_id"]       # intenta "recargar" intentos
    verify(attacker, second, bad)
    assert start_login(attacker, world.mgr).status_code == 423


def test_successful_2fa_resets_the_counter(world):
    client = TestClient(app)
    bad = wrong_code(world.mgr.totp_secret)
    cid = start_login(client, world.mgr).json()["challenge_id"]
    verify(client, cid, bad); verify(client, cid, bad)
    assert verify(client, cid, totp_code(world.mgr.totp_secret)).status_code == 200
    cid = start_login(client, world.mgr).json()["challenge_id"]
    verify(client, cid, bad)
    assert verify(client, cid, totp_code(world.mgr.totp_secret)).status_code == 200


def test_2fa_challenge_cannot_be_replayed(world):
    client = TestClient(app)
    cid = start_login(client, world.adm).json()["challenge_id"]
    code = totp_code(world.adm.totp_secret)
    assert verify(client, cid, code).status_code == 200
    assert verify(TestClient(app), cid, code).status_code == 401


def test_expired_2fa_challenge_is_rejected(world, db):
    client = TestClient(app)
    cid = start_login(client, world.adm).json()["challenge_id"]
    row = db.scalar(select(AuthChallenge).where(AuthChallenge.challenge_id == cid))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1); db.commit()
    assert verify(client, cid, totp_code(world.adm.totp_secret)).status_code == 401


@pytest.mark.parametrize("payload", [
    {"challenge_id": "0" * 32, "code": "12ab56"},
    {"challenge_id": "0" * 32, "code": "1234567"},
    {"challenge_id": "../../etc/passwd" + "0" * 20, "code": "123456"},
])
def test_malformed_2fa_input_is_rejected(world, payload):
    assert TestClient(app).post(f"{API}/auth/2fa/verify", json=payload).status_code == 422


def test_2fa_verification_is_rate_limited(world):
    attacker = TestClient(app)
    for _ in range(10):
        assert verify(attacker, "f" * 32, "123456").status_code == 401
    assert verify(attacker, "f" * 32, "123456").status_code == 429


def test_password_alone_never_opens_a_privileged_session(world):
    client = TestClient(app)
    r = start_login(client, world.adm)
    assert r.json()["requires_2fa"] is True and "inka_access" not in client.cookies
    assert client.get(f"{API}/admin/dashboard").status_code == 401


# ---------------------------------------------------------------------- sesión

def _token_for(user_id, **overrides):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": "admin", "company_id": 1, "iat": now, "exp": now + timedelta(minutes=5), **overrides}
    return jwt.encode({k: v for k, v in payload.items() if v is not None}, settings.jwt_secret_key, algorithm="HS256")


def _me_with(token):
    client = TestClient(app)
    client.cookies.set("inka_access", token)
    return client.get(f"{API}/auth/me")


def test_forged_tokens_are_rejected(world):
    valid = _token_for(world.w1.id)
    assert _me_with(valid).status_code == 200
    header, body, signature = valid.split(".")
    tampered = f"{header}.{body}.{signature[:-2]}{'A' if signature[-2] != 'A' else 'B'}{signature[-1]}"
    forged = {
        "firma alterada": tampered,
        "alg none": jwt.encode({"sub": str(world.adm.id), "exp": time.time() + 300, "iat": time.time()}, None, algorithm="none"),
        "otra clave": jwt.encode({"sub": str(world.adm.id), "exp": time.time() + 300, "iat": time.time()}, "x" * 40, algorithm="HS256"),
        "expirado": _token_for(world.w1.id, exp=datetime.now(timezone.utc) - timedelta(seconds=5)),
        "sin exp": _token_for(world.w1.id, exp=None),
        "basura": "no-es-un-jwt",
    }
    for name, token in forged.items():
        assert _me_with(token).status_code == 401, name


def test_role_in_token_is_not_trusted(world):
    """El rol se lee de la base de datos: un token que diga admin no da permisos de admin."""
    client = TestClient(app)
    client.cookies.set("inka_access", _token_for(world.w1.id, role="admin"))
    assert client.get(f"{API}/admin/dashboard").status_code == 403


def test_session_cookie_flags(world, monkeypatch):
    monkeypatch.setattr(settings, "cookie_secure", True)
    r = start_login(TestClient(app), world.w1)
    cookies = {c.split("=", 1)[0]: c.lower() for c in r.headers.get_list("set-cookie")}
    assert "httponly" in cookies["inka_access"] and "secure" in cookies["inka_access"] and "samesite=lax" in cookies["inka_access"]
    assert "httponly" not in cookies["inka_csrf"]          # el front debe poder leerla para enviarla
    assert "secure" in cookies["inka_csrf"]


def test_logout_ends_the_session(world, client_for):
    client = client_for(world.w1)
    r = client.post(f"{API}/auth/logout", headers=csrf(client))
    assert r.status_code == 200
    assert all("max-age=0" in c.lower() for c in r.headers.get_list("set-cookie"))
    assert client.get(f"{API}/auth/me").status_code == 401


# ------------------------------------------------------------------------ CSRF

@pytest.mark.parametrize("header", [None, "token-de-otro-sitio", "ñandú".encode("latin-1")])
def test_state_changes_require_matching_csrf_token(world, client_for, header):
    # Un sitio malicioso puede hacer que el navegador envíe la cookie, pero no puede leerla.
    client = client_for(world.w1)
    headers = {} if header is None else {"x-csrf-token": header}
    r = client.post(f"{API}/worker/modules/{world.mods[0].id}/complete", headers=headers)
    assert r.status_code == 403 and r.json()["detail"] == "CSRF token inválido"


# --------------------------------------------------------------- autorización

ROLE_MATRIX = [
    ("GET", "/admin/dashboard"), ("GET", "/admin/users"), ("GET", "/admin/audit"), ("GET", "/admin/reports/export"),
    ("POST", "/admin/areas"), ("GET", "/manager/dashboard"), ("POST", "/manager/content"),
    ("GET", "/worker/dashboard"),
]
ALLOWED_PREFIX = {"w1": "/worker", "mgr": "/manager", "adm": "/admin"}


@pytest.mark.parametrize("who", ["w1", "mgr", "adm"])
def test_each_role_only_reaches_its_own_routes(world, client_for, who):
    client = client_for(getattr(world, who))
    for method, path in ROLE_MATRIX:
        if path.startswith(ALLOWED_PREFIX[who]):
            continue
        r = client.request(method, f"{API}{path}", json={}, headers=csrf(client))
        assert r.status_code == 403, (who, method, path)


def test_anonymous_requests_are_rejected(world):
    anonymous = TestClient(app)
    for method, path in ROLE_MATRIX:
        if method == "GET":
            assert anonymous.get(f"{API}{path}").status_code == 401, path


def test_admin_cannot_touch_users_of_another_company(world, client_for, db):
    admin = client_for(world.adm)
    url = f"{API}/admin/users/{world.outsider.id}"
    assert admin.patch(url, json={"is_active": False}, headers=csrf(admin)).status_code == 404
    assert admin.delete(url, headers=csrf(admin)).status_code == 404
    db.expire_all()
    assert db.get(User, world.outsider.id).is_active is True


def test_admin_cannot_lock_themselves_out(world, client_for, db):
    admin = client_for(world.adm)
    url = f"{API}/admin/users/{world.adm.id}"
    assert admin.patch(url, json={"role": "worker"}, headers=csrf(admin)).status_code == 400
    assert admin.patch(url, json={"is_active": False}, headers=csrf(admin)).status_code == 400
    assert admin.delete(url, headers=csrf(admin)).status_code == 400
    db.expire_all()
    me = db.get(User, world.adm.id)
    assert me.role == "admin" and me.is_active


def test_extra_fields_cannot_escalate_privileges(world, client_for, db):
    """Asignación masiva: campos que no están en el esquema se ignoran."""
    admin = client_for(world.adm)
    payload = {"is_active": True, "company_id": world.other.id, "password_hash": "x", "totp_secret": None}
    assert admin.patch(f"{API}/admin/users/{world.w1.id}", json=payload, headers=csrf(admin)).status_code == 200
    db.expire_all()
    victim = db.get(User, world.w1.id)
    assert victim.company_id == world.co.id and victim.password_hash != "x"


def test_worker_cannot_read_drafts_or_other_companies_modules(world, client_for):
    worker = client_for(world.w1)
    assert worker.get(f"{API}/worker/modules/{world.mods[0].id}").status_code == 200
    assert worker.get(f"{API}/worker/modules/{world.draft.id}").status_code == 404
    assert worker.get(f"{API}/worker/modules/{world.foreign.id}").status_code == 404


def test_worker_cannot_write_answers_into_foreign_or_draft_modules(world, client_for, db):
    worker = client_for(world.w1)
    payload = {"phase": "pre", "responses": [{"dimension": "capacidad", "code": "C1", "value": 3}]}
    for module in (world.foreign, world.draft):
        assert worker.post(f"{API}/worker/modules/{module.id}/comb", json=payload, headers=csrf(worker)).status_code == 404
    assert db.scalars(select(CombResponse)).all() == []


def test_comb_payload_size_is_capped(world, client_for):
    worker = client_for(world.w1)
    payload = {"phase": "pre", "responses": [{"dimension": "capacidad", "code": f"C{i}", "value": 3} for i in range(21)]}
    assert worker.post(f"{API}/worker/modules/{world.mods[0].id}/comb", json=payload, headers=csrf(worker)).status_code == 422


def test_worker_cannot_answer_other_companies_challenges(world, client_for):
    worker = client_for(world.w1)
    r = worker.post(f"{API}/worker/challenges/{world.foreign_challenge.id}/answer", json={"choice": 1}, headers=csrf(worker))
    assert r.status_code == 404


def test_create_user_rejects_invalid_email(world, client_for):
    admin = client_for(world.adm)
    r = admin.post(f"{API}/admin/users", json={"name": "Xx", "email": "no-es-correo", "area": "Finanzas"}, headers=csrf(admin))
    assert r.status_code == 422


# -------------------------------------------------------------------- inyección

def test_csv_formula_injection_is_neutralized(world, client_for, db):
    db.add(Area(company_id=world.co.id, name='=HYPERLINK("http://evil.example","Clic")')); db.commit()
    csv = client_for(world.adm).get(f"{API}/admin/reports/export").text
    row = next(line for line in csv.splitlines() if "HYPERLINK" in line)
    assert row.startswith("\"'=HYPERLINK")                  # Excel lo muestra como texto, no lo ejecuta


def test_sql_injection_in_audit_search_is_inert(world, client_for):
    admin = client_for(world.adm)                           # el login deja eventos de auditoría
    r = admin.get(f"{API}/admin/audit", params={"q": "' OR 1=1 --"})
    assert r.status_code == 200 and r.json()["total"] == 0


# --------------------------------------------------------------------- cabeceras

def test_security_headers_on_api_responses(world):
    r = TestClient(app).get(f"{API}/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"
    assert r.headers["cache-control"] == "no-store"
    assert "strict-transport-security" not in r.headers     # sin HTTPS no se envía HSTS


def test_hsts_is_sent_when_cookies_are_https_only(world, monkeypatch):
    monkeypatch.setattr(settings, "cookie_secure", True)
    assert "max-age=31536000" in TestClient(app).get(f"{API}/health").headers["strict-transport-security"]


def test_rejected_requests_also_carry_security_headers(world, client_for):
    client = client_for(world.w1)
    r = client.post(f"{API}/worker/modules/{world.mods[0].id}/complete")   # sin CSRF -> 403
    assert r.status_code == 403 and r.headers["x-content-type-options"] == "nosniff"


def test_cors_only_allows_the_configured_frontend():
    preflight = {"access-control-request-method": "POST", "access-control-request-headers": "content-type"}
    evil = TestClient(app).options(f"{API}/auth/login", headers={"origin": "https://evil.example", **preflight})
    assert evil.headers.get("access-control-allow-origin") is None
    good = TestClient(app).options(f"{API}/auth/login", headers={"origin": "http://localhost:5173", **preflight})
    assert good.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.fixture
def production_app(monkeypatch):
    import app.main as main_module
    monkeypatch.setattr(settings, "app_env", "production")
    yield importlib.reload(main_module).app
    monkeypatch.setattr(settings, "app_env", "test")
    importlib.reload(main_module)


def test_api_docs_are_hidden_in_production(production_app):
    client = TestClient(production_app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path


# --------------------------------------------------------------- configuración

def make_settings(**overrides):
    base = {"jwt_secret_key": "s" * 40}
    return Settings(_env_file=None, **{**base, **overrides})


@pytest.mark.parametrize("overrides", [
    {"jwt_secret_key": "NATAKONG123"},                                  # secreto débil
    {"jwt_algorithm": "none"},                                          # firma desactivada
    {"frontend_origin": "*"},                                           # CORS abierto con cookies
    {"cookie_samesite": "none", "cookie_secure": False},
    {"audit_retention_days": 30},                                       # RNF: mínimo 12 meses
    {"app_env": "production", "cookie_secure": False},
    {"app_env": "production", "cookie_secure": True, "seed_demo_data": True},
])
def test_insecure_configuration_refuses_to_start(overrides):
    with pytest.raises(ValidationError):
        make_settings(**overrides)


def test_secure_production_configuration_is_accepted():
    s = make_settings(app_env="production", cookie_secure=True, trusted_proxy_hops=1)
    assert s.is_production


def test_dev_scripts_refuse_to_run_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(SystemExit, match="producción"):
        dev_totp.main("admin@inkasec.pe")
    with pytest.raises(SystemExit, match="producción"):
        dev_seed_challenges.main()
    with pytest.raises(RuntimeError, match="producción"):
        seed.seed_demo()


@pytest.mark.parametrize("password,secret,message", [
    ("corta", "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", "al menos 12"),
    ("una-clave-bien-larga", "esto-no-es-base32!", "Base32"),
    ("una-clave-bien-larga", "JBSW", "Base32"),
])
def test_bootstrap_admin_rejects_weak_settings(monkeypatch, password, secret, message):
    monkeypatch.setattr(settings, "bootstrap_admin_email", "admin@empresa.pe")
    monkeypatch.setattr(settings, "bootstrap_admin_password", password)
    monkeypatch.setattr(settings, "bootstrap_admin_totp_secret", secret)
    with pytest.raises(SystemExit, match=message):
        bootstrap_admin.validate_bootstrap_settings()


def test_bootstrap_admin_accepts_strong_settings(monkeypatch):
    monkeypatch.setattr(settings, "bootstrap_admin_email", "admin@empresa.pe")
    monkeypatch.setattr(settings, "bootstrap_admin_password", "una-clave-bien-larga")
    monkeypatch.setattr(settings, "bootstrap_admin_totp_secret", "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP")
    bootstrap_admin.validate_bootstrap_settings()
