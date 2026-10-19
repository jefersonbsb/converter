import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

logger = logging.getLogger("converter")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


# Maximum accepted upload size, enforced both at the request level (Content-Length)
# and while streaming the body to disk. Tune via the MAX_UPLOAD_SIZE_MB env var.
MAX_UPLOAD_SIZE_MB = max(1, _env_int("MAX_UPLOAD_SIZE_MB", 50))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024


TEMP_DIR = Path(tempfile.gettempdir()) / "file-converter-api"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def unique_path(ext: str) -> Path:
    """Return a unique file path inside the temporary directory."""
    return TEMP_DIR / f"{uuid.uuid4().hex}{ext}"


def cleanup_files(*paths: Path) -> None:
    """Safely remove files, ignoring errors."""
    for p in paths:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


def validate_ext(filename: str | None, allowed: set) -> str:
    """Validate file extension and return lowercase extension."""
    if not filename:
        raise HTTPException(400, "No file name provided.")
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        alts = ", ".join(sorted(allowed))
        raise HTTPException(400, f"Only {alts} files are accepted. Got '{ext}'.")
    return ext


def _read_head(path: Path, n: int) -> bytes:
    try:
        with path.open("rb") as f:
            return f.read(n)
    except OSError:
        return b""


def validate_signature(path: Path, ext: str) -> None:
    """Reject files whose magic bytes do not match the declared extension.

    Covers PDF and common raster formats. Office/EPUB/HTML files are validated
    by the underlying conversion tooling instead and are not checked here.
    """
    head = _read_head(path, 16)
    if ext == ".pdf":
        ok = head.startswith(b"%PDF")
    elif ext in (".jpg", ".jpeg"):
        ok = head.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        ok = head.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext == ".webp":
        ok = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    elif ext == ".bmp":
        ok = head.startswith(b"BM")
    elif ext in (".tif", ".tiff"):
        ok = head.startswith((b"II*\x00", b"MM\x00*"))
    else:
        return

    if not ok:
        cleanup_files(path)
        raise HTTPException(400, "Arquivo inválido: o conteúdo não corresponde à extensão informada.")


