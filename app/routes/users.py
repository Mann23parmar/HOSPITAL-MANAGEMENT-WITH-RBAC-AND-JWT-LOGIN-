from fastapi import APIRouter, Depends
from app.schemas.user import UserCreate, UserStatusUpdate
from app.services.auth_service import get_current_user
from app.core.rbac import require_role
from app.services.users_service import (
    create_user as create_user_workflow,
    update_user_status as update_user_status_workflow,
)


router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", dependencies=[Depends(require_role("admin"))], status_code=201)
def create_user(user: UserCreate, current_user: dict = Depends(get_current_user)):
    return create_user_workflow(user, current_user)


@router.patch("/{user_id}/status", dependencies=[Depends(require_role("admin"))])
def update_user_status(
    user_id: str,
    status: UserStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    return update_user_status_workflow(user_id, status, current_user)
