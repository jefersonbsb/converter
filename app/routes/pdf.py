import zipfile
import traceback
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse

from app.utils import unique_path, cleanup_files, validate_ext

router = APIRouter(prefix="/convert", tags=["PDF"])


# ── PDF → Word ────────────────────────────────────────────────────────────

@router.post("/pdf-to-word")
async def convert_pdf_to_word(
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
        content = await file.read()
        input_path.write_bytes(content)

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
                page_text = (page.get_text("text") or "").strip()
                if page_text:
                    for line in page_text.splitlines():
                        line = line.strip()
                        if line:
                            doc.add_paragraph(line)
                if i < len(pdf) - 1:
                    doc.add_page_break()

            pdf.close()
            doc.save(str(docx_path))

        def build_docx_from_pdf_ocr(pdf_path: Path, docx_path: Path) -> None:
            try:
                import pytesseract
            except Exception as exc:
                raise HTTPException(
                    500,
                    f"OCR não está disponível no servidor (pytesseract). Erro: {exc}",
                )

            try:
                import fitz
            except Exception as exc:
                raise HTTPException(500, f"Falha ao carregar PyMuPDF para OCR: {exc}")

            try:
                from PIL import Image
            except Exception as exc:
                raise HTTPException(500, f"Falha ao carregar Pillow para OCR: {exc}")

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
        error_detail = f"Conversion failed: {exc}\n{traceback.format_exc()}"
        print(f"[pdf-to-word] ERROR: {error_detail}")
        raise HTTPException(500, detail=f"Conversion failed: {exc}")


# ── PDF → Image ───────────────────────────────────────────────────────────


@router.post("/pdf-to-image")
async def convert_pdf_to_image(
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
        content = await file.read()
        input_path.write_bytes(content)

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
        raise HTTPException(500, detail=f"Conversion failed: {exc}")


# ── Image → PDF ───────────────────────────────────────────────────────────

from PIL import Image


@router.post("/image-to-pdf")
async def convert_image_to_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    validate_ext(file.filename, {".jpg", ".jpeg", ".png"})
    ext = Path(file.filename).suffix.lower()
    input_path = unique_path(ext)
    output_path = input_path.with_suffix(".pdf")
    try:
        content = await file.read()
        input_path.write_bytes(content)

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
        raise HTTPException(500, detail=f"Conversion failed: {exc}")
