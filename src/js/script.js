// ── Conversion definitions ──────────────────────────────────────
const conversions = {
    // Office category
    'office-to-pdf': {
        category: 'office',
        label: 'Office → PDF',
        accept: '.doc,.docx,.odt,.rtf,.xls,.xlsx,.ppt,.pptx,.html,.htm,.epub',
        hint: 'DOC, DOCX, ODT, RTF, XLS, XLSX, PPT, PPTX, HTML, EPUB',
        endpoint: '/convert/office-to-pdf',
        extra: false,
    },
    'word-to-pdf': {
        category: 'office',
        label: 'Word → PDF',
        accept: '.doc,.docx,.odt,.rtf',
        hint: 'DOC, DOCX, ODT, RTF',
        endpoint: '/convert/word-to-pdf',
        extra: false,
    },
    'word-to-html': {
        category: 'office',
        label: 'Word → HTML',
        accept: '.doc,.docx,.odt,.rtf',
        hint: 'DOC, DOCX, ODT, RTF',
        endpoint: '/convert/word-to-html',
        extra: false,
    },
    'excel-to-csv': {
        category: 'office',
        label: 'Excel → CSV',
        accept: '.xls,.xlsx',
        hint: 'XLS, XLSX',
        endpoint: '/convert/excel-to-csv',
        extra: false,
    },
    'powerpoint-to-pdf': {
        category: 'office',
        label: 'PowerPoint → PDF',
        accept: '.ppt,.pptx',
        hint: 'PPT, PPTX',
        endpoint: '/convert/powerpoint-to-pdf',
        extra: false,
    },
    // PDF category
    'pdf-to-word': {
        category: 'pdf',
        label: 'PDF → Word (DOCX)',
        accept: '.pdf',
        hint: 'PDF',
        endpoint: '/convert/pdf-to-word',
        extra: 'pdf-to-word',
    },
    'pdf-large-to-word': {
        category: 'pdf-large',
        label: 'PDF Grande → Word (DOCX)',
        accept: '.pdf',
        hint: 'PDF (recomendado para muitas páginas)',
        endpoint: '/convert/pdf-to-word',
        extra: 'pdf-to-word-large',
    },
    'pdf-to-image': {
        category: 'pdf',
        label: 'PDF → Imagem',
        accept: '.pdf',
        hint: 'PDF (cada página vira PNG/JPG)',
        endpoint: '/convert/pdf-to-image',
        extra: 'pdf-to-image',
    },
    'merge-pdfs': {
        category: 'pdf-tools',
        label: 'Juntar PDFs (Merge)',
        accept: '.pdf',
        hint: 'PDF (selecione 2+ arquivos)',
        endpoint: '/convert/merge-pdfs',
        extra: 'pdf-merge',
        multiple: true,
    },
    'image-to-pdf': {
        category: 'pdf',
        label: 'Imagem → PDF',
        accept: '.jpg,.jpeg,.png',
        hint: 'JPG, JPEG, PNG',
        endpoint: '/convert/image-to-pdf',
        extra: false,
    },
    // Image category
    'image-convert': {
        category: 'image',
        label: 'Converter formato (JPG ⇄ PNG ⇄ WebP ⇄ BMP ⇄ TIFF)',
        accept: '.jpg,.jpeg,.png,.webp,.bmp,.tiff,.tif',
        hint: 'JPG, PNG, WebP, BMP, TIFF',
        endpoint: '/convert/image',
        extra: 'image-convert',
    },
    // E-books & Web category
    'epub-to-pdf': {
        category: 'ebook',
        label: 'EPUB → PDF',
        accept: '.epub',
        hint: 'EPUB',
        endpoint: '/convert/epub-to-pdf',
        extra: false,
    },
    'html-to-pdf': {
        category: 'ebook',
        label: 'HTML → PDF',
        accept: '.html,.htm',
        hint: 'HTML, HTM',
        endpoint: '/convert/html-to-pdf',
        extra: false,
    },
};

