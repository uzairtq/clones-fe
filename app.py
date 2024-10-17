import os
import logging
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from botocore.exceptions import ClientError
import boto3
from utils.youtube_api import get_youtube_video_info
import traceback
import psutil
import isodate
import base64
import io
import subprocess
import tempfile
from pytube import YouTube

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET')
s3_client = None

def initialize_s3_client():
    try:
        return boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='us-east-1'
        )
    except Exception as e:
        logger.error(f"Error initializing S3 client: {str(e)}")
        return None

s3_client = initialize_s3_client()

def generate_presigned_url(file_name, file_type):
    if not s3_client:
        logger.error("S3 client is not initialized")
        return None

    s3_key = f"user-uploads/{Path(file_name).stem}-{uuid.uuid4()}{Path(file_name).suffix}"
    try:
        response = s3_client.generate_presigned_url(
            'put_object',
            Params={'Bucket': S3_BUCKET, 'Key': s3_key, 'ContentType': file_type},
            ExpiresIn=3600
        )
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None
    return {'uploadUrl': response, 's3Key': s3_key}

def upload_thumbnail_to_s3(thumbnail_data, video_key):
    if not s3_client:
        logger.error("S3 client is not initialized")
        return None

    try:
        # Remove the "data:image/jpeg;base64," prefix
        thumbnail_data = thumbnail_data.split(',')[1]
        thumbnail_bytes = base64.b64decode(thumbnail_data)
        thumbnail_buffer = io.BytesIO(thumbnail_bytes)

        thumbnail_key = f"thumbnails/{os.path.basename(video_key).split('.')[0]}.jpg"
        s3_client.upload_fileobj(thumbnail_buffer, S3_BUCKET, thumbnail_key, ExtraArgs={'ContentType': 'image/jpeg'})
        return f"https://{S3_BUCKET}.s3.amazonaws.com/{thumbnail_key}"
    except Exception as e:
        logger.error(f"Error uploading thumbnail to S3: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-upload-url', methods=['POST'])
def get_upload_url():
    file_name = request.json.get('fileName')
    file_type = request.json.get('fileType')

    if not file_name or not file_type:
        return jsonify({'status': 'error', 'message': 'File name and type are required'}), 400

    presigned_data = generate_presigned_url(file_name, file_type)
    if not presigned_data:
        return jsonify({'status': 'error', 'message': 'Failed to generate upload URL'}), 500

    return jsonify({
        'status': 'success',
        'filename': file_name,
        's3Key': presigned_data['s3Key'],
        'uploadUrl': presigned_data['uploadUrl']
    })

@app.route('/process_videos', methods=['POST'])
def process_videos():
    try:
        logger.debug("Received request to process videos")
        data = request.json
        personal_video_s3_key = data.get('personal_video_s3_key')
        youtube_url = data.get('youtube_url')
        personal_video_thumbnail = data.get('personal_video_thumbnail')

        logger.debug(f"Personal video S3 key: {personal_video_s3_key}")
        logger.debug(f"YouTube URL: {youtube_url}")

        if not personal_video_s3_key or not youtube_url or not personal_video_thumbnail:
            logger.error("Missing required data")
            return jsonify({'status': 'error', 'message': 'Personal video S3 key, YouTube URL, and personal video thumbnail are required'}), 400

        # Validate S3 key
        if not s3_client:
            logger.error("S3 client is not initialized. Cannot validate S3 object.")
            return jsonify({'status': 'error', 'message': 'S3 connection error. Please try again later.'}), 500

        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=personal_video_s3_key)
        except ClientError as e:
            logger.error(f"Error validating S3 object: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Invalid or inaccessible personal video'}), 400

        # Download personal video from S3
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_personal_video:
            s3_client.download_fileobj(S3_BUCKET, personal_video_s3_key, temp_personal_video)
            personal_video_path = temp_personal_video.name

        # Download YouTube video
        yt = YouTube(youtube_url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
        youtube_video_path = tempfile.mktemp(suffix='.mp4')
        stream.download(filename=youtube_video_path)

        # Process videos using FFmpeg
        output_video_path = tempfile.mktemp(suffix='.mp4')
        ffmpeg_command = [
            'ffmpeg',
            '-i', personal_video_path,
            '-i', youtube_video_path,
            '-filter_complex', '[0:v][1:v]hstack=inputs=2[v];[0:a][1:a]amix=inputs=2[a]',
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-crf', '23',
            '-preset', 'veryfast',
            output_video_path
        ]

        try:
            subprocess.run(ffmpeg_command, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return jsonify({'status': 'error', 'message': 'Error processing videos'}), 500

        # Upload processed video to S3
        processed_video_key = f"processed-videos/{uuid.uuid4()}.mp4"
        s3_client.upload_file(output_video_path, S3_BUCKET, processed_video_key)

        # Generate URL for the processed video
        processed_video_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET, 'Key': processed_video_key},
            ExpiresIn=3600
        )

        # Upload thumbnail to S3
        thumbnail_url = upload_thumbnail_to_s3(personal_video_thumbnail, personal_video_s3_key)
        if not thumbnail_url:
            logger.error("Failed to upload thumbnail to S3")
            return jsonify({'status': 'error', 'message': 'Failed to upload thumbnail'}), 500

        # Get YouTube video info
        youtube_info = get_youtube_video_info(youtube_url)
        if not youtube_info:
            logger.error("Failed to get YouTube video info")
            return jsonify({'status': 'error', 'message': 'Invalid YouTube URL'}), 400

        logger.debug(f"YouTube video info: {youtube_info}")
        logger.debug("Video processing completed successfully")

        # Clean up temporary files
        os.unlink(personal_video_path)
        os.unlink(youtube_video_path)
        os.unlink(output_video_path)

        return jsonify({
            'status': 'success',
            'message': 'Videos processed and fused successfully.',
            'processed_video_url': processed_video_url,
            'personal_video_thumbnail': thumbnail_url,
            'youtube_info': youtube_info
        })

    except Exception as e:
        logger.error(f"Error processing videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}. Please try again later.'}), 500

@app.route('/get_youtube_info')
def get_youtube_info():
    youtube_url = request.args.get('url')
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    video_info = get_youtube_video_info(youtube_url)
    if not video_info:
        return jsonify({'error': 'Invalid YouTube URL or unable to fetch video information'}), 400

    return jsonify(video_info)

@app.route('/api/health', methods=['GET'])
def health_check():
    health_status = {
        'status': 'healthy',
        's3_status': 'ERROR',
        'cpu_usage': psutil.cpu_percent(),
        'memory_usage': psutil.virtual_memory().percent,
        'disk_usage': psutil.disk_usage('/').percent
    }

    # Check S3 connection
    global s3_client
    if not s3_client:
        s3_client = initialize_s3_client()

    if not s3_client:
        logger.error("S3 client is not initialized.")
        health_status['s3_status'] = 'ERROR'
        health_status['status'] = 'unhealthy'
        health_status['s3_error'] = 'S3 client initialization failed'
    else:
        try:
            s3_client.list_buckets()
            health_status['s3_status'] = 'OK'
        except Exception as e:
            logger.error(f"S3 health check failed: {str(e)}")
            health_status['s3_status'] = 'ERROR'
            health_status['status'] = 'unhealthy'
            health_status['s3_error'] = str(e)
            s3_client = None  # Reset the client to force reinitialization on next request

    logger.info(f"Health check: {health_status}")
    return jsonify(health_status), 200 if health_status['status'] == 'healthy' else 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
