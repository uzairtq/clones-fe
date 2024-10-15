document.addEventListener('DOMContentLoaded', () => {
    const videoForm = document.getElementById('video-form');
    const personalVideoInput = document.getElementById('personal-video');
    const recordVideoButton = document.getElementById('record-video');
    const stopRecordingButton = document.getElementById('stop-recording');
    const videoPreview = document.getElementById('video-preview');
    const youtubeUrlInput = document.getElementById('youtube-url');
    const personalVideoInfo = document.getElementById('personal-video-info');
    const referenceVideoInfo = document.getElementById('reference-video-info');
    const resultSection = document.getElementById('result');
    const fusedVideo = document.getElementById('fused-video');
    const simulationMessage = document.getElementById('simulation-message');
    const serverStatus = document.getElementById('server-status');
    const gallerySection = document.getElementById('gallery-section');

    let mediaRecorder;
    let recordedChunks = [];
    let stream;

    if (recordVideoButton) {
        recordVideoButton.addEventListener('click', startRecording);
    }
    if (stopRecordingButton) {
        stopRecordingButton.addEventListener('click', stopRecording);
    }

    async function startRecording() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            videoPreview.srcObject = stream;
            videoPreview.classList.remove('d-none');

            mediaRecorder = new MediaRecorder(stream);

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    recordedChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(recordedChunks, { type: 'video/webm' });
                const file = new File([blob], 'recorded_video.webm', { type: 'video/webm' });
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                personalVideoInput.files = dataTransfer.files;
                updatePersonalVideoInfo();
            };

            mediaRecorder.start();
            recordVideoButton.classList.add('d-none');
            stopRecordingButton.classList.remove('d-none');
        } catch (error) {
            console.error('Error accessing camera:', error);
            showErrorMessage('Unable to access camera. Please make sure you have granted the necessary permissions and that no other application is using the camera.');
        }
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            stream.getTracks().forEach(track => track.stop());
            videoPreview.classList.add('d-none');
            recordVideoButton.classList.remove('d-none');
            stopRecordingButton.classList.add('d-none');
            recordedChunks = [];
        }
    }

    if (personalVideoInput) {
        personalVideoInput.addEventListener('change', updatePersonalVideoInfo);
    }
    if (youtubeUrlInput) {
        youtubeUrlInput.addEventListener('input', updateReferenceVideoInfo);
    }

    function updatePersonalVideoInfo() {
        const file = personalVideoInput.files[0];
        if (file) {
            const videoElement = document.createElement('video');
            videoElement.preload = 'metadata';
            videoElement.onloadedmetadata = () => {
                const duration = videoElement.duration;
                personalVideoInfo.innerHTML = `
                    <h5>Personal Video</h5>
                    <p>Filename: ${file.name}</p>
                    <p>Duration: ${formatDuration(duration)}</p>
                `;
            };
            videoElement.src = URL.createObjectURL(file);
        } else {
            personalVideoInfo.innerHTML = '';
        }
    }

    function updateReferenceVideoInfo() {
        const youtubeUrl = youtubeUrlInput.value;
        if (youtubeUrl) {
            const mockData = {
                title: 'Sample YouTube Video',
                thumbnail: 'https://img.youtube.com/vi/dQw4w9WgXcQ/0.jpg',
                duration: 212
            };

            referenceVideoInfo.innerHTML = `
                <h5>YouTube Video</h5>
                <p>Title: ${mockData.title}</p>
                <p>Duration: ${formatDuration(mockData.duration)}</p>
                <img src="${mockData.thumbnail}" alt="YouTube Thumbnail" class="img-fluid mt-2">
            `;
        } else {
            referenceVideoInfo.innerHTML = '';
        }
    }

    async function fetchWithRetry(url, options = {}, retries = 3, backoff = 300) {
        try {
            const response = await fetchWithTimeout(url, options);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response;
        } catch (error) {
            if (retries > 0) {
                await new Promise(resolve => setTimeout(resolve, backoff));
                return fetchWithRetry(url, options, retries - 1, backoff * 2);
            } else {
                throw error;
            }
        }
    }

    async function getUploadUrl(file) {
        try {
            const response = await fetchWithRetry('/get-upload-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fileName: file.name,
                    fileType: file.type,
                }),
            });
            return response.json();
        } catch (error) {
            throw new Error(`Failed to get upload URL: ${error.message}. Please check your internet connection and try again.`);
        }
    }

    async function uploadFileToS3(file, uploadUrl) {
        try {
            const response = await fetchWithRetry(uploadUrl, {
                method: 'PUT',
                body: file,
                headers: {
                    'Content-Type': file.type,
                },
            });
            if (!response.ok) {
                throw new Error(`Failed to upload file to S3: ${response.statusText}`);
            }
        } catch (error) {
            throw new Error(`Error uploading file: ${error.message}. Please try again or contact support if the problem persists.`);
        }
    }

    if (videoForm) {
        videoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData();

            try {
                const personalVideo = personalVideoInput.files[0];
                if (!personalVideo) {
                    throw new Error('Personal video is required');
                }

                const personalVideoUploadData = await getUploadUrl(personalVideo);
                console.log('Upload URL:', personalVideoUploadData.uploadUrl);
                await uploadFileToS3(personalVideo, personalVideoUploadData.uploadUrl);
                formData.append('personal_video_s3_key', personalVideoUploadData.s3Key);

                formData.append('youtube_url', youtubeUrlInput.value);

                const response = await fetchWithRetry('/process_videos', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.status === 'success') {
                    fusedVideo.src = data.fused_video_url;
                    resultSection.classList.remove('d-none');
                    showSuccessMessage(data.message);
                    updateGallery(data.fused_video);
                } else {
                    showErrorMessage(`Error processing videos: ${data.message}`);
                }
            } catch (error) {
                console.error('Error processing videos:', error);
                showErrorMessage(`An error occurred: ${error.message}. Please try again later or contact support if the problem persists.`);
            }
        });
    }

    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    function showErrorMessage(message) {
        simulationMessage.innerHTML = `
            <div class="alert alert-danger mt-3" role="alert">
                ${message}
            </div>
        `;
        simulationMessage.classList.remove('d-none');
    }

    function showSuccessMessage(message) {
        simulationMessage.innerHTML = `
            <div class="alert alert-success mt-3" role="alert">
                ${message}
            </div>
        `;
        simulationMessage.classList.remove('d-none');
    }

    function updateGallery(fusedVideo) {
        const videoCard = document.createElement('div');
        videoCard.className = 'col-md-4 mb-4';
        videoCard.innerHTML = `
            <div class="card">
                <img src="${fusedVideo.youtube_thumbnail}" class="card-img-top" alt="${fusedVideo.youtube_title}">
                <div class="card-body">
                    <h5 class="card-title">${fusedVideo.youtube_title}</h5>
                    <a href="${fusedVideo.fused_video_url}" class="btn btn-primary" target="_blank">Watch Fused Video</a>
                </div>
            </div>
        `;
        gallerySection.appendChild(videoCard);
    }

    async function fetchWithTimeout(url, options = {}) {
        const timeout = 30000;
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(id);
            return response;
        } catch (error) {
            clearTimeout(id);
            throw error;
        }
    }

    let healthCheckInterval = 30000;
    const maxHealthCheckInterval = 300000;

    async function checkServerHealth() {
        try {
            const response = await fetchWithRetry('/api/health');
            const data = await response.json();
            if (data.status === 'healthy') {
                serverStatus.innerHTML = '';
                healthCheckInterval = 30000;
            } else {
                throw new Error(JSON.stringify(data));
            }
        } catch (error) {
            console.error('Server health check failed:', error);
            let errorMessage = 'The server may be experiencing issues. Some features might not work correctly.';
            
            try {
                const errorData = JSON.parse(error.message);
                if (errorData.s3_status === 'ERROR') {
                    errorMessage += ' There seems to be a problem with the storage service.';
                }
                if (errorData.cpu_usage > 90 || errorData.memory_usage > 90) {
                    errorMessage += ' The server is under high load.';
                }
            } catch (e) {
                // If parsing fails, we'll use the default error message
            }

            serverStatus.innerHTML = `
                <div class="alert alert-warning mt-3" role="alert">
                    Warning: ${errorMessage} We're working on resolving this. Please try again later.
                </div>
            `;
            healthCheckInterval = Math.min(healthCheckInterval * 2, maxHealthCheckInterval);
        } finally {
            setTimeout(checkServerHealth, healthCheckInterval);
        }
    }

    checkServerHealth();
});