// ── DOM refs ────────────────────────────────────────────────────
const form = document.getElementById('convertForm');
const categorySelect = document.getElementById('categorySelect');
const conversionType = document.getElementById('conversionType');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const fileExtHint = document.getElementById('fileExtHint');
const fileLabel = document.getElementById('fileLabel');
const dropZone = document.getElementById('dropZone');
const submitBtn = document.getElementById('submitBtn');
const btnText = document.getElementById('btnText');
const spinner = document.getElementById('spinner');
const statusMessage = document.getElementById('statusMessage');
const extraOptions = document.getElementById('extraOptions');
const imageFormatSelect = document.getElementById('imageFormatSelect');
const dpiInput = document.getElementById('dpiInput');
const ocrToggle = document.getElementById('ocrToggle');
const ocrCheckbox = document.getElementById('ocrCheckbox');
const ocrLangWrap = document.getElementById('ocrLangWrap');
const ocrLangInput = document.getElementById('ocrLangInput');
const pdfEngineWrap = document.getElementById('pdfEngineWrap');
const pdfEngineSelect = document.getElementById('pdfEngineSelect');
const pdfRangeWrap = document.getElementById('pdfRangeWrap');
const startPageInput = document.getElementById('startPageInput');
const endPageInput = document.getElementById('endPageInput');
const progressWrap = document.getElementById('progressWrap');
const progressText = document.getElementById('progressText');
const progressMsg = document.getElementById('progressMsg');
const progressBar = document.getElementById('progressBar');

// ── Populate conversion types based on category ────────────────
const categoryMap = {};
for (const [key, def] of Object.entries(conversions)) {
    if (!categoryMap[def.category]) categoryMap[def.category] = [];
    categoryMap[def.category].push({ key, ...def });
}

function updateConversionTypes() {
    const cat = categorySelect.value;
    const items = categoryMap[cat] || [];
    conversionType.innerHTML = '';
    items.forEach(item => {
        const opt = document.createElement('option');
        opt.value = item.key;
        opt.textContent = item.label;
        conversionType.appendChild(opt);
    });
    updateFileAccept();
    updateExtraOptions();
}

function updateFileAccept() {
    const key = conversionType.value;
    const def = conversions[key];
    if (def) {
        fileInput.accept = def.accept;
        fileInput.multiple = Boolean(def.multiple);
        fileExtHint.textContent = `Formatos aceitos: ${def.hint}`;
    }
    // Reset file display
    fileInput.value = '';
    fileName.classList.add('hidden');
    fileLabel.classList.remove('hidden');
}

function updateExtraOptions() {
    const key = conversionType.value;
    const def = conversions[key];
    if (def && def.extra === 'pdf-to-image') {
        extraOptions.classList.remove('hidden');
        imageFormatSelect.parentElement.classList.remove('hidden');
        dpiInput.parentElement.classList.remove('hidden');
        ocrToggle.classList.add('hidden');
        ocrLangWrap.classList.add('hidden');
        pdfEngineWrap.classList.add('hidden');
        pdfRangeWrap.classList.add('hidden');
        dpiInput.value = dpiInput.value || '150';
    } else if (def && def.extra === 'image-convert') {
        extraOptions.classList.remove('hidden');
        imageFormatSelect.parentElement.classList.remove('hidden');
        dpiInput.parentElement.classList.add('hidden');
        ocrToggle.classList.add('hidden');
        ocrLangWrap.classList.add('hidden');
        pdfEngineWrap.classList.add('hidden');
        pdfRangeWrap.classList.add('hidden');
    } else if (def && def.extra === 'pdf-to-word') {
        extraOptions.classList.remove('hidden');
        imageFormatSelect.parentElement.classList.add('hidden');
        ocrToggle.classList.remove('hidden');
        ocrLangWrap.classList.toggle('hidden', !ocrCheckbox.checked);
        dpiInput.parentElement.classList.toggle('hidden', !ocrCheckbox.checked);
        pdfEngineWrap.classList.add('hidden');
        pdfRangeWrap.classList.add('hidden');
        if (ocrCheckbox.checked) {
            dpiInput.value = dpiInput.value || '200';
        }
    } else if (def && def.extra === 'pdf-to-word-large') {
        extraOptions.classList.remove('hidden');
        imageFormatSelect.parentElement.classList.add('hidden');
        ocrToggle.classList.remove('hidden');
        pdfEngineWrap.classList.remove('hidden');
        pdfRangeWrap.classList.remove('hidden');

        const engine = (pdfEngineSelect.value || 'text').toLowerCase();
        const ocrEnabled = ocrCheckbox.checked || engine === 'ocr';
        ocrLangWrap.classList.toggle('hidden', !ocrEnabled);
        dpiInput.parentElement.classList.toggle('hidden', !ocrEnabled);
        if (ocrEnabled) {
            dpiInput.value = dpiInput.value || '200';
        }
    } else if (def && def.extra === 'pdf-merge') {
        extraOptions.classList.add('hidden');
    } else {
        extraOptions.classList.add('hidden');
    }
}