def save_upload_file_sync(upload_file: UploadFile, destination: Path, chunk_size: int = 1024 * 1024) -> None:
    """Stream an upload to disk synchronously, enforcing the upload size limit.

    Used by synchronous (CPU-bound) endpoints running in FastAPI's threadpool,
    where ``upload_file.file`` is already a complete spooled file object.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = upload_file.file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_SIZE_BYTES:
                    raise HTTPException(413, f"Arquivo excede o limite de {MAX_UPLOAD_SIZE_MB} MB.")
                out.write(chunk)
    except Exception:
        cleanup_files(destination)
        raise


def _resolve_libreoffice_executable() -> str:
    candidates: list[str] = []

    if os.name == "nt":
        env_soffice = os.environ.get("SOFFICE_PATH")
        if env_soffice:
            candidates.append(env_soffice)

        env_lo = os.environ.get("LIBREOFFICE_PATH")
        if env_lo:
            p = Path(env_lo)
            if p.is_dir():
                candidates.append(str(p / "program" / "soffice.exe"))
            else:
                candidates.append(env_lo)

        candidates.extend(
            [
                "soffice",
                "libreoffice",
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            ]
        )
    else:
        candidates.extend(["libreoffice", "soffice"])

    for c in candidates:
        if not c:
            continue
        if os.path.isabs(c) and Path(c).exists():
            return c
        which = shutil.which(c)
        if which:
            return which

    raise HTTPException(
        500,
        "LibreOffice não encontrado no servidor. Instale o LibreOffice e garanta que o executável (soffice/libreoffice) esteja no PATH, ou defina SOFFICE_PATH/LIBREOFFICE_PATH.",
    )


def prune_old_temp_files(max_age_seconds: int = 3600) -> None:
    """Remove orphaned temporary files older than max_age_seconds."""
    now = time.time()
    try:
        if not TEMP_DIR.exists():
            return
        for p in TEMP_DIR.iterdir():
            try:
                if p.is_file() and (now - p.stat().st_mtime) > max_age_seconds:
                    p.unlink(missing_ok=True)
                elif p.is_dir() and (now - p.stat().st_mtime) > max_age_seconds:
                    shutil.rmtree(p, ignore_errors=True)
            except Exception:
                pass
    except Exception:
        pass


def libre_convert(input_path: Path, output_ext: str, timeout: int = 85) -> Path:
    """
    Use LibreOffice headless to convert a file.
    Returns the path to the output file.
    """
    exe = _resolve_libreoffice_executable()
    profile_dir = TEMP_DIR / f"lo_profile_{uuid.uuid4().hex}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    profile_uri = profile_dir.as_uri()

    args = [
        exe,
        f"-env:UserInstallation={profile_uri}",
        "--headless",
        "--norestore",
        "--nolockcheck",
        "--nodefault",
        "--nofirststartwizard",
        "--convert-to",
        output_ext.lstrip("."),
        "--outdir",
        str(TEMP_DIR),
        str(input_path),
    ]

    env = os.environ.copy()
    env.setdefault("HOME", str(profile_dir))
    env.setdefault("TMPDIR", str(TEMP_DIR))
    env.setdefault("USERPROFILE", str(profile_dir))

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            500,
            f"LibreOffice não encontrado no servidor ({exc}). Instale o LibreOffice e garanta que o executável esteja no PATH.",
        )
    except subprocess.TimeoutExpired:
        logger.error("LibreOffice conversion timed out after %ds", timeout)
        raise HTTPException(504, "Tempo limite excedido na conversão do arquivo.")
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    if result.returncode != 0:
        logger.error("LibreOffice conversion failed: %s", result.stderr.strip())
        raise HTTPException(500, "Falha na conversão do arquivo (LibreOffice).")

    # LibreOffice saves output with the same stem as the input
    output_path = input_path.with_suffix(output_ext)
    if not output_path.exists():
        # LibreOffice may add a filter suffix – try to find the file
        for f in TEMP_DIR.iterdir():
            if f.stem == input_path.stem and f.suffix == output_ext:
                output_path = f
                break
        else:
            raise HTTPException(500, "Output file not found after conversion.")

    return output_path


_JOB_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def _cleanup_old_jobs(max_age_seconds: int = 3600) -> None:
    prune_old_temp_files(max_age_seconds)
    now = time.time()
    with _JOB_LOCK:
        expired = [
            job_id
            for job_id, job in _JOBS.items()
            if now - float(job.get("created_at", now)) > max_age_seconds
        ]
        for job_id in expired:
            job = _JOBS.pop(job_id, None)
            if job:
                in_path = job.get("input_path")
                out_path = job.get("output_path")
                if isinstance(in_path, Path):
                    cleanup_files(in_path)
                if isinstance(out_path, Path):
                    cleanup_files(out_path)


def create_job() -> str:
    _cleanup_old_jobs()
    job_id = uuid.uuid4().hex
    with _JOB_LOCK:
        _JOBS[job_id] = {
            "status": "running",
            "progress": 0,
            "message": "",
            "created_at": time.time(),
            "input_path": None,
            "output_path": None,
            "download_name": None,
            "media_type": None,
        }
    return job_id


def update_job(
    job_id: str,
    *,
    progress: int | None = None,
    status: str | None = None,
    message: str | None = None,
) -> None:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        if progress is not None:
            job["progress"] = max(0, min(100, int(progress)))
        if status is not None:
            job["status"] = status
        if message is not None:
            job["message"] = message


def attach_job_files(job_id: str, *, input_path: Path | None = None) -> None:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        if input_path is not None:
            job["input_path"] = input_path


def complete_job(
    job_id: str,
    *,
    output_path: Path,
    download_name: str,
    media_type: str,
) -> None:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job["status"] = "done"
        job["progress"] = 100
        job["output_path"] = output_path
        job["download_name"] = download_name
        job["media_type"] = media_type


def fail_job(job_id: str, *, message: str) -> None:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if not job:
            return
        job["status"] = "error"
        job["message"] = message


def get_job(job_id: str) -> dict | None:
    _cleanup_old_jobs()
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def pop_job(job_id: str) -> dict | None:
    with _JOB_LOCK:
        job = _JOBS.pop(job_id, None)
        return dict(job) if job else None
