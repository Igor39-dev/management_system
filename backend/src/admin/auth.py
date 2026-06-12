from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from backend.src.config import settings
from backend.src.database import session as session_factory
from backend.src.models.enums import UserRole
from backend.src.services.auth import AuthService, InvalidCredentialsError


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        email = form.get("username")
        password = form.get("password")
        if not email or not password:
            return False

        async with session_factory() as db:
            try:
                user = await AuthService.login(db, str(email), str(password))
            except InvalidCredentialsError:
                return False

            if user.role != UserRole.ADMIN and not user.is_superuser:
                return False

            request.session["admin_user_id"] = user.id
            return True

    async def logout(self, request: Request) -> RedirectResponse:
        request.session.clear()
        return RedirectResponse(request.url_for("admin:login"), status_code=302)

    async def authenticate(self, request: Request) -> bool:
        admin_user_id = request.session.get("admin_user_id")
        if admin_user_id is None:
            return False

        async with session_factory() as db:
            user = await AuthService.get_user_by_id(db, int(admin_user_id))
            if user is None or not user.is_active:
                request.session.clear()
                return False
            if user.role != UserRole.ADMIN and not user.is_superuser:
                request.session.clear()
                return False

        return True


admin_auth_backend = AdminAuth(secret_key=settings.JWT_SECRET_KEY)
