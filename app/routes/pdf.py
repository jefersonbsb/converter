import os
import shutil
import zipfile
import threading
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

from app.utils import (
    unique_path,
    cleanup_files,
    validate_ext,
    validate_signature,
    save_upload_file_sync,
    create_job,
    update_job,
    attach_job_files,
    complete_job,
    fail_job,
    logger,
)

router = APIRouter(prefix="/convert", tags=["PDF"])


# ── PDF → Word ────────────────────────────────────────────────────────────

@router.post("/pdf-to-word")
def convert_pdf_to_word(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ocr: bool = Query(False, description="Ativa OCR quando o PDF não possui texto extraível"),
    ocr_lang: str = Query("por", description="Idioma do OCR (ex.: por, eng, por+eng)"),
    ocr_dpi: int = Query(200, description="Resolução (DPI) usada para OCR"),
):
    validate_ext(file.filename, {".pdf"})
    input_path = unique_path(".pdf")
    output_path = input_path.with_suffix(".docx")
    try:
        save_upload_file_sync(file, input_path)
        validate_signature(input_path, ".pdf")

        def docx_has_meaningful_text(path: Path) -> bool:
            try:
                from docx import Document
            except Exception:
                return False

            try:
                doc = Document(str(path))
            except Exception:
                return False

            text_parts: list[str] = []

            for p in doc.paragraphs:
                if p.text:
                    text_parts.append(p.text)

            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text:
                            text_parts.append(cell.text)

            combined = "\n".join(text_parts).strip()
            return len(combined) > 0

        def build_docx_from_pdf_text(pdf_path: Path, docx_path: Path) -> None:
            import fitz
            from docx import Document

            pdf = fitz.open(str(pdf_path))
            doc = Document()

            for i in range(len(pdf)):
                page = pdf[i]
                words = page.get_text("words") or []
                lines: dict[tuple[int, int], dict] = {}
                for w in words:
                    x0, y0, x1, y1, text, block_no, line_no, word_no = w
                    text = (text or "").strip()
                    if not text:
                        continue
                    key = (int(block_no), int(line_no))
                    item = lines.get(key)
                    if not item:
                        item = {"y0": float(y0), "x0": float(x0), "parts": []}
                        lines[key] = item
                    else:
                        if float(y0) < item["y0"]:
                            item["y0"] = float(y0)
                        if float(x0) < item["x0"]:
                            item["x0"] = float(x0)
                    item["parts"].append((float(x0), text))

                ordered = sorted(
                    lines.values(),
                    key=lambda it: (it["y0"], it["x0"]),
                )

                rendered_lines: list[str] = []
                for it in ordered:
                    parts = sorted(it["parts"], key=lambda p: p[0])
                    line_text = " ".join(t for _, t in parts).strip()
                    if line_text:
                        rendered_lines.append(line_text)

                normalized_lines: list[str] = []
                for line_text in rendered_lines:
                    if (
                        normalized_lines
                        and normalized_lines[-1].endswith("-")
                        and line_text[:1].islower()
                    ):
                        normalized_lines[-1] = normalized_lines[-1][:-1] + line_text
                    else:
                        normalized_lines.append(line_text)

                for line_text in normalized_lines:
                    if line_text:
                        doc.add_paragraph(line_text)
                if i < len(pdf) - 1:
                    doc.add_page_break()

            pdf.close()
            doc.save(str(docx_path))

        def build_docx_from_pdf_ocr(pdf_path: Path, docx_path: Path) -> None:
            try:
                import pytesseract
            except Exception as exc:
                logger.exception("pytesseract unavailable for OCR")
                raise HTTPException(500, "OCR não está disponível no servidor (pytesseract).")

            try:
                import fitz
            except Exception as exc:
                logger.exception("PyMuPDF unavailable for OCR")
                raise HTTPException(500, "Falha ao carregar PyMuPDF para OCR.")

            try:
                from PIL import Image
            except Exception as exc:
                logger.exception("Pillow unavailable for OCR")
                raise HTTPException(500, "Falha ao carregar Pillow para OCR.")

            from docx import Document

            pdf = fitz.open(str(pdf_path))
            doc = Document()
            scale = max(1.0, ocr_dpi / 72)
            matrix = fitz.Matrix(scale, scale)

            for i in range(len(pdf)):
                page = pdf[i]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                if pix.n == 1:
                    mode = "L"
                elif pix.n == 3:
                    mode = "RGB"
                elif pix.n == 4:
                    mode = "RGBA"
                else:
                    mode = "RGB"

                img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                if img.mode != "RGB":
                    img = img.convert("RGB")

                text = (pytesseract.image_to_string(img, lang=ocr_lang) or "").strip()
                if text:
                    for line in text.splitlines():
                        line = line.strip()
                        if line:
                            doc.add_paragraph(line)
                if i < len(pdf) - 1:
                    doc.add_page_break()

            pdf.close()
            doc.save(str(docx_path))

        pdf2docx_error: Exception | None = None
        try:
            from pdf2docx import Converter as PdfToDocxConverter

            cv = PdfToDocxConverter(str(input_path))
            cv.convert(str(output_path), start=0, end=None)
            cv.close()
        except Exception as err:
            pdf2docx_error = err

        if output_path.exists() and not docx_has_meaningful_text(output_path):
            cleanup_files(output_path)

        if (not output_path.exists()) or (not docx_has_meaningful_text(output_path)):
            try:
                build_docx_from_pdf_text(input_path, output_path)
            except Exception:
                cleanup_files(output_path)

        if output_path.exists() and not docx_has_meaningful_text(output_path) and ocr:
            cleanup_files(output_path)
            build_docx_from_pdf_ocr(input_path, output_path)

        if output_path.exists() and not docx_has_meaningful_text(output_path):
            cleanup_files(output_path)
            if pdf2docx_error:
                raise HTTPException(
                    422,
                    "PDF parece ser escaneado ou não possui texto extraível; use o parâmetro ocr=true para tentar OCR.",
                )
            raise HTTPException(
                422,
                "PDF não possui texto extraível; use o parâmetro ocr=true para tentar OCR.",
            )

        if not output_path.exists():
            # Try to find the output file with a different name
            for f in input_path.parent.iterdir():
                if f.stem.startswith(input_path.stem.split("_")[0]) and f.suffix == ".docx":
                    output_path = f
                    break
            else:
                raise HTTPException(500, "DOCX output not found after conversion.")

        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{Path(file.filename).stem}.docx",
        )
    except HTTPException:
        cleanup_files(input_path, output_path)
        raise
    except Exception as exc:
        cleanup_files(input_path, output_path)
        logger.exception("pdf-to-word failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


@router.post("/pdf-to-word-job")
def convert_pdf_to_word_job(
    file: UploadFile = File(...),
    engine: str = Query("auto", description="auto, pdf2docx, text, ocr"),
    ocr: bool = Query(False, description="Ativa OCR quando o PDF não possui texto extraível"),
    ocr_lang: str = Query("por", description="Idioma do OCR (ex.: por, eng, por+eng)"),
    ocr_dpi: int = Query(200, description="Resolução (DPI) usada para OCR"),
    start_page: int = Query(1, ge=1, description="Página inicial (1-based)"),
    end_page: int | None = Query(None, ge=1, description="Página final (1-based, inclusiva)"),
):
    validate_ext(file.filename, {".pdf"})
    input_path = unique_path(".pdf")
    output_path = input_path.with_suffix(".docx")

    save_upload_file_sync(file, input_path)
    validate_signature(input_path, ".pdf")

    job_id = create_job()
    attach_job_files(job_id, input_path=input_path)
    update_job(job_id, progress=0, status="running")

    download_name = f"{Path(file.filename).stem}.docx"
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def progress_cb(pct: int) -> None:
        update_job(job_id, progress=pct)

    def worker() -> None:
        out_path = output_path
        progress_stop = threading.Event()
        try:
            progress_cb(5)
            update_job(job_id, message="Analisando PDF…")

            import fitz

            pdf = fitz.open(str(input_path))
            total_pages = len(pdf) or 1
            pdf.close()

            sp = int(start_page)
            ep = int(end_page) if end_page is not None else int(total_pages)
            if sp < 1 or ep < 1 or sp > ep:
                raise HTTPException(400, "Intervalo de páginas inválido.")
            if sp > total_pages:
                raise HTTPException(400, f"start_page fora do limite. Total: {total_pages}.")
            if ep > total_pages:
                ep = int(total_pages)

            selected_pages = int(ep - sp + 1)

            eng = (engine or "auto").strip().lower()
            if eng not in ("auto", "pdf2docx", "text", "ocr"):
                raise HTTPException(400, "engine inválido. Use: auto, pdf2docx, text, ocr.")

            if eng == "auto":
                eng = "text" if selected_pages > 120 else "pdf2docx"

            if eng == "ocr":
                ocr = True

            def docx_has_meaningful_text(path: Path) -> bool:
                try:
                    from docx import Document
                except Exception:
                    return False

                try:
                    doc = Document(str(path))
                except Exception:
                    return False

                text_parts: list[str] = []

                for p in doc.paragraphs:
                    if p.text:
                        text_parts.append(p.text)

                for table in doc.tables:
                    for row in table.rows:
                        for cell in row.cells:
                            if cell.text:
                                text_parts.append(cell.text)

                combined = "\n".join(text_parts).strip()
                return len(combined) > 0

            def build_docx_from_pdf_text(pdf_path: Path, docx_path: Path) -> None:
                import fitz
                from docx import Document

                pdf = fitz.open(str(pdf_path))
                doc = Document()
                total = max(1, selected_pages)

                for idx, page_i in enumerate(range(sp - 1, ep)):
                    page = pdf[page_i]
                    words = page.get_text("words") or []
                    lines: dict[tuple[int, int], dict] = {}
                    for w in words:
                        x0, y0, x1, y1, text, block_no, line_no, word_no = w
                        text = (text or "").strip()
                        if not text:
                            continue
                        key = (int(block_no), int(line_no))
                        item = lines.get(key)
                        if not item:
                            item = {"y0": float(y0), "x0": float(x0), "parts": []}
                            lines[key] = item
                        else:
                            if float(y0) < item["y0"]:
                                item["y0"] = float(y0)
                            if float(x0) < item["x0"]:
                                item["x0"] = float(x0)
                        item["parts"].append((float(x0), text))

                    ordered = sorted(
                        lines.values(),
                        key=lambda it: (it["y0"], it["x0"]),
                    )

                    rendered_lines: list[str] = []
                    for it in ordered:
                        parts = sorted(it["parts"], key=lambda p: p[0])
                        line_text = " ".join(t for _, t in parts).strip()
                        if line_text:
                            rendered_lines.append(line_text)

                    normalized_lines: list[str] = []
                    for line_text in rendered_lines:
                        if (
                            normalized_lines
                            and normalized_lines[-1].endswith("-")
                            and line_text[:1].islower()
                        ):
                            normalized_lines[-1] = normalized_lines[-1][:-1] + line_text
                        else:
                            normalized_lines.append(line_text)

                    for line_text in normalized_lines:
                        if line_text:
                            doc.add_paragraph(line_text)
                    if page_i < ep - 1:
                        doc.add_page_break()

                    progress_cb(35 + int(((idx + 1) / total) * 60))

                pdf.close()
                doc.save(str(docx_path))

            def build_docx_from_pdf_ocr(pdf_path: Path, docx_path: Path) -> None:
                try:
                    import pytesseract
                except Exception as exc:
                    logger.exception("pytesseract unavailable for OCR")
                    raise HTTPException(500, "OCR não está disponível no servidor (pytesseract).")

                try:
                    import fitz
                except Exception as exc:
                    logger.exception("PyMuPDF unavailable for OCR")
                    raise HTTPException(500, "Falha ao carregar PyMuPDF para OCR.")

                try:
                    from PIL import Image
                except Exception as exc:
                    logger.exception("Pillow unavailable for OCR")
                    raise HTTPException(500, "Falha ao carregar Pillow para OCR.")

                from docx import Document

                pdf = fitz.open(str(pdf_path))
                doc = Document()
                total = max(1, selected_pages)
                scale = max(1.0, ocr_dpi / 72)
                matrix = fitz.Matrix(scale, scale)

                for idx, page_i in enumerate(range(sp - 1, ep)):
                    page = pdf[page_i]
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    if pix.n == 1:
                        mode = "L"
                    elif pix.n == 3:
                        mode = "RGB"
                    elif pix.n == 4:
                        mode = "RGBA"
                    else:
                        mode = "RGB"

                    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    text = (pytesseract.image_to_string(img, lang=ocr_lang) or "").strip()
                    if text:
                        for line in text.splitlines():
                            line = line.strip()
                            if line:
                                doc.add_paragraph(line)
                    if page_i < ep - 1:
                        doc.add_page_break()

                    progress_cb(35 + int(((idx + 1) / total) * 60))

                pdf.close()
                doc.save(str(docx_path))

            pdf2docx_error: Exception | None = None
            if eng == "pdf2docx":
                update_job(job_id, message="Convertendo (pdf2docx)…")

                def tick_progress() -> None:
                    p = 10
                    while not progress_stop.is_set():
                        p = min(34, p + 1)
                        update_job(job_id, progress=p)
                        progress_stop.wait(2.0)

                threading.Thread(target=tick_progress, daemon=True).start()

                try:
                    from pdf2docx import Converter as PdfToDocxConverter

                    progress_cb(10)
                    cv = PdfToDocxConverter(str(input_path))
                    cv.convert(str(out_path), start=sp - 1, end=ep)
                    cv.close()
                    progress_cb(35)
                except Exception as err:
                    pdf2docx_error = err
                    cleanup_files(out_path)
                finally:
                    progress_stop.set()
            else:
                progress_cb(35)

            if out_path.exists() and not docx_has_meaningful_text(out_path):
                cleanup_files(out_path)

            if (not out_path.exists()) or (not docx_has_meaningful_text(out_path)):
                try:
                    update_job(job_id, message="Extraindo texto…")
                    build_docx_from_pdf_text(input_path, out_path)
                except Exception:
                    cleanup_files(out_path)

            if out_path.exists() and not docx_has_meaningful_text(out_path) and ocr:
                cleanup_files(out_path)
                update_job(job_id, message="Executando OCR…")
                build_docx_from_pdf_ocr(input_path, out_path)

            if out_path.exists() and not docx_has_meaningful_text(out_path):
                cleanup_files(out_path)
                if pdf2docx_error:
                    raise HTTPException(
                        422,
                        "PDF parece ser escaneado ou não possui texto extraível; use o parâmetro ocr=true para tentar OCR.",
                    )
                raise HTTPException(
                    422,
                    "PDF não possui texto extraível; use o parâmetro ocr=true para tentar OCR.",
                )

            if not out_path.exists():
                for f in input_path.parent.iterdir():
                    if (
                        f.stem.startswith(input_path.stem.split("_")[0])
                        and f.suffix == ".docx"
                    ):
                        out_path = f
                        break
                else:
                    raise HTTPException(500, "DOCX output not found after conversion.")

            update_job(job_id, message="Finalizando…")
            complete_job(
                job_id,
                output_path=out_path,
                download_name=download_name,
                media_type=media_type,
            )
        except HTTPException as exc:
            progress_stop.set()
            fail_job(job_id, message=str(exc.detail))
            cleanup_files(input_path, out_path)
        except Exception as exc:
            progress_stop.set()
            logger.exception("pdf-to-word-job failed: %s", exc)
            fail_job(job_id, message="Falha na conversão do arquivo.")
            cleanup_files(input_path, out_path)

    threading.Thread(target=worker, daemon=True).start()

    return {
        "job_id": job_id,
        "status_url": f"/jobs/{job_id}",
        "download_url": f"/jobs/{job_id}/download",
    }


# ── PDF Merge ──────────────────────────────────────────────────────────────


@router.post("/merge-pdfs")
def merge_pdfs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    if len(files) < 2:
        raise HTTPException(400, detail="Envie pelo menos 2 arquivos PDF para juntar.")

    input_paths: List[Path] = []
    output_path = unique_path(".pdf")
    try:
        for f in files:
            validate_ext(f.filename, {".pdf"})
            p = unique_path(".pdf")
            save_upload_file_sync(f, p)
            validate_signature(p, ".pdf")
            input_paths.append(p)

        import fitz

        out_doc = fitz.open()
        for p in input_paths:
            doc = fitz.open(str(p))
            out_doc.insert_pdf(doc)
            doc.close()

        out_doc.save(str(output_path))
        out_doc.close()

        background_tasks.add_task(cleanup_files, *input_paths, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename="merged.pdf",
        )
    except HTTPException:
        cleanup_files(*input_paths, output_path)
        raise
    except Exception as exc:
        cleanup_files(*input_paths, output_path)
        logger.exception("merge-pdfs failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


# ── PDF → Image ───────────────────────────────────────────────────────────


@router.post("/pdf-to-image")
def convert_pdf_to_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    fmt: str = Query("png", description="Output image format: png or jpg"),
    dpi: int = Query(150, description="Image resolution in DPI"),
):
    validate_ext(file.filename, {".pdf"})
    if fmt.lower() not in ("png", "jpg", "jpeg"):
        raise HTTPException(400, "Format must be 'png' or 'jpg'.")

    output_ext = ".png" if fmt.lower() == "png" else ".jpg"
    input_path = unique_path(".pdf")

    try:
        save_upload_file_sync(file, input_path)
        validate_signature(input_path, ".pdf")

        import fitz  # PyMuPDF
        doc = fitz.open(input_path)
        output_paths: List[Path] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            matrix = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=matrix)
            page_path = unique_path(f"_page{page_num + 1}{output_ext}")
            pix.save(str(page_path))
            output_paths.append(page_path)

        doc.close()

        if len(output_paths) == 1:
            p = output_paths[0]
            background_tasks.add_task(cleanup_files, input_path, p)
            return FileResponse(
                path=str(p),
                media_type=f"image/{fmt.lower().replace('jpg', 'jpeg')}",
                filename=f"{Path(file.filename).stem}{output_ext}",
            )

        zip_path = unique_path(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in output_paths:
                zf.write(p, p.name)

        all_paths = [input_path, zip_path] + output_paths
        background_tasks.add_task(cleanup_files, *all_paths)

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"{Path(file.filename).stem}_pages.zip",
        )

    except HTTPException:
        cleanup_files(input_path)
        raise
    except Exception as exc:
        cleanup_files(input_path)
        logger.exception("pdf-to-image failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


# ── Image → PDF ───────────────────────────────────────────────────────────

from PIL import Image


@router.post("/image-to-pdf")
def convert_image_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    validate_ext(file.filename, {".jpg", ".jpeg", ".png"})
    ext = Path(file.filename).suffix.lower()
    input_path = unique_path(ext)
    output_path = input_path.with_suffix(".pdf")
    try:
        save_upload_file_sync(file, input_path)
        validate_signature(input_path, ext)

        image = Image.open(input_path)
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        image.save(output_path, "PDF", resolution=100.0)

        background_tasks.add_task(cleanup_files, input_path, output_path)
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=f"{Path(file.filename).stem}.pdf",
        )
    except HTTPException:
        cleanup_files(input_path, output_path)
        raise
    except Exception as exc:
        cleanup_files(input_path, output_path)
        logger.exception("image-to-pdf failed: %s", exc)
        raise HTTPException(500, detail="Falha na conversão do arquivo.")


