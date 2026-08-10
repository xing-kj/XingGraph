from fastapi import APIRouter, HTTPException, Depends
from xinggraph.api.DTO import InDTO
from pydantic import EmailStr

from xinggraph.modules.users.models.User import User
from xinggraph.modules.users.methods import get_authenticated_user
from xinggraph.modules.users.methods.get_user_id_by_email import get_user_id_by_email


class UserEmailRequest(InDTO):
    email: EmailStr


def get_user_id_by_email_router() -> APIRouter:
    router = APIRouter()

    @router.post("/get-user-id")
    async def get_user_id(body: UserEmailRequest, user: User = Depends(get_authenticated_user)):
        user_id = await get_user_id_by_email(str(body.email))

        if user_id is None:
            raise HTTPException(status_code=404, detail="User not found")

        return {"user_id": str(user_id)}

    return router
