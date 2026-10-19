from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.utils import unique_path, cleanup_files, validate_ext, libre_convert, save_upload_file_sync, logger

router = APIRouter(prefix="/convert", tags=["E-books & Web"])


@router.post("/epub-to-pdf")
def convert_epub_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    validate_ext(file.filename, {".epub"})
    input_path = unique_path(".epub")
    try:
        save_upload_file_sync(file, input_path)
        output_path = libre_convert(input_path, ".pdf")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=f"{Path(file.filename).stem}.pdf",
        )
    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("epub-to-pdf failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


@router.post("/html-to-pdf")
def convert_html_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    validate_ext(file.filename, {".html", ".htm"})
    input_path = unique_path(Path(file.filename).suffix.lower())
    try:
        save_upload_file_sync(file, input_path)
        output_path = libre_convert(input_path, ".pdf")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=f"{Path(file.filename).stem}.pdf",
        )
    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("html-to-pdf failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")
