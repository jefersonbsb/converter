from pathlib import Path

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from app.utils import get_job, pop_job, cleanup_files

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
    return FileResponse(
        path=str(index_path),
        media_type="text/html",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/jobs/{job_id}", include_in_schema=False)
async def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress", 0),
        "message": job.get("message", ""),
    }


@router.get("/jobs/{job_id}/download", include_in_schema=False)
async def job_download(job_id: str, background_tasks: BackgroundTasks):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado.")
    status = job.get("status")
    if status == "running":
        raise HTTPException(409, "Conversão ainda em andamento.")
    if status == "error":
        raise HTTPException(422, job.get("message") or "Falha na conversão.")

    output_path = job.get("output_path")
    input_path = job.get("input_path")
    download_name = job.get("download_name") or "converted.file"
    media_type = job.get("media_type") or "application/octet-stream"

    if not isinstance(output_path, Path) or not output_path.exists():
        raise HTTPException(500, "Arquivo de saída não encontrado.")

    def finalize() -> None:
        if isinstance(input_path, Path):
            cleanup_files(input_path)
        if isinstance(output_path, Path):
            cleanup_files(output_path)
        pop_job(job_id)

    background_tasks.add_task(finalize)
    return FileResponse(
        path=str(output_path),
        media_type=media_type,
        filename=download_name,
    )
