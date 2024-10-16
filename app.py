import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from botocore.exceptions import ClientError
import boto3
from utils.youtube_api import get_youtube_video_info
import traceback
import psutil
import uuid
import base64
import io

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

S3_BUCKET = os.environ.get('S3_BUCKET')
s3_client = None

def initialize_s3_client():
    try:
        client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name='us-east-1')
        
        # Set CORS configuration for the S3 bucket
        set_s3_cors_configuration(client)
        
        return client
    except Exception as e:
        logger.error(f"Error initializing S3 client: {str(e)}")
        return None

def set_s3_cors_configuration(s3_client):
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
            'AllowedOrigins': ['*'],
            'ExposeHeaders': ['ETag']
        }]
    }
    try:
        s3_client.put_bucket_cors(Bucket=S3_BUCKET, CORSConfiguration=cors_configuration)
        logger.info(f"CORS configuration set for bucket: {S3_BUCKET}")
    except Exception as e:
        logger.error(f"Error setting CORS configuration for S3 bucket: {str(e)}")

s3_client = initialize_s3_client()

def generate_presigned_url(file_name, file_type):
    if not s3_client:
        logger.error("S3 client is not initialized")
        return None

    s3_key = f"user-uploads/{Path(file_name).stem}-{uuid.uuid4()}{Path(file_name).suffix}"
    try:
        response = s3_client.generate_presigned_url('put_object',
                                                    Params={
                                                        'Bucket': S3_BUCKET,
                                                        'Key': s3_key,
                                                        'ContentType':
                                                        file_type
                                                    },
                                                    ExpiresIn=3600)
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None
    return {'uploadUrl': response, 's3Key': s3_key}

def upload_thumbnail_to_s3(thumbnail_data, video_key):
    if not s3_client:
        logger.error("S3 client is not initialized")
        return None

    try:
        thumbnail_data = thumbnail_data.split(',')[1]
        thumbnail_bytes = base64.b64decode(thumbnail_data)
        thumbnail_buffer = io.BytesIO(thumbnail_bytes)

        thumbnail_key = f"thumbnails/{os.path.basename(video_key).split('.')[0]}.jpg"
        s3_client.upload_fileobj(thumbnail_buffer,
                                 S3_BUCKET,
                                 thumbnail_key,
                                 ExtraArgs={'ContentType': 'image/jpeg'})
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
        return jsonify({
            'status': 'error',
            'message': 'File name and type are required'
        }), 400

    presigned_data = generate_presigned_url(file_name, file_type)
    if not presigned_data:
        return jsonify({
            'status': 'error',
            'message': 'Failed to generate upload URL'
        }), 500

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
        personal_video_thumbnail = request.form.get('personal_video_thumbnail')

        logger.debug(f"Personal video S3 key: {personal_video_s3_key}")
        logger.debug(f"YouTube URL: {youtube_url}")

        if not personal_video_s3_key:
            logger.error("Personal video S3 key is missing")
            return jsonify({
                'status': 'error',
                'message': 'Personal video S3 key is required'
            }), 400

        if not youtube_url:
            logger.error("YouTube URL is missing")
            return jsonify({
                'status': 'error',
                'message': 'YouTube URL is required'
            }), 400

        if not personal_video_thumbnail:
            logger.error("Personal video thumbnail is missing")
            return jsonify({
                'status': 'error',
                'message': 'Personal video thumbnail is required'
            }), 400

        if not s3_client:
            logger.error(
                "S3 client is not initialized. Cannot validate S3 object.")
            return jsonify({
                'status':
                'error',
                'message':
                'S3 connection error. Please try again later.'
            }), 500

        try:
            s3_client.head_object(Bucket=S3_BUCKET, Key=personal_video_s3_key)
        except ClientError as e:
            logger.error(f"Error validating S3 object: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Invalid or inaccessible personal video'
            }), 400

        personal_video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{personal_video_s3_key}"
        logger.debug(f"Personal video URL: {personal_video_url}")

        thumbnail_url = upload_thumbnail_to_s3(personal_video_thumbnail,
                                               personal_video_s3_key)
        if not thumbnail_url:
            logger.error("Failed to upload thumbnail to S3")
            return jsonify({
                'status': 'error',
                'message': 'Failed to upload thumbnail'
            }), 500

        youtube_info = get_youtube_video_info(youtube_url)
        if not youtube_info:
            logger.error("Failed to get YouTube video info")
            return jsonify({
                'status': 'error',
                'message': 'Invalid YouTube URL'
            }), 400

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
        return jsonify({
            'status':
            'error',
            'message':
            f'An error occurred: {str(e)}. Please try again later.'
        }), 500

@app.route('/get_youtube_info')
def get_youtube_info():
    youtube_url = request.args.get('url')
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is required'}), 400

    video_info = get_youtube_video_info(youtube_url)
    if not video_info:
        return jsonify({
            'error':
            'Invalid YouTube URL or unable to fetch video information'
        }), 400

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
            s3_client = None

    logger.info(f"Health check: {health_status}")
    return jsonify(
        health_status), 200 if health_status['status'] == 'healthy' else 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)