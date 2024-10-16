if (videoForm) {
    videoForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData();

        try {
            uploadButton.disabled = true;
            uploadButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';

            // Add progress bar
            const progressContainer = document.createElement('div');
            progressContainer.className = 'progress mt-2';
            progressContainer.innerHTML = '<div id="upload-progress" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>';
            uploadButton.parentNode.insertBefore(progressContainer, uploadButton.nextSibling);

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
            
            try {
                await uploadFileToS3(personalVideo, personalVideoUploadData.uploadUrl);
            } catch (uploadError) {
                console.error('Error uploading file:', uploadError);
                throw new Error(`Error uploading file: ${uploadError.message}. Please try again or check your network connection.`);
            }
            
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
                throw new Error(`Error processing video: ${data.message}`);
            }
        } catch (error) {
            console.error('Error uploading video:', error);
            showErrorMessage(`An error occurred: ${error.message}. Please try again later or contact support if the problem persists.`);
        } finally {
            uploadButton.disabled = false;
            uploadButton.innerHTML = 'Upload Video';
            const progressContainer = document.querySelector('.progress');
            if (progressContainer) {
                progressContainer.remove();
            }
        }
    });
}
