"""FastAPI application entry point.

Run locally:
    uvicorn app.main:app --reload
Docs:
    http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .errors import install_error_handlers
from .routers import catalog, health, products

DESCRIPTION = """
PriceMatch backend (Team 03). Search products, list every store's offer for a
product sorted by price, and read price history.

All errors share one shape:

```json
{"error": {"code": "not_found", "message": "Product 42 not found", "details": null}}
```
"""


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=DESCRIPTION,
        contact={"name": "Team 03 - Database & Backend"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    app.include_router(health.router)
    app.include_router(products.router, prefix=settings.api_prefix)
    app.include_router(catalog.router, prefix=settings.api_prefix)
    return app


app = create_app()
