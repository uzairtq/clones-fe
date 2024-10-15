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
            alert('Unable to access camera. Please make sure you have granted the necessary permissions and that no other application is using the camera.');
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
            // In a real application, you would make an API call to get video information
            // For this example, we'll use mock data
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

    async function getUploadUrl(file) {
        const response = await fetch('/get-upload-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                fileName: file.name,
                fileType: file.type,
            }),
        });

        if (!response.ok) {
            throw new Error('Failed to get upload URL');
        }

        return response.json();
    }

    async function uploadFileToS3(file, uploadUrl) {
        const response = await fetch(uploadUrl, {
            method: 'PUT',
            body: file,
            headers: {
                'Content-Type': file.type,
            },
        });

        if (!response.ok) {
            throw new Error('Failed to upload file to S3');
        }
    }

    if (videoForm) {
        videoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData();

            try {
                // Upload personal video
                const personalVideo = personalVideoInput.files[0];
                if (!personalVideo) {
                    throw new Error('Personal video is required');
                }

                const personalVideoUploadData = await getUploadUrl(personalVideo);
                await uploadFileToS3(personalVideo, personalVideoUploadData.uploadUrl);
                formData.append('personal_video_s3_key', personalVideoUploadData.s3Key);

                // Add YouTube URL
                formData.append('youtube_url', youtubeUrlInput.value);

                // Process videos
                const response = await fetch('/process_videos', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (data.status === 'success') {
                    fusedVideo.src = data.fused_video_url;
                    resultSection.classList.remove('d-none');
                    simulationMessage.innerHTML = `
                        <div class="alert alert-info mt-3" role="alert">
                            ${data.message}
                        </div>
                    `;
                    simulationMessage.classList.remove('d-none');
                } else {
                    alert('Error processing videos: ' + data.message);
                }
            } catch (error) {
                console.error('Error processing videos:', error);
                alert('An error occurred. Please try again.');
            }
        });
    }

    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
});