categorySelect.addEventListener('change', updateConversionTypes);
conversionType.addEventListener('change', () => {
    updateFileAccept();
    updateExtraOptions();
});

// Initialize
updateConversionTypes();
ocrCheckbox.addEventListener('change', updateExtraOptions);
pdfEngineSelect.addEventListener('change', updateExtraOptions);

// ── File name display ───────────────────────────────────────────
fileInput.addEventListener('change', () => {
    const files = Array.from(fileInput.files || []);
    if (files.length === 1) {
        fileName.textContent = files[0].name;
        fileName.classList.remove('hidden');
        fileLabel.classList.add('hidden');
    } else if (files.length > 1) {
        fileName.textContent = `${files.length} arquivos selecionados`;
        fileName.classList.remove('hidden');
        fileLabel.classList.add('hidden');
    } else {
        fileName.classList.add('hidden');
        fileLabel.classList.remove('hidden');
    }
});

// ── Drag & drop visual hint ─────────────────────────────────────
['dragenter', 'dragover'].forEach(evt => {
    dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropZone.classList.add('border-indigo-500', 'bg-indigo-50/50');
    });
});
['dragleave', 'drop'].forEach(evt => {
    dropZone.addEventListener(evt, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-indigo-500', 'bg-indigo-50/50');
    });
});
dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length) {
        if (fileInput.multiple) {
            fileInput.files = files;
        } else {
            const dt = new DataTransfer();
            dt.items.add(files[0]);
            fileInput.files = dt.files;
        }
        fileName.textContent = (fileInput.files.length === 1)
            ? fileInput.files[0].name
            : `${fileInput.files.length} arquivos selecionados`;
        fileName.classList.remove('hidden');
        fileLabel.classList.add('hidden');
    }
});

