import os
import logging
from flask import Flask, render_template, request, jsonify
from models import db, Video
from utils.youtube_api import get_youtube_video_info
from werkzeug.utils import secure_filename
from uuid import uuid4
from urllib.parse import urlparse

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db.init_app(app)

with app.app_context():
    db.drop_all()  # Drop all existing tables
    db.create_all()  # Recreate all tables

def get_dummy_presigned_url():
    return {
        "filename": "ad_v02.mp4",
        "s3Key": "user-uploads/ad_v02-50c8000e-eb01-4f09-9810-53ff94959c89.mp4",
        "uploadUrl": "https://clones-main.s3-accelerate.amazonaws.com/studio/670e67896360db8d4102b742/user-uploads/ad_v02-50c8000e-eb01-4f09-9810-53ff94959c89.mp4?AWSAccessKeyId=AKIAQE43KLS4A2UB4LIT&Signature=vUKEx6YilRNopt%2FqnJFtyltdSxE%3D&content-type=video%2Fmp4&Expires=1729001167"
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get-upload-url', methods=['POST'])
def get_upload_url():
    file_name = request.json.get('fileName')
    file_type = request.json.get('fileType')

    if not file_name or not file_type:
        return jsonify({'status': 'error', 'message': 'File name and type are required'}), 400

    dummy_data = get_dummy_presigned_url()
    return jsonify({
        'status': 'success',
        'filename': dummy_data['filename'],
        's3Key': dummy_data['s3Key'],
        'uploadUrl': dummy_data['uploadUrl']
    })

@app.route('/process_videos', methods=['POST'])
def process_videos():
    personal_video_s3_key = request.form.get('personal_video_s3_key')
    reference_video_s3_key = request.form.get('reference_video_s3_key')
    youtube_url = request.form.get('youtube_url')

    if not personal_video_s3_key:
        return jsonify({'status': 'error', 'message': 'Personal video S3 key is required'}), 400

    personal_video_url = f"https://example.com/{personal_video_s3_key}"

    # Process reference video
    if youtube_url:
        youtube_info = get_youtube_video_info(youtube_url)
        reference_video_url = youtube_url
        reference_video_title = youtube_info['title'] if youtube_info else 'Unknown YouTube Video'
        reference_video_thumbnail = youtube_info['thumbnail'] if youtube_info else None
    elif reference_video_s3_key:
        reference_video_url = f"https://example.com/{reference_video_s3_key}"
        reference_video_title = os.path.basename(reference_video_s3_key)
        reference_video_thumbnail = None
    else:
        return jsonify({'status': 'error', 'message': 'Reference video S3 key or YouTube URL is required'}), 400

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
