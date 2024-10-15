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
    const uploadedVideo = document.getElementById('uploaded-video');
    const uploadMessage = document.getElementById('upload-message');
    const serverStatus = document.getElementById('server-status');
    const uploadButton = document.getElementById('upload-button');

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
                console.log('Recorded video blob:', blob.size, blob.type);
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

    async function generateThumbnail(file) {
        return new Promise((resolve, reject) => {
            const video = document.createElement('video');
            video.preload = 'metadata';
            console.log('Generating thumbnail for:', file.name);

            video.onloadedmetadata = () => {
                console.log('Video metadata loaded');
                video.currentTime = 2; // Seek to 2 seconds
            };

            video.addEventListener('loadeddata', () => {
                console.log('Video data loaded');
                try {
                    const canvas = document.createElement('canvas');
                    canvas.width = 320;
                    canvas.height = 180;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    const thumbnailDataUrl = canvas.toDataURL('image/jpeg');
                    console.log('Thumbnail generated successfully');
                    URL.revokeObjectURL(video.src);
                    resolve(thumbnailDataUrl);
                } catch (error) {
                    console.error('Error generating thumbnail:', error);
                    reject(error);
                }
            });

            video.onerror = (e) => {
                console.error('Error loading video for thumbnail:', e);
                URL.revokeObjectURL(video.src);
                reject(e);
            };

            const url = URL.createObjectURL(file);
            console.log('Video URL created:', url);
            video.src = url;
        });
    }

    function getDuration(file) {
        return new Promise((resolve, reject) => {
            const video = document.createElement('video');
            video.preload = 'metadata';
            
            const timeoutId = setTimeout(() => {
                reject(new Error('Timeout: Unable to get video duration'));
            }, 10000); // 10 seconds timeout

            video.onloadedmetadata = () => {
                console.log('Video readyState:', video.readyState);
                console.log('Video duration:', video.duration);
                clearTimeout(timeoutId);
                if (isFinite(video.duration)) {
                    resolve(video.duration);
                } else {
                    reject(new Error('Invalid video duration'));
                }
                URL.revokeObjectURL(video.src);
            };

            video.onerror = (e) => {
                clearTimeout(timeoutId);
                reject(new Error(`Error loading video: ${e.target.error.message}`));
                URL.revokeObjectURL(video.src);
            };

            console.log('Getting duration for:', file.name);
            const url = URL.createObjectURL(file);
            console.log('Video URL created for duration:', url);
            video.src = url;
        });
    }

    async function updatePersonalVideoInfo() {
        const file = personalVideoInput.files[0];
        if (file) {
            try {
                console.log('Processing file:', file.name);
                console.log('File type:', file.type);
                console.log('File size:', file.size);

                const [duration, thumbnailDataUrl] = await Promise.all([
                    getDuration(file),
                    generateThumbnail(file)
                ]);

                console.log('File processed successfully');
                console.log('Duration:', duration);
                personalVideoInfo.innerHTML = `
                    <h5>Personal Video</h5>
                    <p>Filename: ${file.name}</p>
                    <p>Duration: ${formatDuration(duration)}</p>
                    <img src="${thumbnailDataUrl}" alt="Personal Video Thumbnail" class="img-fluid mt-2 personal-thumbnail">
                `;
            } catch (error) {
                console.error('Error processing video:', error);
                personalVideoInfo.innerHTML = `
                    <h5>Personal Video</h5>
                    <p>Filename: ${file.name}</p>
                    <p class="text-danger">Error processing video: ${error.message}</p>
                    <p>Please try uploading the video again or use a different video file.</p>
                `;
            }
        } else {
            personalVideoInfo.innerHTML = '';
        }
    }

    function updateReferenceVideoInfo() {
        const youtubeUrl = youtubeUrlInput.value;
        if (youtubeUrl) {
            fetchYouTubeInfo(youtubeUrl);
        } else {
            referenceVideoInfo.innerHTML = '';
        }
    }

    async function fetchYouTubeInfo(url) {
        try {
            const response = await fetchWithRetry(`/get_youtube_info?url=${encodeURIComponent(url)}`);
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            referenceVideoInfo.innerHTML = `
                <h5>YouTube Video</h5>
                <p>Title: ${data.title}</p>
                <p>Duration: ${data.duration}</p>
                <img src="${data.thumbnail}" alt="YouTube Thumbnail" class="img-fluid mt-2">
            `;
        } catch (error) {
            console.error('Error fetching YouTube info:', error);
            referenceVideoInfo.innerHTML = `<p class="text-danger">Error: ${error.message}</p>`;
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
                uploadButton.disabled = true;
                uploadButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';

                const personalVideo = personalVideoInput.files[0];
                if (!personalVideo) {
                    throw new Error('Personal video is required');
                }

                const youtubeUrl = youtubeUrlInput.value;
                if (!youtubeUrl) {
                    throw new Error('YouTube URL is required');
                }

                const thumbnailDataUrl = await generateThumbnail(personalVideo);
                
                const personalVideoUploadData = await getUploadUrl(personalVideo);
                console.log('Upload URL:', personalVideoUploadData.uploadUrl);
                await uploadFileToS3(personalVideo, personalVideoUploadData.uploadUrl);
                formData.append('personal_video_s3_key', personalVideoUploadData.s3Key);
                formData.append('personal_video_thumbnail', thumbnailDataUrl);

                formData.append('youtube_url', youtubeUrl);

                const response = await fetchWithRetry('/process_videos', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.status === 'success') {
                    uploadedVideo.src = data.uploaded_video_url;
                    resultSection.classList.remove('d-none');
                    showSuccessMessage(data.message);
                    
                    const personalThumbnail = document.querySelector('.personal-thumbnail');
                    if (personalThumbnail) {
                        personalThumbnail.src = thumbnailDataUrl;
                        personalThumbnail.style.display = 'block';
                        personalThumbnail.style.maxWidth = '100%';
                        personalThumbnail.style.height = 'auto';
                    }

                    if (data.youtube_info) {
                        referenceVideoInfo.innerHTML = `
                            <h5>YouTube Video</h5>
                            <p>Title: ${data.youtube_info.title}</p>
                            <p>Duration: ${data.youtube_info.duration}</p>
                            <img src="${data.youtube_info.thumbnail}" alt="YouTube Thumbnail" class="img-fluid mt-2">
                        `;
                    }
                } else {
                    showErrorMessage(`Error uploading video: ${data.message}`);
                }
            } catch (error) {
                console.error('Error uploading video:', error);
                showErrorMessage(`An error occurred: ${error.message}. Please try again later or contact support if the problem persists.`);
            } finally {
                uploadButton.disabled = false;
                uploadButton.innerHTML = 'Upload Video';
            }
        });
    }

    function formatDuration(seconds) {
        if (isNaN(seconds) || seconds === Infinity) {
            return 'Unknown';
        }
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
    }

    function showErrorMessage(message) {
        uploadMessage.innerHTML = `
            <div class="alert alert-danger mt-3" role="alert">
                ${message}
            </div>
        `;
        uploadMessage.classList.remove('d-none');
    }

    function showSuccessMessage(message) {
        uploadMessage.innerHTML = `
            <div class="alert alert-success mt-3" role="alert">
                ${message}
            </div>
        `;
        uploadMessage.classList.remove('d-none');
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
