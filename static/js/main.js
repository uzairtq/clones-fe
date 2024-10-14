document.addEventListener('DOMContentLoaded', () => {
    const personalVideoInput = document.getElementById('personal-video');
    const recordVideoButton = document.getElementById('record-video');
    const youtubeUrlInput = document.getElementById('youtube-url');
    const personalVideoInfo = document.getElementById('personal-video-info');
    const youtubeVideoInfo = document.getElementById('youtube-video-info');
    const fuseButton = document.getElementById('fuse-button');
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
                personalVideoInput.files = new FileList([file]);
                updatePersonalVideoInfo();
            };

            mediaRecorder.start();
            recordVideoButton.textContent = 'Stop Recording';
            recordVideoButton.classList.remove('bg-blue-500', 'hover:bg-blue-700');
            recordVideoButton.classList.add('bg-red-500', 'hover:bg-red-700');
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    });

    personalVideoInput.addEventListener('change', updatePersonalVideoInfo);
    youtubeUrlInput.addEventListener('input', updateYoutubeVideoInfo);

    function updatePersonalVideoInfo() {
        const file = personalVideoInput.files[0];
        if (file) {
            const videoElement = document.createElement('video');
            videoElement.preload = 'metadata';
            videoElement.onloadedmetadata = () => {
                const duration = videoElement.duration;
                personalVideoInfo.innerHTML = `
                    <h3 class="font-bold">Personal Video</h3>
                    <p>Duration: ${formatDuration(duration)}</p>
                `;
            };
            videoElement.src = URL.createObjectURL(file);
        } else {
            personalVideoInfo.innerHTML = '';
        }
    }

    function updateYoutubeVideoInfo() {
        const youtubeUrl = youtubeUrlInput.value;
        if (youtubeUrl) {
            // In a real application, you would make an API call to get video information
            // For this example, we'll use mock data
            const mockData = {
                title: 'Sample YouTube Video',
                thumbnail: 'https://img.youtube.com/vi/dQw4w9WgXcQ/0.jpg',
                duration: 212
            };

            youtubeVideoInfo.innerHTML = `
                <h3 class="font-bold">YouTube Video</h3>
                <p>Title: ${mockData.title}</p>
                <p>Duration: ${formatDuration(mockData.duration)}</p>
                <img src="${mockData.thumbnail}" alt="YouTube Thumbnail" class="mt-2 max-w-full h-auto">
            `;
        } else {
            youtubeVideoInfo.innerHTML = '';
        }
    }

    fuseButton.addEventListener('click', async () => {
        const personalVideo = personalVideoInput.files[0];
        const youtubeUrl = youtubeUrlInput.value;

        if (!personalVideo && !youtubeUrl) {
            alert('Please provide at least one video source');
            return;
        }

        const formData = new FormData();
        if (personalVideo) {
            formData.append('personal_video', personalVideo);
        }
        if (youtubeUrl) {
            formData.append('youtube_url', youtubeUrl);
        }

        try {
            const response = await fetch('/process_videos', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                fusedVideo.src = data.fused_video_url;
                resultSection.classList.remove('hidden');
            } else {
                alert('Error processing videos. Please try again.');
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
