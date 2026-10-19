from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.utils import unique_path, cleanup_files, validate_ext, libre_convert, save_upload_file_sync, logger

router = APIRouter(prefix="/convert", tags=["Office"])

OFFICE_EXTENSIONS = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".html", ".htm", ".epub"}
WORD_EXTENSIONS = {".doc", ".docx", ".odt", ".rtf"}
EXCEL_EXTENSIONS = {".xls", ".xlsx"}
PPT_EXTENSIONS = {".ppt", ".pptx"}


@router.post("/office-to-pdf")
def convert_office_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, OFFICE_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        save_upload_file_sync(file, input_path)
        output_path = libre_convert(input_path, ".pdf")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return _pdf_response(file.filename, output_path)
    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("office-to-pdf failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


@router.post("/word-to-pdf")
def convert_word_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    return convert_office_to_pdf(background_tasks, file)


@router.post("/word-to-html")
def convert_word_to_html(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, WORD_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        save_upload_file_sync(file, input_path)
        output_path = libre_convert(input_path, ".html")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="text/html",
            filename=f"{Path(file.filename).stem}.html",
        )
    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("word-to-html failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


@router.post("/excel-to-csv")
def convert_excel_to_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, EXCEL_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        save_upload_file_sync(file, input_path)
        output_path = libre_convert(input_path, ".csv")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="text/csv",
            filename=f"{Path(file.filename).stem}.csv",
        )
    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("excel-to-csv failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


@router.post("/powerpoint-to-pdf")
def convert_powerpoint_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, PPT_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        save_upload_file_sync(file, input_path)
        output_path = libre_convert(input_path, ".pdf")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return _pdf_response(file.filename, output_path)
    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("powerpoint-to-pdf failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")

# ── Shared helpers ────────────────────────────────────────────────────────


def _pdf_response(original_name: str, pdf_path: Path):
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{Path(original_name).stem}.pdf",
    )