# ── PDF → Compressed PDF ─────────────────────────────────────────────────


def _compress_pdf_to_target(
    input_path: Path,
    output_path: Path,
    target_bytes: int,
    progress_cb=None,
) -> int:
    """Reduce a PDF's size until it fits within ``target_bytes``.

    Uses smart progressive strategies with live progress callbacks:
      1. Lossless re-save (garbage collection, object streams, font subsetting);
      2. Adaptive image recompression based on target ratio to avoid slow multi-pass loops.
    """
    import fitz  # PyMuPDF

    def cb(pct: int, msg: str = "") -> None:
        if progress_cb:
            try:
                progress_cb(pct, msg)
            except Exception:
                pass

    def save_doc(doc, path: Path) -> None:
        tmp = path.with_name(path.name + ".tmp")
        try:
            doc.save(str(tmp), garbage=4, deflate=1, use_objstms=True)
            os.replace(str(tmp), str(path))
        finally:
            if tmp.exists():
                try:
                    tmp.unlink()
                except OSError:
                    pass

    def rewrite(doc, quality: int, dpi_threshold, dpi_target: int) -> None:
        try:
            doc.subset_fonts()
        except Exception:
            pass
        if dpi_threshold:
            doc.rewrite_images(
                dpi_threshold=dpi_threshold,
                dpi_target=dpi_target,
                quality=quality,
            )
        else:
            doc.rewrite_images(quality=quality)

    def fits() -> bool:
        return output_path.exists() and output_path.stat().st_size <= target_bytes

    original_size = input_path.stat().st_size
    ratio = target_bytes / max(1, original_size)

    # Strategy 1: lossless re-save + font subsetting
    cb(20, "Otimizando objetos e fontes do PDF...")
    doc = fitz.open(str(input_path))
    try:
        try:
            doc.subset_fonts()
        except Exception:
            pass
        save_doc(doc, output_path)
    finally:
        doc.close()

    if fits():
        cb(100, "Concluído!")
        return output_path.stat().st_size

    # Strategy 2: targeted image recompression (at most 2 passes instead of 9)
    if hasattr(fitz.Document, "rewrite_images"):
        if ratio >= 0.70:
            candidates = [
                (70, 200, 140, "Otimizando imagens e gráficos (qualidade alta)...", 50),
                (50, 150, 100, "Comprimindo imagens para atingir o tamanho...", 80),
            ]
        elif ratio >= 0.35:
            candidates = [
                (55, 150, 96, "Otimizando imagens e ajustando resolução...", 50),
                (35, 110, 72, "Aplicando compressão profunda...", 80),
            ]
        else:
            candidates = [
                (35, 110, 72, "Reduzindo resolução para tamanho mínimo...", 50),
                (20, 96, 72, "Aplicando compressão máxima...", 80),
            ]

        for quality, dpi_threshold, dpi_target, step_msg, step_pct in candidates:
            cb(step_pct, step_msg)
            doc = fitz.open(str(input_path))
            try:
                rewrite(doc, quality, dpi_threshold, dpi_target)
                save_doc(doc, output_path)
            except Exception:
                continue
            finally:
                doc.close()
            if fits():
                cb(100, "Concluído!")
                return output_path.stat().st_size

    # Guarantee a valid output even if compression steps failed.
    if not output_path.exists():
        shutil.copy(str(input_path), str(output_path))
    cb(100, "Concluído!")
    return output_path.stat().st_size


