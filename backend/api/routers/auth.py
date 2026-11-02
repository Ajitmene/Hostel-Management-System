from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from accounts.models import User
from api.core.config import get_settings
from api.core.db import DBRoute
from api.core.errors import ApiError
from api.core.security import (ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE, clear_auth_cookies,
                               create_access_token, set_auth_cookies)
from api.dependencies import client_ip, get_current_user, verify_csrf
from api.schemas.auth import ChangePasswordRequest, LoginRequest, SessionOut, TokenOut
from api.schemas.common import Message
from api.services import audit
from api.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"], route_class=DBRoute, dependencies=[Depends(verify_csrf)])


def _session(user: User, tokens: dict) -> dict:
    return {"user": auth_service.serialize_user(user), "csrf_token": tokens["csrf"], "expires_in": tokens["access_seconds"]}


def _apply(response: Response, tokens: dict) -> None:
    set_auth_cookies(response, tokens["access"], tokens["access_seconds"], tokens["refresh"], tokens["csrf"])


@router.post("/login", response_model=SessionOut, summary="Sign in",
             description="Checks the credentials and sets HttpOnly cookies (access token, refresh token, CSRF token). "
                         "Roles: anyone with an active account.",
             responses={401: {"description": "Incorrect email or password"}})
def login(body: LoginRequest, request: Request, response: Response):
    user = auth_service.authenticate_user(body.email, body.password, client_ip(request))
    tokens = auth_service.issue_tokens(user)
    _apply(response, tokens)
    audit.record(user, "auth.login", "user", user.id, {}, client_ip(request))
    return _session(user, tokens)


@router.post("/token", response_model=TokenOut, summary="Get a bearer token (Swagger/Postman)",
             description="OAuth2 password flow used by Swagger UI's Authorize button and Postman. "
                         "Enter the account email in the `username` field. Disabled in production.")
def issue_bearer_token(request: Request, form: OAuth2PasswordRequestForm = Depends()):
    if not get_settings().enable_bearer_token_endpoint:
        raise ApiError(404, "not_found", "Not found.")
    user = auth_service.authenticate_user(form.username, form.password, client_ip(request))
    token, seconds = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "expires_in": seconds}


@router.post("/refresh", response_model=SessionOut, summary="Rotate the refresh token")
def refresh(request: Request, response: Response):
    user, tokens = auth_service.rotate_refresh_token(request.cookies.get(REFRESH_COOKIE))
    _apply(response, tokens)
    return _session(user, tokens)


@router.post("/logout", response_model=Message, summary="Sign out")
def logout(request: Request, response: Response):
    user = auth_service.revoke_presented_token(request.cookies.get(REFRESH_COOKIE))
    if user:
        audit.record(user, "auth.logout", "user", user.id, {}, client_ip(request))
    clear_auth_cookies(response)
    return {"message": "Signed out."}


@router.get("/me", response_model=SessionOut, summary="Current user")
def me(request: Request, user: User = Depends(get_current_user)):
    return {"user": auth_service.serialize_user(user), "csrf_token": request.cookies.get(CSRF_COOKIE), "expires_in": None}


@router.post("/change-password", response_model=SessionOut, summary="Change your own password")
def change_password(body: ChangePasswordRequest, request: Request, response: Response,
                    user: User = Depends(get_current_user)):
    tokens = auth_service.change_password(user, body.current_password, body.new_password, client_ip(request))
    _apply(response, tokens)
    return _session(user, tokens)