// ── Submit ──────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const selectedFiles = Array.from(fileInput.files || []);
    if (selectedFiles.length === 0) {
        showStatus('Selecione um arquivo antes de converter.', 'red');
        return;
    }

    const key = conversionType.value;
    const def = conversions[key];
    if (!def) return;

    // Build URL with query params if needed
    let url = def.endpoint;
    const params = new URLSearchParams();

    if (def.extra === 'pdf-to-image') {
        params.set('fmt', imageFormatSelect.value);
        params.set('dpi', dpiInput.value || '150');
    } else if (def.extra === 'image-convert') {
        params.set('to', imageFormatSelect.value);
    } else if (def.extra === 'pdf-to-word') {
        if (ocrCheckbox.checked) {
            params.set('ocr', 'true');
            params.set('ocr_lang', ocrLangInput.value || 'por');
            params.set('ocr_dpi', dpiInput.value || '200');
        }
    } else if (def.extra === 'pdf-to-word-large') {
        const engine = (pdfEngineSelect.value || 'auto').toLowerCase();
        params.set('engine', engine);
        params.set('start_page', startPageInput.value || '1');
        if (endPageInput.value) {
            params.set('end_page', endPageInput.value);
        }
        if (ocrCheckbox.checked || engine === 'ocr') {
            params.set('ocr', 'true');
            params.set('ocr_lang', ocrLangInput.value || 'por');
            params.set('ocr_dpi', dpiInput.value || '200');
        }
    }

    const qs = params.toString();
    if (qs) url += '?' + qs;

    // UI loading state
    setLoading(true);
    hideStatus();
    setProgressVisible(false);

    const defaultApiBase = 'http://127.0.0.1:3004';
    const apiFromQuery = new URLSearchParams(location.search).get('api');
    const apiBase = apiFromQuery
        ? apiFromQuery.replace(/\/+$/, '')
        : (location.protocol === 'http:' || location.protocol === 'https:')
            ? ''
            : defaultApiBase;

    const formData = new FormData();
    if (def.extra === 'pdf-merge') {
        for (const f of selectedFiles) {
            formData.append('files', f);
        }
    } else {
        formData.append('file', selectedFiles[0]);
    }

    try {
        if (def.extra === 'pdf-to-word' || def.extra === 'pdf-to-word-large') {
            setProgressVisible(true);
            setProgress(0);

            const jobUrl = apiBase + '/convert/pdf-to-word-job' + (qs ? ('?' + qs) : '');
            const jobRes = await fetch(jobUrl, { method: 'POST', body: formData });

            if (!jobRes.ok) {
                let msg = `Erro ${jobRes.status}`;
                try {
                    const err = await jobRes.json();
                    msg = err.detail || msg;
                } catch { }
                throw new Error(msg);
            }

            const job = await jobRes.json();
            const jobId = job.job_id;
            const statusUrl = apiBase + (job.status_url || (`/jobs/${jobId}`));
            const downloadUrl = apiBase + (job.download_url || (`/jobs/${jobId}/download`));

            while (true) {
                const st = await fetch(statusUrl, { method: 'GET' });
                if (!st.ok) {
                    throw new Error(`Erro ${st.status}`);
                }
                const data = await st.json();
                setProgress(Number(data.progress || 0));
                setProgressMessage(data.message || '');
                if (data.status === 'done') break;
                if (data.status === 'error') throw new Error(data.message || 'Falha na conversão.');
                await sleep(500);
            }

            const res = await fetch(downloadUrl, { method: 'GET' });
            if (!res.ok) {
                let msg = `Erro ${res.status}`;
                try {
                    const err = await res.json();
                    msg = err.detail || msg;
                } catch { }
                throw new Error(msg);
            }

            const blob = await res.blob();
            downloadBlob(blob, selectedFiles[0].name, res.headers.get('Content-Disposition') || '');
            showStatus('✅ Conversão concluída! Download iniciado.', 'green');
            return;
        }

        const res = await fetch(apiBase + url, { method: 'POST', body: formData });

        if (!res.ok) {
            let msg = `Erro ${res.status}`;
            try {
                const err = await res.json();
                msg = err.detail || msg;
            } catch {
                try {
                    const text = await res.text();
                    if (text) msg = text.slice(0, 200);
                } catch { }
            }
            throw new Error(msg);
        }

        // Trigger automatic download
        const blob = await res.blob();
        const disposition = res.headers.get('Content-Disposition') || '';
        const filenameStarMatch = disposition.match(/filename\*\s*=\s*UTF-8''([^;\n]+)/i);
        const filenameQuotedMatch = disposition.match(/filename\s*=\s*"([^"\n]+)"/i);
        const filenameBareMatch = disposition.match(/filename\s*=\s*([^;\n]+)/i);

        let serverFilename = '';
        if (filenameStarMatch && filenameStarMatch[1]) {
            try {
                serverFilename = decodeURIComponent(filenameStarMatch[1]);
            } catch {
                serverFilename = filenameStarMatch[1];
            }
        } else if (filenameQuotedMatch && filenameQuotedMatch[1]) {
            serverFilename = filenameQuotedMatch[1];
        } else if (filenameBareMatch && filenameBareMatch[1]) {
            serverFilename = filenameBareMatch[1].trim().replace(/^"|"$/g, '');
        }

        const mimeToExt = {
            'application/pdf': 'pdf',
            'application/zip': 'zip',
            'text/csv': 'csv',
            'text/html': 'html',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'image/png': 'png',
            'image/jpeg': 'jpg',
            'image/webp': 'webp',
            'image/bmp': 'bmp',
            'image/tiff': 'tiff',
        };

        const safeBaseName = (name) =>
            (name || 'converted')
                .replace(/\.[^/.]+$/, '')
                .replace(/[\\/:*?\"<>|]/g, '_')
                .trim() || 'converted';

        const extFromMime = mimeToExt[blob.type] || (blob.type.startsWith('image/') ? blob.type.split('/')[1] : '');
        const defaultFilename = `${safeBaseName(selectedFiles[0].name)}.${extFromMime || 'file'}`;
        const filename = serverFilename || defaultFilename;

        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(a.href);

        showStatus('✅ Conversão concluída! Download iniciado.', 'green');
    } catch (err) {
        showStatus(`❌ ${err.message}`, 'red');
    } finally {
        setLoading(false);
        setProgressVisible(false);
    }
});

