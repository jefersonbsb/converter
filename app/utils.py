import uuid
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from fastapi import HTTPException, UploadFile


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


async def save_upload_file(upload_file: UploadFile, destination: Path, chunk_size: int = 1024 * 1024) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as out:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)


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


def libre_convert(input_path: Path, output_ext: str, timeout: int = 120) -> Path:
    """
    Use LibreOffice headless to convert a file.
    Returns the path to the output file.
    """
    exe = _resolve_libreoffice_executable()
    args = [
        exe,
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
    env.setdefault("HOME", str(TEMP_DIR))
    env.setdefault("TMPDIR", str(TEMP_DIR))
    env.setdefault("USERPROFILE", str(TEMP_DIR))

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

    if result.returncode != 0:
        raise HTTPException(
            500, f"LibreOffice conversion failed: {result.stderr.strip()}"
        )

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
