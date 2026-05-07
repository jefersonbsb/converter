from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import office, pdf, image, ebook, root


def create_app() -> FastAPI:
    app = FastAPI(title="File Converter API", version="2.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    app.include_router(root.router)
    app.include_router(office.router)
    app.include_router(pdf.router)
    app.include_router(image.router)
    app.include_router(ebook.router)

    return app
