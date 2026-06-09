import uvicorn
from fastapi import FastAPI, HTTPException
from sqlalchemy import text

from backend.src.api.auth import router as auth_router
from backend.src.api.dependencies import DBDep


app = FastAPI(
    title="Management System",
    description="API для управления бизнесном",
)

app.include_router(auth_router)


@app.get("/health", tags=["Check DB connection"])
async def health_check(db: DBDep):
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=500, detail="Нет подлючения к базе данных")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("backend.src.main:app", host="127.0.0.1", port=8000, reload=True)
