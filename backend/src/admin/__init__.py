from pathlib import Path

from fastapi import FastAPI
from sqladmin import Admin

from backend.src.admin.auth import admin_auth_backend
from backend.src.admin.views import EvaluationAdmin, MeetingAdmin, TaskAdmin, TaskCommentAdmin, TeamAdmin, UserAdmin
from backend.src.database import engine, session

ADMIN_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def setup_admin(app: FastAPI) -> Admin:
    admin = Admin(
        app=app,
        engine=engine,
        session_maker=session,
        authentication_backend=admin_auth_backend,
        title="Management System",
        base_url="/admin",
        templates_dir=str(ADMIN_TEMPLATES_DIR),
    )
    admin.add_view(UserAdmin)
    admin.add_view(TeamAdmin)
    admin.add_view(TaskAdmin)
    admin.add_view(MeetingAdmin)
    admin.add_view(EvaluationAdmin)
    admin.add_view(TaskCommentAdmin)
    return admin
