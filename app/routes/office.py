from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.utils import unique_path, cleanup_files, validate_ext, libre_convert, save_upload_file

router = APIRouter(prefix="/convert", tags=["Office"])

OFFICE_EXTENSIONS = {".doc", ".docx", ".odt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".html", ".htm", ".epub"}
WORD_EXTENSIONS = {".doc", ".docx", ".odt", ".rtf"}
EXCEL_EXTENSIONS = {".xls", ".xlsx"}
PPT_EXTENSIONS = {".ppt", ".pptx"}


@router.post("/office-to-pdf")
async def convert_office_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, OFFICE_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        await save_upload_file(file, input_path)
        output_path = libre_convert(input_path, ".pdf")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return _pdf_response(file.filename, output_path)
    except Exception as exc:
        cleanup_files(input_path)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, f"Conversion failed: {exc}")


@router.post("/word-to-pdf")
async def convert_word_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    return await convert_office_to_pdf(background_tasks, file)


@router.post("/word-to-html")
async def convert_word_to_html(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, WORD_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        await save_upload_file(file, input_path)
        output_path = libre_convert(input_path, ".html")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="text/html",
            filename=f"{Path(file.filename).stem}.html",
        )
    except Exception as exc:
        cleanup_files(input_path)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, f"Conversion failed: {exc}")


@router.post("/excel-to-csv")
async def convert_excel_to_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, EXCEL_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        await save_upload_file(file, input_path)
        output_path = libre_convert(input_path, ".csv")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="text/csv",
            filename=f"{Path(file.filename).stem}.csv",
        )
    except Exception as exc:
        cleanup_files(input_path)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, f"Conversion failed: {exc}")


@router.post("/powerpoint-to-pdf")
async def convert_powerpoint_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    ext = validate_ext(file.filename, PPT_EXTENSIONS)
    input_path = unique_path(ext)
    try:
        await save_upload_file(file, input_path)
        output_path = libre_convert(input_path, ".pdf")
        background_tasks.add_task(cleanup_files, input_path, output_path)
        return _pdf_response(file.filename, output_path)
    except Exception as exc:
        cleanup_files(input_path)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, f"Conversion failed: {exc}")

# ── Shared helpers ────────────────────────────────────────────────────────


def _pdf_response(original_name: str, pdf_path: Path):
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{Path(original_name).stem}.pdf",
    )