@router.post("/compress-pdf-job")
def compress_pdf_job(
    file: UploadFile = File(...),
    target: float = Query(10, description="Tamanho máximo desejado em MB (ex.: 5, 8, 10)"),
):
    """Compress a PDF asynchronously with live progress reporting."""
    validate_ext(file.filename, {".pdf"})

    try:
        target_mb = float(target)
    except (TypeError, ValueError):
        raise HTTPException(400, "Parâmetro 'target' inválido. Use um número em MB.")

    target_mb = max(0.1, min(target_mb, 100))
    target_bytes = int(target_mb * 1024 * 1024)

    input_path = unique_path(".pdf")
    output_path = unique_path(".pdf")

    save_upload_file_sync(file, input_path)
    validate_signature(input_path, ".pdf")

    job_id = create_job()
    attach_job_files(job_id, input_path=input_path)
    update_job(job_id, progress=5, status="running", message="Arquivo recebido. Iniciando análise...")

    download_name = f"{Path(file.filename).stem}-comprimido.pdf"
    media_type = "application/pdf"

    def worker() -> None:
        try:
            def progress_cb(pct: int, msg: str = ""):
                update_job(job_id, progress=pct, message=msg)

            original_size = input_path.stat().st_size
            _compress_pdf_to_target(input_path, output_path, target_bytes, progress_cb=progress_cb)
            compressed_size = output_path.stat().st_size if output_path.exists() else original_size

            final_path = output_path
            if not output_path.exists() or compressed_size >= original_size:
                final_path = input_path

            complete_job(
                job_id,
                output_path=final_path,
                download_name=download_name,
                media_type=media_type,
            )
            update_job(job_id, progress=100, status="done", message="Concluído com sucesso!")
        except Exception as exc:
            logger.exception("compress-pdf-job failed: %s", exc)
            cleanup_files(output_path)
            fail_job(job_id, message="Falha durante a compressão do arquivo.")

    threading.Thread(target=worker, daemon=True).start()

    return {
        "job_id": job_id,
        "status_url": f"/jobs/{job_id}",
        "download_url": f"/jobs/{job_id}/download",
    }


