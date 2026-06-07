from fastapi import FastAPI
import uvicorn


app = FastAPI(
    title="Management System",
    description="API для управления бизнесном"
)



if __name__ == "__main__":
    uvicorn.run("backend.src.main:app", host="127.0.0.1", port=8000, reload=True)
