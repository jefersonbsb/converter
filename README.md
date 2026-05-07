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

## UI (Frontend)

A interface web é um HTML simples servido pela própria API em `/ui`. O JavaScript da UI fica em `/src/js/script.js` (servido como arquivo estático em `/src`).

### Categorias na UI

- PDF: conversão padrão (comportamento simples)
- PDF (Grande): fluxo recomendado para PDFs com muitas páginas (suporta modo de conversão e intervalo de páginas)

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
- `POST /convert/pdf-to-word-job` → PDF para DOCX usando “job” (progresso + download separado)
  - Retorna JSON com:
    - `job_id`
    - `status_url` (ex.: `/jobs/<job_id>`)
    - `download_url` (ex.: `/jobs/<job_id>/download`)
  - Query params:
    - `engine` (padrão `auto`): `auto`, `pdf2docx`, `text`, `ocr`
      - `pdf2docx`: mais fiel ao layout (mais pesado)
      - `text`: mais editável e leve (menos fiel ao layout)
      - `ocr`: para PDF escaneado (mais lento)
      - `auto`: escolhe automaticamente (tende a usar `text` em PDFs grandes)
    - `start_page` (padrão `1`): página inicial (1-based)
    - `end_page` (opcional): página final (1-based, inclusiva)
    - `ocr` / `ocr_lang` / `ocr_dpi`: mesmos parâmetros do endpoint simples
- `POST /convert/pdf-to-image` → PDF para imagem (1 página retorna a imagem; múltiplas páginas retorna ZIP)
  - Query params:
    - `fmt` (padrão `png`): `png` ou `jpg`
    - `dpi` (padrão `150`)
- `POST /convert/image-to-pdf` → JPG/JPEG/PNG para PDF

### Jobs

- `GET /jobs/{job_id}` → status e progresso
  - Retorna: `status` (`running`, `done`, `error`), `progress` (0–100), `message`
- `GET /jobs/{job_id}/download` → baixa o arquivo quando o job terminar
  - Se ainda estiver processando retorna `409`
  - Após o download, os arquivos temporários do job são excluídos automaticamente

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

PDF grande → DOCX com progresso (modo editável / por páginas):

```bash
curl -F "file=@arquivo.pdf" "http://localhost:3004/convert/pdf-to-word-job?engine=text&start_page=1&end_page=100"
```

Consultar status:

```bash
curl http://localhost:3004/jobs/<job_id>
```

Baixar resultado:

```bash
curl -L http://localhost:3004/jobs/<job_id>/download --output saida.docx
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

## Arquivos temporários

- Os arquivos enviados e gerados são salvos em diretório temporário do sistema.
- Nas rotas padrão, o cleanup ocorre após a resposta terminar.
- Nos “jobs”, o cleanup ocorre após o download em `/jobs/{job_id}/download`, para evitar encher o disco da VPS.

