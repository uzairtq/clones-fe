@app.route('/process_videos', methods=['POST'])
def process_videos():
    try:
        logger.debug("Received request to process videos")
        personal_video_s3_key = request.form.get('personal_video_s3_key')
        youtube_url = request.form.get('youtube_url')
        personal_video_thumbnail = request.form.get('personal_video_thumbnail')

        logger.debug(f"Personal video S3 key: {personal_video_s3_key}")
        logger.debug(f"YouTube URL: {youtube_url}")

        if not personal_video_s3_key:
            logger.error("Personal video S3 key is missing")
            return jsonify({'status': 'error', 'message': 'Personal video S3 key is required'}), 400

        if not youtube_url:
            logger.error("YouTube URL is missing")
            return jsonify({'status': 'error', 'message': 'YouTube URL is required'}), 400

        if not personal_video_thumbnail:
            logger.error("Personal video thumbnail is missing")
            return jsonify({'status': 'error', 'message': 'Personal video thumbnail is required'}), 400

        global s3_client
        if not s3_client:
            logger.error("S3 client is not initialized. Attempting to reinitialize.")
            s3_client = initialize_s3_client()
            if not s3_client:
                logger.error("Failed to reinitialize S3 client.")
                return jsonify({'status': 'error', 'message': 'S3 connection error. Please try again later.'}), 500

        try:
            # Check if the multipart upload is complete
            s3_client.head_object(Bucket=S3_BUCKET, Key=personal_video_s3_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.error(f"Error validating S3 object: File not found. Key: {personal_video_s3_key}")
                return jsonify({'status': 'error', 'message': 'Video upload incomplete or failed. Please try uploading again.'}), 400
            else:
                logger.error(f"Error validating S3 object: {str(e)}")
                return jsonify({'status': 'error', 'message': 'Error validating uploaded video. Please try again.'}), 500

        personal_video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{personal_video_s3_key}"
        logger.debug(f"Personal video URL: {personal_video_url}")

        try:
            thumbnail_url = upload_thumbnail_to_s3(personal_video_thumbnail, personal_video_s3_key)
            if not thumbnail_url:
                raise Exception("Failed to upload thumbnail to S3")
        except Exception as thumb_error:
            logger.error(f"Failed to upload thumbnail to S3: {str(thumb_error)}")
            return jsonify({'status': 'error', 'message': 'Failed to upload thumbnail'}), 500

        try:
            youtube_info = get_youtube_video_info(youtube_url)
            if not youtube_info:
                raise Exception("Failed to get YouTube video info")
        except Exception as yt_error:
            logger.error(f"Failed to get YouTube video info: {str(yt_error)}")
            return jsonify({'status': 'error', 'message': 'Invalid YouTube URL or unable to fetch video information'}), 400

        logger.debug(f"YouTube video info: {youtube_info}")

        uploaded_video_url = personal_video_url

        logger.debug("Video processing completed successfully")
        return jsonify({
            'status': 'success',
            'message': 'Video uploaded successfully.',
            'uploaded_video_url': uploaded_video_url,
            'personal_video_thumbnail': thumbnail_url,
            'youtube_info': youtube_info
        })

    except Exception as e:
        logger.error(f"Error processing videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}. Please try again later.'}), 500
