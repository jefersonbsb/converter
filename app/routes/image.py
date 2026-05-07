from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from PIL import Image

from app.utils import unique_path, cleanup_files, validate_ext

router = APIRouter(prefix="/convert", tags=["Image"])

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

IMAGE_FORMAT_MAP = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WebP",
    ".bmp": "BMP",
    ".tiff": "TIFF",
    ".tif": "TIFF",
}

IMAGE_OUTPUT_OPTIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

MEDIA_MAP = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
}


@router.post("/image")
async def convert_image_format(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    to: str = Query("png", description="Target format: png, jpg, webp, bmp, tiff"),
):
    ext = validate_ext(file.filename, IMAGE_EXTENSIONS)
    target_ext = f".{to.lower().replace('jpeg', 'jpg')}"
    if target_ext not in IMAGE_OUTPUT_OPTIONS:
        raise HTTPException(400, f"Target format '{to}' is not supported.")

    input_path = unique_path(ext)
    output_path = input_path.with_suffix(target_ext)
    try:
        content = await file.read()
        input_path.write_bytes(content)

        image = Image.open(input_path)
        if image.mode in ("RGBA", "P") and target_ext in (".jpg", ".jpeg"):
            image = image.convert("RGB")

        save_format = IMAGE_FORMAT_MAP[target_ext]
        image.save(output_path, save_format)

        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type=MEDIA_MAP.get(target_ext, "application/octet-stream"),
            filename=f"{Path(file.filename).stem}{target_ext}",
        )
    except Exception as exc:
        cleanup_files(input_path, output_path)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(500, f"Conversion failed: {exc}")
