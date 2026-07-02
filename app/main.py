from fastapi import FastAPI

from app.api.routes.extraction import router as extraction_router
from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="FillForm",
        version="0.1.0",
        description=(
            "Evidence-based document extraction API for form filling. Upload a supported "
            "document and a JSON payload with questions; the service returns structured "
            "answers only when they are supported by document evidence."
        ),
        openapi_tags=[
            {
                "name": "extraction",
                "description": (
                    "Run synchronous extractions or create asynchronous extraction jobs."
                ),
            }
        ],
    )
    app.include_router(extraction_router, prefix="/api/v1/form-extraction", tags=["extraction"])
    return app


app = create_app()