// ── Helpers ─────────────────────────────────────────────────────
function setLoading(loading) {
    submitBtn.disabled = loading;
    spinner.classList.toggle('hidden', !loading);
    btnText.textContent = loading ? 'Convertendo…' : 'Converter e Baixar';
}

function setProgressVisible(visible) {
    progressWrap.classList.toggle('hidden', !visible);
}

function setProgress(pct) {
    const val = Math.max(0, Math.min(100, Number(pct) || 0));
    progressText.textContent = `${val}%`;
    progressBar.style.width = `${val}%`;
}

function setProgressMessage(msg) {
    progressMsg.textContent = msg || '';
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function downloadBlob(blob, originalName, contentDisposition) {
    const disposition = contentDisposition || '';
    const filenameStarMatch = disposition.match(/filename\*\s*=\s*UTF-8''([^;\n]+)/i);
    const filenameQuotedMatch = disposition.match(/filename\s*=\s*\"([^\"\n]+)\"/i);
    const filenameBareMatch = disposition.match(/filename\s*=\s*([^;\n]+)/i);

    let serverFilename = '';
    if (filenameStarMatch && filenameStarMatch[1]) {
        try {
            serverFilename = decodeURIComponent(filenameStarMatch[1]);
        } catch {
            serverFilename = filenameStarMatch[1];
        }
    } else if (filenameQuotedMatch && filenameQuotedMatch[1]) {
        serverFilename = filenameQuotedMatch[1];
    } else if (filenameBareMatch && filenameBareMatch[1]) {
        serverFilename = filenameBareMatch[1].trim().replace(/^\"|\"$/g, '');
    }

    const mimeToExt = {
        'application/pdf': 'pdf',
        'application/zip': 'zip',
        'text/csv': 'csv',
        'text/html': 'html',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/webp': 'webp',
        'image/bmp': 'bmp',
        'image/tiff': 'tiff',
    };

    const safeBaseName = (name) =>
        (name || 'converted')
            .replace(/\.[^/.]+$/, '')
            .replace(/[\\/:*?\"<>|]/g, '_')
            .trim() || 'converted';

    const extFromMime = mimeToExt[blob.type] || (blob.type.startsWith('image/') ? blob.type.split('/')[1] : '');
    const defaultFilename = `${safeBaseName(originalName)}.${extFromMime || 'file'}`;
    const filename = serverFilename || defaultFilename;

    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
}

function showStatus(msg, type) {
    statusMessage.textContent = msg;
    statusMessage.className = `text-sm text-center rounded-lg p-3 ${type === 'red'
        ? 'bg-red-50 text-red-700 border border-red-200'
        : 'bg-green-50 text-green-700 border border-green-200'
        }`;
    statusMessage.classList.remove('hidden');
}

function hideStatus() {
    statusMessage.classList.add('hidden');
}
