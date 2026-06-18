"""FastAPI 应用入口模块。

定义 FastAPI 应用实例、全局异常处理、健康检查与根路径。
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import user_router

# ----------------------------------------------------------
# 初始化
# ----------------------------------------------------------

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="User CRUD API",
    description=(
        "FastAPI project with layered architecture: "
        "router / service / repository."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(user_router.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ============================================================
# 异常处理
# ============================================================


@app.exception_handler(Exception)
async def global_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    """全局异常处理，将所有未捕获异常转为 500 JSON 响应。

    Args:
        _request: 触发异常的请求（本处理中未使用）。
        exc: 被捕获的异常实例。

    Returns:
        包含错误详情的 JSONResponse。
    """
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


# ============================================================
# 基础路由
# ============================================================


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """健康检查接口。

    Returns:
        包含状态信息的字典。
    """
    return {"status": "ok"}


@app.get("/")
def root() -> FileResponse:
    """根路径，返回静态前端页面。

    Returns:
        index.html 的 FileResponse。
    """
    return FileResponse("app/static/index.html")
