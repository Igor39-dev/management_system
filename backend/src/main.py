from fastapi import FastAPI, HTTPException
import uvicorn

from backend.src.database import check_db_connection


app = FastAPI(
    title="Management System",
    description="API для управления бизнесном"
)

@app.get("/health", tags=["Check DB connection"])
async def health_check():

    db_ok = await check_db_connection()
    if not db_ok:
        raise HTTPException(status_code=500, detail="Database connection failed")
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("backend.src.main:app", host="127.0.0.1", port=8000, reload=True)
