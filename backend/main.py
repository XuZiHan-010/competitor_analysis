from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.auth import router as auth_router
from api.routes.health import router as health_router
from api.routes.reports import router as reports_router
from api.routes.scoping import router as scoping_router
from api.routes.stream import router as stream_router
from api.routes.survey import router as survey_router
from api.routes.tasks import router as tasks_router
from api.routes.validation import router as validation_router
from settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(health_router)
    app.include_router(scoping_router)
    app.include_router(survey_router)
    app.include_router(tasks_router)
    app.include_router(stream_router)
    app.include_router(reports_router)
    app.include_router(validation_router)
    return app


app = create_app()
