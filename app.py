import os
import logging
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import ClientError
import psutil
from utils.youtube_api import get_youtube_video_info

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

s3_client = None

def initialize_s3_client():
    global s3_client
    try:
        logger.debug("Initializing S3 client")
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        logger.debug("S3 client initialized successfully")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    logger.debug("Health check initiated")
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
        logger.debug("S3 client not initialized. Attempting to initialize.")
        s3_client = initialize_s3_client()

    if not s3_client:
        logger.error("S3 client initialization failed.")
        health_status['s3_status'] = 'ERROR'
        health_status['status'] = 'unhealthy'
        health_status['s3_error'] = 'S3 client initialization failed'
    else:
        try:
            logger.debug("Attempting to list S3 buckets.")
            s3_client.list_buckets()
            logger.debug("Successfully listed S3 buckets.")
            health_status['s3_status'] = 'OK'
        except ClientError as e:
            logger.error(f"S3 health check failed: {str(e)}")
            health_status['s3_status'] = 'ERROR'
            health_status['status'] = 'unhealthy'
            health_status['s3_error'] = str(e)
            s3_client = None  # Reset the client to force reinitialization on next request

    logger.info(f"Health check result: {health_status}")
    return jsonify(health_status), 200 if health_status['status'] == 'healthy' else 500

@app.route('/get_youtube_info', methods=['GET'])
def get_youtube_info():
    url = request.args.get('url')
    if not url:
        logger.warning("Missing URL parameter in get_youtube_info request")
        return jsonify({'error': 'Missing URL parameter'}), 400

    try:
        logger.debug(f"Fetching YouTube info for URL: {url}")
        video_info = get_youtube_video_info(url)
        if video_info:
            logger.debug(f"Successfully fetched YouTube info: {video_info}")
            return jsonify(video_info)
        else:
            logger.error(f"Failed to fetch YouTube video info for URL: {url}")
            return jsonify({'error': 'Failed to fetch YouTube video info. Please check the URL and try again.'}), 500
    except Exception as e:
        logger.error(f"Error fetching YouTube info: {str(e)}")
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=5000, debug=True)
