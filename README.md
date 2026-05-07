# File Converter API

API em FastAPI para conversão de arquivos (Office, PDF, imagens e e-books), com interface web simples em `/ui`.

## Como rodar (Docker)

```bash
docker build -t converter .
docker run --rm -p 3004:3004 converter
```

- UI: `http://localhost:3004/ui`
- OpenAPI/Swagger: `http://localhost:3004/docs`
- Health check: `GET http://localhost:3004/`

## Endpoints

Todos os endpoints recebem `multipart/form-data` com o campo `file`.

### Office

- `POST /convert/office-to-pdf` → converte DOC/DOCX/ODT/RTF/XLS/XLSX/PPT/PPTX/HTML/EPUB para PDF
- `POST /convert/word-to-pdf` → atalho para `office-to-pdf`
- `POST /convert/word-to-html` → Word para HTML
- `POST /convert/excel-to-csv` → Excel para CSV
- `POST /convert/powerpoint-to-pdf` → PowerPoint para PDF

### PDF

- `POST /convert/pdf-to-word` → PDF para DOCX
  - Query params:
    - `ocr` (bool, padrão `false`): ativa OCR quando o PDF não possui texto extraível (PDF escaneado)
    - `ocr_lang` (string, padrão `por`): idioma do OCR (ex.: `por`, `eng`, `por+eng`)
    - `ocr_dpi` (int, padrão `200`): DPI usado no OCR
- `POST /convert/pdf-to-image` → PDF para imagem (1 página retorna a imagem; múltiplas páginas retorna ZIP)
  - Query params:
    - `fmt` (padrão `png`): `png` ou `jpg`
    - `dpi` (padrão `150`)
- `POST /convert/image-to-pdf` → JPG/JPEG/PNG para PDF

### Imagens

- `POST /convert/image` → conversão de formato de imagem
  - Query params:
    - `to` (padrão `png`): `png`, `jpg`, `webp`, `bmp`, `tiff`

### E-books & Web

- `POST /convert/epub-to-pdf` → EPUB para PDF
- `POST /convert/html-to-pdf` → HTML para PDF

## Exemplos (cURL)

PDF → DOCX:

```bash
curl -F "file=@arquivo.pdf" http://localhost:3004/convert/pdf-to-word --output saida.docx
```

PDF escaneado → DOCX (OCR):

```bash
curl -F "file=@arquivo.pdf" "http://localhost:3004/convert/pdf-to-word?ocr=true&ocr_lang=por&ocr_dpi=200" --output saida.docx
```

Word → PDF:

```bash
curl -F "file=@arquivo.docx" http://localhost:3004/convert/word-to-pdf --output saida.pdf
```

## Dependências de conversão

- Conversões Office/HTML/EPUB dependem de LibreOffice (incluído no Dockerfile).
- OCR depende do Tesseract + `pytesseract` (incluídos no Dockerfile e requirements).

