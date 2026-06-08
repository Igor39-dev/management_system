from sqlalchemy.sql import text
from backend.src.config import settings
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


engine = create_async_engine(settings.DB_URL)

session = async_sessionmaker(engine, expire_on_commit=False)


async def check_db_connection():
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        return False
    return True


class Base(DeclarativeBase):
    pass
