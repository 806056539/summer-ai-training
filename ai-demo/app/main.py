from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.database import engine, Base
from app.routers import user_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="User CRUD API",
    description="FastAPI project with layered architecture: router / service / repository.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(user_router.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.get("/")
def root():
    return FileResponse("app/static/index.html")
