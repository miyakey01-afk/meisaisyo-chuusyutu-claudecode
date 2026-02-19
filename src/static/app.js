// 明細抽出くん Ver2 - Upload form JavaScript

const MAX_FILES = 10;
const ALLOWED_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'];

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileList = document.getElementById('file-list');
const submitBtn = document.getElementById('submit-btn');
const uploadForm = document.getElementById('upload-form');
const uploadArea = document.getElementById('upload-area');
const processing = document.getElementById('processing');
const result = document.getElementById('result');
const errorDiv = document.getElementById('error');

let selectedFiles = [];

// Drag & drop
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    addFiles(e.dataTransfer.files);
});

// File input change
fileInput.addEventListener('change', () => {
    addFiles(fileInput.files);
    fileInput.value = '';
});

function addFiles(newFiles) {
    for (const file of newFiles) {
        if (selectedFiles.length >= MAX_FILES) {
            alert(`ファイルは同時に${MAX_FILES}枚までです。`);
            break;
        }
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            alert(`サポートされていないファイル形式です: ${file.name}`);
            continue;
        }
        selectedFiles.push(file);
    }
    renderFileList();
}

function removeFile(index) {
    selectedFiles.splice(index, 1);
    renderFileList();
}

function renderFileList() {
    if (selectedFiles.length === 0) {
        fileList.innerHTML = '';
        submitBtn.disabled = true;
        return;
    }
    let html = '<ul class="file-list">';
    selectedFiles.forEach((file, i) => {
        const sizeMB = (file.size / 1024 / 1024).toFixed(1);
        html += `<li>${file.name} (${sizeMB}MB) <button type="button" onclick="removeFile(${i})" class="btn-remove">x</button></li>`;
    });
    html += '</ul>';
    fileList.innerHTML = html;
    submitBtn.disabled = false;
}

// Form submission
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (selectedFiles.length === 0) return;

    uploadArea.classList.add('hidden');
    processing.classList.remove('hidden');
    result.classList.add('hidden');
    errorDiv.classList.add('hidden');

    const formData = new FormData();
    selectedFiles.forEach(file => formData.append('files', file));

    try {
        const response = await fetch('/extract', {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();

        processing.classList.add('hidden');

        if (data.success) {
            document.getElementById('drive-link').href = data.drive_url;
            document.getElementById('result-filename').textContent = data.filename;
            result.classList.remove('hidden');
        } else {
            document.getElementById('error-message').textContent = data.error_message;
            errorDiv.classList.remove('hidden');
        }
    } catch (err) {
        processing.classList.add('hidden');
        document.getElementById('error-message').textContent =
            'ネットワークエラーが発生しました。もう一度お試しください。';
        errorDiv.classList.remove('hidden');
    }
});

function resetForm() {
    selectedFiles = [];
    renderFileList();
    uploadArea.classList.remove('hidden');
    processing.classList.add('hidden');
    result.classList.add('hidden');
    errorDiv.classList.add('hidden');
}
