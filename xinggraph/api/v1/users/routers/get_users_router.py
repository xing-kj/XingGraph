from xinggraph.modules.users.get_fastapi_users import get_fastapi_users
from xinggraph.modules.users.models.User import UserRead, UserUpdate


def get_users_router():
    return get_fastapi_users().get_users_router(UserRead, UserUpdate)
