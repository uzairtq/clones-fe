import os
import logging
from flask import Flask, render_template, request, jsonify
from models import db, Video
from utils.youtube_api import get_youtube_video_info
from werkzeug.utils import secure_filename
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AWS S3 configuration
S3_BUCKET = os.environ.get('S3_BUCKET')
S3_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')

# Initialize S3 client
s3_client = None
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=S3_REGION
    )
    logger.info("S3 client initialized successfully")
    logger.info(f"AWS_ACCESS_KEY_ID length: {len(os.environ.get('AWS_ACCESS_KEY_ID', ''))}")
    logger.info(f"AWS_SECRET_ACCESS_KEY length: {len(os.environ.get('AWS_SECRET_ACCESS_KEY', ''))}")
    logger.info(f"S3_BUCKET: {S3_BUCKET}")
    logger.info(f"S3_REGION: {S3_REGION}")
except Exception as e:
    logger.error(f"Failed to initialize S3 client: {str(e)}")

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

def test_aws_credentials():
    if not s3_client:
        logger.error("S3 client not initialized")
        return False, "S3 client not initialized"

    try:
        s3_client.list_buckets()
        logger.info("AWS credentials test successful")
        return True, "AWS credentials test successful"
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS credentials test failed: {error_code} - {error_message}")
        return False, f"AWS credentials test failed: {error_code} - {error_message}"
    except Exception as e:
        logger.error(f"AWS credentials test failed: {str(e)}")
        return False, f"AWS credentials test failed: {str(e)}"

def upload_to_s3(file, bucket, s3_file):
    if not s3_client:
        logger.error("S3 client not initialized")
        return None

    try:
        s3_client.upload_fileobj(file, bucket, s3_file)
        logger.info(f"File uploaded successfully to S3: {s3_file}")
        return f"https://{bucket}.s3.{S3_REGION}.amazonaws.com/{s3_file}"
    except NoCredentialsError as e:
        logger.error(f"AWS credentials not found or invalid: {str(e)}")
        return None
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"AWS S3 ClientError: {error_code} - {error_message}")
        return None
    except Exception as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        return None

@app.route('/process_videos', methods=['POST'])
def process_videos():
    aws_creds_test, aws_creds_message = test_aws_credentials()
    if not aws_creds_test:
        return jsonify({'status': 'error', 'message': f'AWS credentials test failed: {aws_creds_message}'}), 500

    personal_video = request.files.get('personal_video')
    reference_video = request.files.get('reference_video')
    youtube_url = request.form.get('youtube_url')

    if not personal_video:
        return jsonify({'status': 'error', 'message': 'Personal video is required'}), 400

    # Upload personal video to S3
    if personal_video.filename:
        personal_video_filename = secure_filename(personal_video.filename)
        s3_personal_video_path = f"personal_videos/{personal_video_filename}"
        personal_video_url = upload_to_s3(personal_video, S3_BUCKET, s3_personal_video_path)

        if not personal_video_url:
            return jsonify({'status': 'error', 'message': 'Failed to upload personal video to S3'}), 500
    else:
        return jsonify({'status': 'error', 'message': 'Invalid personal video file'}), 400

    # Process reference video
    if youtube_url:
        youtube_info = get_youtube_video_info(youtube_url)
        reference_video_url = youtube_url
        reference_video_title = youtube_info['title'] if youtube_info else 'Unknown YouTube Video'
        reference_video_thumbnail = youtube_info['thumbnail'] if youtube_info else None
    elif reference_video:
        if reference_video.filename:
            reference_video_filename = secure_filename(reference_video.filename)
            s3_reference_video_path = f"reference_videos/{reference_video_filename}"
            reference_video_url = upload_to_s3(reference_video, S3_BUCKET, s3_reference_video_path)
            if not reference_video_url:
                return jsonify({'status': 'error', 'message': 'Failed to upload reference video to S3'}), 500
            reference_video_title = reference_video_filename
            reference_video_thumbnail = None
        else:
            return jsonify({'status': 'error', 'message': 'Invalid reference video file'}), 400
    else:
        return jsonify({'status': 'error', 'message': 'Reference video or YouTube URL is required'}), 400

    # Save video information to database
    new_video = Video(
        personal_video_url=personal_video_url,
        reference_video_url=reference_video_url,
        reference_video_title=reference_video_title,
        reference_video_thumbnail=reference_video_thumbnail
    )
    db.session.add(new_video)
    db.session.commit()

    # TODO: Implement actual video fusion logic
    # For now, we'll just return the personal video URL as the fused video
    fused_video_url = personal_video_url

    return jsonify({
        'status': 'success',
        'fused_video_url': fused_video_url
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
