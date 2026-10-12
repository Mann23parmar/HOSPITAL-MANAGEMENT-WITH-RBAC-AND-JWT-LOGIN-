from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.user import UserLogin
from app.services.auth_service import (
    get_current_user,
    login_user,
    logout_user,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/login")
@limiter.limit("5/minute")
def login(user: UserLogin, request: Request):
    return login_user(user)


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user)):
    return logout_user(current_user)
