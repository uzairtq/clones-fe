import os
import logging
import traceback
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from flask import Flask, render_template, request, jsonify, redirect, url_for
from utils.youtube_api import get_youtube_video_info
from werkzeug.utils import secure_filename
from uuid import uuid4
from urllib.parse import urlparse
import psutil
from models import db, Video, FusedVideo

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videofusion.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

db.init_app(app)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def initialize_s3_client():
    try:
        return boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='us-east-1'  # Specify the correct region
        )
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please check your environment variables.")
        return None
    except Exception as e:
        logger.error(f"Error initializing S3 client: {str(e)}")
        return None

s3_client = initialize_s3_client()

S3_BUCKET = os.environ.get('S3_BUCKET')

def generate_presigned_url(file_name, file_type):
    if not s3_client:
        logger.error("S3 client is not initialized. Cannot generate presigned URL.")
        return None

    s3_key = f"user-uploads/{file_name}-{uuid4()}"
    try:
        response = s3_client.generate_presigned_url('put_object',
                                                    Params={'Bucket': S3_BUCKET,
                                                            'Key': s3_key,
                                                            'ContentType': file_type},
                                                    ExpiresIn=3600)
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        logger.error(traceback.format_exc())
        return None
    return {'uploadUrl': response, 's3Key': s3_key}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gallery')
def gallery():
    fused_videos = FusedVideo.query.order_by(FusedVideo.created_at.desc()).all()
    return render_template('gallery.html', fused_videos=fused_videos)

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
        personal_video_s3_key = request.form.get('personal_video_s3_key')
        youtube_url = request.form.get('youtube_url')

        logger.debug(f"Personal video S3 key: {personal_video_s3_key}")
        logger.debug(f"YouTube URL: {youtube_url}")

        if not personal_video_s3_key:
            logger.error("Personal video S3 key is missing")
            return jsonify({'status': 'error', 'message': 'Personal video S3 key is required'}), 400

        if not youtube_url:
            logger.error("YouTube URL is missing")
            return jsonify({'status': 'error', 'message': 'YouTube URL is required'}), 400

        # Validate S3 key
        if not s3_client:
            logger.error("S3 client is not initialized. Cannot validate S3 object.")
            return jsonify({'status': 'error', 'message': 'S3 connection error. Please try again later.'}), 500

        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=personal_video_s3_key)
        except ClientError as e:
            logger.error(f"Error validating S3 object: {str(e)}")
            return jsonify({'status': 'error', 'message': 'Invalid or inaccessible personal video'}), 400

        personal_video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{personal_video_s3_key}"
        logger.debug(f"Personal video URL: {personal_video_url}")

        # Process reference video (YouTube)
        youtube_info = get_youtube_video_info(youtube_url)
        if not youtube_info:
            logger.error("Failed to get YouTube video info")
            return jsonify({'status': 'error', 'message': 'Invalid YouTube URL'}), 400

        logger.debug(f"YouTube video info: {youtube_info}")

        # TODO: Implement actual video fusion logic
        # For now, we'll just return the personal video URL as the fused video
        fused_video_url = personal_video_url

        # Store fused video information in the database
        new_fused_video = FusedVideo(
            personal_video_url=personal_video_url,
            reference_video_url=youtube_url,
            fused_video_url=fused_video_url
        )
        db.session.add(new_fused_video)
        db.session.commit()

        logger.debug("Video processing completed successfully")
        return jsonify({
            'status': 'success',
            'message': 'Video processing completed successfully.',
            'fused_video_url': fused_video_url
        })

    except Exception as e:
        logger.error(f"Error processing videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}. Please try again later.'}), 500

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
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)