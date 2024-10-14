document.addEventListener('DOMContentLoaded', () => {
    const videoForm = document.getElementById('video-form');
    const personalVideoInput = document.getElementById('personal-video');
    const recordVideoButton = document.getElementById('record-video');
    const youtubeUrlInput = document.getElementById('youtube-url');
    const referenceVideoFileInput = document.getElementById('reference-video-file');
    const youtubeOption = document.getElementById('youtube-option');
    const fileOption = document.getElementById('file-option');
    const personalVideoInfo = document.getElementById('personal-video-info');
    const referenceVideoInfo = document.getElementById('reference-video-info');
    const resultSection = document.getElementById('result');
    const fusedVideo = document.getElementById('fused-video');

    let mediaRecorder;
    let recordedChunks = [];

    recordVideoButton.addEventListener('click', async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            const videoElement = document.createElement('video');
            videoElement.srcObject = stream;
            videoElement.play();

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
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            recordVideoButton.textContent = 'Stop Recording';
            recordVideoButton.classList.remove('btn-primary');
            recordVideoButton.classList.add('btn-danger');
        } catch (error) {
            console.error('Error accessing camera:', error);
            alert('Unable to access camera. Please make sure you have granted the necessary permissions.');
        }
    });

    personalVideoInput.addEventListener('change', updatePersonalVideoInfo);
    youtubeUrlInput.addEventListener('input', updateReferenceVideoInfo);
    referenceVideoFileInput.addEventListener('change', updateReferenceVideoInfo);

    youtubeOption.addEventListener('change', toggleReferenceVideoInputs);
    fileOption.addEventListener('change', toggleReferenceVideoInputs);

    function toggleReferenceVideoInputs() {
        if (youtubeOption.checked) {
            youtubeUrlInput.classList.remove('d-none');
            referenceVideoFileInput.classList.add('d-none');
        } else {
            youtubeUrlInput.classList.add('d-none');
            referenceVideoFileInput.classList.remove('d-none');
        }
        updateReferenceVideoInfo();
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
        if (youtubeOption.checked) {
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
        } else {
            const file = referenceVideoFileInput.files[0];
            if (file) {
                const videoElement = document.createElement('video');
                videoElement.preload = 'metadata';
                videoElement.onloadedmetadata = () => {
                    const duration = videoElement.duration;
                    referenceVideoInfo.innerHTML = `
                        <h5>Reference Video</h5>
                        <p>Filename: ${file.name}</p>
                        <p>Duration: ${formatDuration(duration)}</p>
                    `;
                };
                videoElement.src = URL.createObjectURL(file);
            } else {
                referenceVideoInfo.innerHTML = '';
            }
        }
    }

    videoForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(videoForm);

        try {
            const response = await fetch('/process_videos', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                fusedVideo.src = data.fused_video_url;
                resultSection.classList.remove('d-none');
            } else {
                alert('Error processing videos: ' + data.message);
            }
        } catch (error) {
            console.error('Error processing videos:', error);
            alert('An error occurred. Please try again.');
        }
    });

    function formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
});