@router.post("/compress-pdf")
def compress_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    target: float = Query(10, description="Tamanho máximo desejado em MB (ex.: 5, 8, 10)"),
):
    """Synchronous compress route for API / cURL usage."""
    validate_ext(file.filename, {".pdf"})

    try:
        target_mb = float(target)
    except (TypeError, ValueError):
        raise HTTPException(400, "Parâmetro 'target' inválido. Use um número em MB.")

    target_mb = max(0.1, min(target_mb, 100))
    target_bytes = int(target_mb * 1024 * 1024)

    input_path = unique_path(".pdf")
    output_path = unique_path(".pdf")
    try:
        save_upload_file_sync(file, input_path)
        validate_signature(input_path, ".pdf")
        original_size = input_path.stat().st_size

        _compress_pdf_to_target(input_path, output_path, target_bytes)
        compressed_size = output_path.stat().st_size if output_path.exists() else original_size

        background_tasks.add_task(cleanup_files, input_path, output_path)

        if not output_path.exists() or compressed_size >= original_size:
            return FileResponse(
                path=str(input_path),
                media_type="application/pdf",
                filename=f"{Path(file.filename).stem}.pdf",
                headers={
                    "X-Original-Size": str(original_size),
                    "X-Compressed-Size": str(original_size),
                },
            )

        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=f"{Path(file.filename).stem}-comprimido.pdf",
            headers={
                "X-Original-Size": str(original_size),
                "X-Compressed-Size": str(compressed_size),
            },
        )
    except HTTPException:
        cleanup_files(input_path, output_path)
        raise
    except Exception as exc:
        cleanup_files(input_path, output_path)
        logger.exception("compress-pdf failed: %s", exc)
        raise HTTPException(500, detail="Falha na compressão do arquivo.")
