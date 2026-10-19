import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.middleware import RateLimitMiddleware, UploadSizeLimitMiddleware
from app.routes import office, pdf, image, ebook, root


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

    app = FastAPI(title="File Converter API", version="2.0.0", docs_url=None, redoc_url=None)

    app.add_middleware(UploadSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Original-Size", "X-Compressed-Size"],
    )

    app.include_router(root.router)
    app.include_router(office.router)
    app.include_router(pdf.router)
    app.include_router(image.router)
    app.include_router(ebook.router)

    src_dir = Path(__file__).resolve().parents[1] / "src"
    if src_dir.exists():
        app.mount("/src", StaticFiles(directory=str(src_dir)), name="src")

    return app
