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
        category: 'pdf',
        label: 'PDF Grande → Word (com páginas / OCR)',
        accept: '.pdf',
        hint: 'PDF (recomendado para muitas páginas ou escaneados)',
        endpoint: '/convert/pdf-to-word',
        extra: 'pdf-to-word-large',
    },
    'compress-pdf': {
        category: 'pdf',
        label: '🗜️ Reduzir tamanho do PDF (comprimir)',
        accept: '.pdf',
        hint: 'PDF (reduz tamanho com alvos de 1 a 10 MB)',
        endpoint: '/convert/compress-pdf',
        extra: 'pdf-compress',
    },
    'merge-pdfs': {
        category: 'pdf',
        label: '📑 Juntar PDFs (Mesclar / Merge)',
        accept: '.pdf',
        hint: 'PDF (selecione 2 ou mais arquivos)',
        endpoint: '/convert/merge-pdfs',
        extra: 'pdf-merge',
        multiple: true,
    },
    'pdf-to-image': {
        category: 'pdf',
        label: 'PDF → Imagem',
        accept: '.pdf',
        hint: 'PDF (cada página vira PNG/JPG)',
        endpoint: '/convert/pdf-to-image',
        extra: 'pdf-to-image',
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
const pdfCompressWrap = document.getElementById('pdfCompressWrap');
const compressTargetSelect = document.getElementById('compressTargetSelect');
const progressWrap = document.getElementById('progressWrap');
const progressText = document.getElementById('progressText');
const progressMsg = document.getElementById('progressMsg');
const progressBar = document.getElementById('progressBar');

// ── Populate conversion types based on category ────────────────
const categoryAliases = {
    'pdf-large': 'pdf',
    'pdf-tools': 'pdf',
};

const categoryMap = {};
for (const [key, def] of Object.entries(conversions)) {
    if (!categoryMap[def.category]) categoryMap[def.category] = [];
    categoryMap[def.category].push({ key, ...def });
}

function updateConversionTypes() {
    const rawCat = categorySelect.value;
    const cat = categoryAliases[rawCat] || rawCat;
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
    pdfCompressWrap.classList.add('hidden');
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
    } else if (def && def.extra === 'pdf-compress') {
        extraOptions.classList.remove('hidden');
        imageFormatSelect.parentElement.classList.add('hidden');
        dpiInput.parentElement.classList.add('hidden');
        ocrToggle.classList.add('hidden');
        ocrLangWrap.classList.add('hidden');
        pdfEngineWrap.classList.add('hidden');
        pdfRangeWrap.classList.add('hidden');
        pdfCompressWrap.classList.remove('hidden');
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
        fileName.textContent = `${files[0].name} (${formatSize(files[0].size)})`;
        fileName.classList.remove('hidden');
        fileLabel.classList.add('hidden');
    } else if (files.length > 1) {
        const totalBytes = files.reduce((acc, f) => acc + f.size, 0);
        fileName.textContent = `${files.length} arquivos selecionados (${formatSize(totalBytes)})`;
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
        const totalBytes = Array.from(fileInput.files || []).reduce((acc, f) => acc + f.size, 0);
        fileName.textContent = (fileInput.files.length === 1)
            ? `${fileInput.files[0].name} (${formatSize(fileInput.files[0].size)})`
            : `${fileInput.files.length} arquivos selecionados (${formatSize(totalBytes)})`;
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

    // Limite de upload (espelha MAX_UPLOAD_SIZE_MB configurado no servidor)
    const MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024;
    for (const f of selectedFiles) {
        if (f.size > MAX_UPLOAD_SIZE_BYTES) {
            showStatus(`O arquivo "${f.name}" excede o limite de 50 MB.`, 'red');
            return;
        }
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
    } else if (def.extra === 'pdf-compress') {
        params.set('target', compressTargetSelect.value || '10');
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
        const isJobBased = (def.extra === 'pdf-to-word' || def.extra === 'pdf-to-word-large' || def.extra === 'pdf-compress');

        if (isJobBased) {
            setProgressVisible(true);
            setProgress(3);
            setProgressMessage('Enviando arquivo para o servidor…');

            const jobEndpoint = (def.extra === 'pdf-compress')
                ? '/convert/compress-pdf-job'
                : '/convert/pdf-to-word-job';

            const jobUrl = apiBase + jobEndpoint + (qs ? ('?' + qs) : '');
            let jobRes;
            try {
                jobRes = await fetch(jobUrl, { method: 'POST', body: formData });
            } catch (netErr) {
                throw new Error('Falha de rede ao conectar com o servidor. Verifique sua conexão.');
            }

            if (!jobRes.ok) {
                let detail = '';
                try {
                    const err = await jobRes.json();
                    detail = err.detail || '';
                } catch { }
                throw new Error(formatErrorMessage(jobRes.status, detail));
            }

            const job = await jobRes.json();
            const jobId = job.job_id;
            const statusUrl = apiBase + (job.status_url || (`/jobs/${jobId}`));
            const downloadUrl = apiBase + (job.download_url || (`/jobs/${jobId}/download`));

            while (true) {
                const st = await fetch(statusUrl, { method: 'GET' });
                if (!st.ok) {
                    throw new Error(formatErrorMessage(st.status));
                }
                const data = await st.json();
                setProgress(Number(data.progress || 0));
                setProgressMessage(data.message || 'Processando documento…');
                if (data.status === 'done') break;
                if (data.status === 'error') {
                    throw new Error(data.message || 'Falha durante o processamento do arquivo.');
                }
                await sleep(500);
            }

            setProgress(96);
            setProgressMessage('Gerando download do arquivo final…');

            const res = await fetch(downloadUrl, { method: 'GET' });
            if (!res.ok) {
                throw new Error(formatErrorMessage(res.status));
            }

            const blob = await res.blob();
            downloadBlob(blob, selectedFiles[0].name, res.headers.get('Content-Disposition') || '');
            setProgress(100);

            if (def.extra === 'pdf-compress') {
                const origSize = selectedFiles[0].size;
                const newSize = blob.size;
                if (newSize < origSize) {
                    const savedPct = Math.round((1 - (newSize / origSize)) * 100);
                    showStatus(`PDF comprimido com sucesso: de ${formatSize(origSize)} para ${formatSize(newSize)} (${savedPct}% de redução). Download iniciado.`, 'green');
                } else {
                    showStatus(`O PDF já se encontrava com tamanho otimizado (${formatSize(origSize)}). Download iniciado.`, 'green');
                }
            } else {
                showStatus('Conversão concluída com sucesso! Download iniciado.', 'green');
            }
            return;
        }

        setProgressVisible(true);
        setProgress(15);
        setProgressMessage('Enviando documento e processando…');

        let simProgress = 15;
        const progressTimer = setInterval(() => {
            if (simProgress < 88) {
                simProgress += Math.min(8, Math.max(2, Math.floor((88 - simProgress) / 5)));
                setProgress(simProgress);
            }
        }, 500);

        let res;
        try {
            res = await fetch(apiBase + url, { method: 'POST', body: formData });
        } catch (netErr) {
            throw new Error('Falha de rede ao conectar com o servidor.');
        } finally {
            clearInterval(progressTimer);
        }

        if (!res.ok) {
            let detail = '';
            try {
                const err = await res.json();
                detail = err.detail || '';
            } catch {
                try {
                    const text = await res.text();
                    if (text) detail = text.slice(0, 200);
                } catch { }
            }
            throw new Error(formatErrorMessage(res.status, detail));
        }

        setProgress(95);
        setProgressMessage('Finalizando download…');

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

        setProgress(100);
        showStatus('Conversão concluída com sucesso! Download iniciado.', 'green');
    } catch (err) {
        showStatus(err.message, 'red');
    } finally {
        setLoading(false);
        setTimeout(() => setProgressVisible(false), 1800);
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

function formatSize(bytes) {
    const n = Number(bytes);
    if (!Number.isFinite(n) || n <= 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    let value = n;
    while (value >= 1024 && i < units.length - 1) {
        value /= 1024;
        i += 1;
    }
    const digits = value >= 100 ? 0 : (value >= 10 ? 1 : 2);
    return `${value.toFixed(digits)} ${units[i]}`;
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

function formatErrorMessage(status, rawMessage) {
    if (status === 524) {
        return 'Tempo limite da Cloudflare esgotado (Erro 524). O processamento levou mais de 100 segundos. O novo modo com barra de progresso foi ativado para evitar essa falha.';
    }
    if (status === 504) {
        return 'Tempo limite do servidor esgotado (Erro 504). O arquivo é muito extenso para processamento síncrono.';
    }
    if (status === 413) {
        return 'Arquivo muito grande (Erro 413). O limite configurado no servidor é de 50 MB.';
    }
    if (status === 429) {
        return 'Muitas requisições enviadas em sequência (Erro 429). Aguarde alguns instantes e tente novamente.';
    }
    if (status === 502 || status === 503) {
        return `Servidor temporariamente indisponível (Erro ${status}). O serviço pode estar reiniciando na VPS.`;
    }
    if (rawMessage && typeof rawMessage === 'string') {
        const trimmed = rawMessage.trim();
        if (!trimmed.includes('<html') && !trimmed.includes('<!DOCTYPE') && !trimmed.startsWith('Erro ')) {
            return trimmed;
        }
    }
    return status ? `Falha no processamento (Erro HTTP ${status}). Verifique o arquivo e tente novamente.` : 'Falha na conexão com o servidor. Verifique sua rede.';
}

function escapeHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function showStatus(msg, type) {
    const cleanMsg = String(msg || '').replace(/^[\u274c\u2705]\s*/, '').trim();
    if (type === 'red') {
        statusMessage.className = 'text-sm rounded-xl p-4 bg-red-50 text-red-800 border border-red-200 flex items-start gap-3 shadow-sm';
        statusMessage.innerHTML = `
            <svg class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>
            <div class="space-y-0.5 text-left">
                <p class="font-semibold text-red-900">Atenção</p>
                <p class="text-xs text-red-700 leading-relaxed">${escapeHtml(cleanMsg)}</p>
            </div>
        `;
    } else {
        statusMessage.className = 'text-sm rounded-xl p-4 bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-start gap-3 shadow-sm';
        statusMessage.innerHTML = `
            <svg class="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <div class="space-y-0.5 text-left">
                <p class="font-semibold text-emerald-900">Sucesso!</p>
                <p class="text-xs text-emerald-700 leading-relaxed">${escapeHtml(cleanMsg)}</p>
            </div>
        `;
    }
    statusMessage.classList.remove('hidden');
}

function hideStatus() {
    statusMessage.classList.add('hidden');
}
