from accounts.models import RefreshToken, User
from tests.conftest import ADMIN_PASSWORD, EMPLOYEE_PASSWORD


def test_login_success_sets_httponly_cookies(client, admin_user):
    r = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["role"] == "admin" and body["csrf_token"]
    assert "password" not in str(body)
    cookies = r.headers.get_list("set-cookie")
    assert any(c.startswith("access_token=") and "HttpOnly" in c for c in cookies)
    assert any(c.startswith("refresh_token=") and "HttpOnly" in c for c in cookies)


def test_login_wrong_password_and_unknown_email_look_identical(client, admin_user):
    bad = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong-password"})
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert bad.json()["error"]["code"] == "invalid_credentials"


def test_missing_token_is_401_with_standard_error_shape(client):
    r = client.get("/api/v1/students")
    assert r.status_code == 401
    assert set(r.json()["error"]) == {"code", "message", "details"}


def test_garbage_token_is_rejected(client):
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "invalid_token"


def test_me_returns_role_and_permissions(client, admin_h, emp_h):
    assert client.get("/api/v1/auth/me", headers=admin_h).json()["user"]["role"] == "admin"
    emp = client.get("/api/v1/auth/me", headers=emp_h).json()["user"]
    assert emp["role"] == "employee" and "students.view" in emp["permissions"] and emp["employee_id"] == "EMP-001"


def test_inactive_user_cannot_log_in(client, employee_user):
    employee_user.is_active = False
    employee_user.save()
    r = client.post("/api/v1/auth/login", json={"email": "emp@example.com", "password": EMPLOYEE_PASSWORD})
    assert r.status_code == 401


def test_deactivating_user_invalidates_existing_token(client, emp_h, employee_user):
    assert client.get("/api/v1/students", headers=emp_h).status_code == 200
    employee_user.is_active = False
    employee_user.save()
    r = client.get("/api/v1/students", headers=emp_h)
    assert r.status_code == 401 and r.json()["error"]["code"] in {"account_inactive", "token_revoked"}


def test_role_change_invalidates_existing_token(client, emp_h, employee_user):
    employee_user.role = "admin"
    employee_user.save()
    assert client.get("/api/v1/students", headers=emp_h).status_code == 401


def test_cookie_login_requires_csrf_header_for_writes(client, admin_user):
    login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD}).json()
    from tests.conftest import student_payload
    # cookies are now stored in the client; no CSRF header -> rejected
    r = client.post("/api/v1/students", json=student_payload())
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf_failed"
    r = client.post("/api/v1/students", json=student_payload(), headers={"X-CSRF-Token": login["csrf_token"]})
    assert r.status_code == 201


def test_refresh_rotates_and_reuse_is_rejected(client, admin_user):
    login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD}).json()
    old_refresh = client.cookies.get("refresh_token")
    r = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": login["csrf_token"]})
    assert r.status_code == 200
    new_csrf = r.json()["csrf_token"]
    assert client.cookies.get("refresh_token") != old_refresh
    # replay the old refresh token
    client.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
    r = client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": new_csrf})
    assert r.status_code == 401
    assert RefreshToken.objects.filter(user=admin_user, revoked_at__isnull=True).count() == 0


def test_logout_revokes_refresh_token(client, admin_user):
    login = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": ADMIN_PASSWORD}).json()
    r = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": login["csrf_token"]})
    assert r.status_code == 200
    assert RefreshToken.objects.filter(user=admin_user, revoked_at__isnull=True).count() == 0


def test_change_password(client, admin_h, admin_user):
    r = client.post("/api/v1/auth/change-password", headers=admin_h,
                    json={"current_password": "wrong-one-123", "new_password": "Another-long-pass-9"})
    assert r.status_code == 400
    r = client.post("/api/v1/auth/change-password", headers=admin_h,
                    json={"current_password": ADMIN_PASSWORD, "new_password": "Another-long-pass-9"})
    assert r.status_code == 200
    assert User.objects.get(pk=admin_user.pk).check_password("Another-long-pass-9")
    # the old access token no longer works
    assert client.get("/api/v1/auth/me", headers=admin_h).status_code == 401


def test_user_model_never_lets_employee_be_staff(employee_user):
    employee_user.is_staff = True
    employee_user.is_superuser = True
    employee_user.save()
    employee_user.refresh_from_db()
    assert not employee_user.is_staff and not employee_user.is_superuser


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "database": "up"}
