from fastapi import APIRouter

from server_modules.app_runtime import using_postgres


router = APIRouter()


@router.get("/api/health")
def health():
    return {
        "ok": True,
        "framework": "fastapi",
        "database_backend": "postgres" if using_postgres() else "sqlite",
    }
