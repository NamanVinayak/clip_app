// DOM Elements
const uploadBox = document.getElementById('uploadBox');
const videoInput = document.getElementById('videoInput');
const processBtn = document.getElementById('processBtn');
const uploadSection = document.getElementById('uploadSection');
const progressSection = document.getElementById('progressSection');
const resultsSection = document.getElementById('resultsSection');
const errorSection = document.getElementById('errorSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const statusBadge = document.getElementById('statusBadge');
const logContent = document.getElementById('logContent');
const clipsGrid = document.getElementById('clipsGrid');
const errorMessage = document.getElementById('errorMessage');
const newVideoBtn = document.getElementById('newVideoBtn');
const retryBtn = document.getElementById('retryBtn');

let selectedFile = null;
let ws = null;

// Upload box interactions
uploadBox.addEventListener('click', () => videoInput.click());

uploadBox.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadBox.classList.add('dragover');
});

uploadBox.addEventListener('dragleave', () => {
    uploadBox.classList.remove('dragover');
});

uploadBox.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadBox.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});

videoInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelect(e.target.files[0]);
    }
});

function handleFileSelect(file) {
    // Validate file type
    if (!file.type.startsWith('video/')) {
        alert('Please select a video file');
        return;
    }

    // Validate file size (2GB max)
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB in bytes
    if (file.size > maxSize) {
        alert('File is too large. Maximum size is 2GB.');
        return;
    }

    selectedFile = file;
    processBtn.disabled = false;

    // Update upload box text
    const uploadText = uploadBox.querySelector('.upload-text');
    uploadText.textContent = `Selected: ${file.name}`;
    uploadText.style.color = 'var(--success)';
}

// Process button
processBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    // Hide upload, show progress
    uploadSection.classList.add('hidden');
    progressSection.classList.remove('hidden');

    // Connect to WebSocket for progress updates
    connectWebSocket();

    // Upload video and start processing
    await uploadAndProcess();
});

function connectWebSocket() {
    const wsUrl = `ws://${window.location.host}/ws`;
    ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleProgressUpdate(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket connection closed');
    };
}

async function uploadAndProcess() {
    const formData = new FormData();
    formData.append('video', selectedFile);

    try {
        const response = await fetch('/process', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (response.ok) {
            showResults(result);
        } else {
            showError(result.detail || 'Processing failed');
        }
    } catch (error) {
        showError('Network error: ' + error.message);
    }
}

function handleProgressUpdate(data) {
    const { step, status, message, progress } = data;

    // Update status badge
    statusBadge.textContent = message || status;
    statusBadge.className = 'status-badge processing';

    // Update progress bar
    if (progress !== undefined) {
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}% complete`;
    }

    // Update step status
    if (step) {
        const stepElement = document.querySelector(`.step[data-step="${step}"]`);
        if (stepElement) {
            stepElement.classList.remove('active');
            stepElement.classList.add(status);

            const stepStatus = stepElement.querySelector('.step-status');
            stepStatus.textContent = message || status;
        }
    }

    // Add to log
    addLog(message || `${step}: ${status}`);
}

function addLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = 'log-entry';
    logEntry.textContent = `[${timestamp}] ${message}`;
    logContent.appendChild(logEntry);
    logContent.scrollTop = logContent.scrollHeight;
}

function showResults(result) {
    progressSection.classList.add('hidden');
    resultsSection.classList.remove('hidden');

    // Clear previous results
    clipsGrid.innerHTML = '';

    // Display clips
    result.clips.forEach((clip, index) => {
        const clipCard = createClipCard(clip, index + 1);
        clipsGrid.appendChild(clipCard);
    });

    // Close WebSocket
    if (ws) {
        ws.close();
    }
}

function createClipCard(clip, number) {
    const card = document.createElement('div');
    card.className = 'clip-card';

    card.innerHTML = `
        <video class="clip-video" controls>
            <source src="${clip.url}" type="video/mp4">
        </video>
        <div class="clip-info">
            <div class="clip-title">Clip ${number}: ${clip.title || 'Untitled'}</div>
            <div class="clip-score">Virality Score: ${clip.virality_score || 'N/A'}</div>
            <div class="clip-reason">${clip.reason || 'No description available'}</div>
            <div class="clip-meta">
                Duration: ${clip.duration}s | ${clip.start_time} - ${clip.end_time}
            </div>
            <button class="clip-download" onclick="downloadClip('${clip.url}', 'clip_${number}.mp4')">
                Download Clip
            </button>
        </div>
    `;

    return card;
}

function downloadClip(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function showError(message) {
    progressSection.classList.add('hidden');
    errorSection.classList.remove('hidden');
    errorMessage.textContent = message;

    // Close WebSocket
    if (ws) {
        ws.close();
    }
}

function resetApp() {
    // Hide all sections except upload
    uploadSection.classList.remove('hidden');
    progressSection.classList.add('hidden');
    resultsSection.classList.add('hidden');
    errorSection.classList.add('hidden');

    // Reset state
    selectedFile = null;
    processBtn.disabled = true;

    // Reset upload box
    const uploadText = uploadBox.querySelector('.upload-text');
    uploadText.textContent = 'Drop your video here or click to browse';
    uploadText.style.color = '';

    // Reset progress
    progressFill.style.width = '0%';
    progressText.textContent = '0% complete';
    logContent.innerHTML = '';

    // Reset steps
    document.querySelectorAll('.step').forEach(step => {
        step.classList.remove('active', 'complete', 'error');
        const stepStatus = step.querySelector('.step-status');
        stepStatus.textContent = 'Waiting...';
    });

    // Reset video input
    videoInput.value = '';
}

// Button handlers
newVideoBtn.addEventListener('click', resetApp);
retryBtn.addEventListener('click', resetApp);
