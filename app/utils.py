import uuid
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException


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
