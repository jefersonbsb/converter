from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()


@router.get("/")
async def root():
    return {
        "status": "ok",
        "message": "File Converter API is running.",
        "version": "2.0.0",
        "endpoints": {
            "office_to_pdf": "/convert/office-to-pdf",
            "word_to_pdf": "/convert/word-to-pdf",
            "word_to_html": "/convert/word-to-html",
            "excel_to_csv": "/convert/excel-to-csv",
            "powerpoint_to_pdf": "/convert/powerpoint-to-pdf",
            "pdf_to_word": "/convert/pdf-to-word",
            "pdf_to_image": "/convert/pdf-to-image",
            "image_to_pdf": "/convert/image-to-pdf",
            "image_converter": "/convert/image",
            "epub_to_pdf": "/convert/epub-to-pdf",
            "html_to_pdf": "/convert/html-to-pdf",
        },
    }


@router.get("/ui", include_in_schema=False)
async def ui():
    index_path = Path(__file__).resolve().parents[2] / "index.html"
    if not index_path.exists():
        raise HTTPException(500, "index.html não encontrado no servidor.")
    return FileResponse(path=str(index_path), media_type="text/html")
