from fastapi import Depends, HTTPException
from app.services.auth_service import get_current_user


#this function is for role based access
def require_role(*allowed_roles: str):

    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):

        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission"
            )

        return current_user

    return role_checker

