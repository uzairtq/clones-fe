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
        'filename': 'simulated_upload.mp4',
        's3Key': 'user-uploads/simulated_upload-12345678-abcd-efgh-ijkl-987654321012.mp4',
        'uploadUrl': 'https://example-bucket.s3.amazonaws.com/user-uploads/simulated_upload-12345678-abcd-efgh-ijkl-987654321012.mp4?AWSAccessKeyId=AKIAIOSFODNN7EXAMPLE&Signature=wJalrXUtnFEMI%2FK7MDENG%2FbPxRfiCYEXAMPLEKEY&Expires=2024-10-16T00:00:00Z'
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
    # Note: This is a simulated upload process and not an actual S3 upload
    personal_video_s3_key = request.form.get('personal_video_s3_key')
    youtube_url = request.form.get('youtube_url')

    if not personal_video_s3_key:
        return jsonify({'status': 'error', 'message': 'Personal video S3 key is required'}), 400

    if not youtube_url:
        return jsonify({'status': 'error', 'message': 'YouTube URL is required'}), 400

    personal_video_url = f"https://example.com/{personal_video_s3_key}"

    # Process reference video (YouTube)
    youtube_info = get_youtube_video_info(youtube_url)
    if not youtube_info:
        return jsonify({'status': 'error', 'message': 'Invalid YouTube URL'}), 400

    # Save video information to database
    new_video = Video(
        personal_video_url=personal_video_url,
        reference_video_url=youtube_url,
        reference_video_title=youtube_info['title'],
        reference_video_thumbnail=youtube_info['thumbnail']
    )
    db.session.add(new_video)
    db.session.commit()

    # TODO: Implement actual video fusion logic
    # For now, we'll just return the personal video URL as the fused video
    fused_video_url = personal_video_url

    return jsonify({
        'status': 'success',
        'message': 'Video processing simulated successfully. Note: This is a simulated process, and no actual S3 upload has occurred.',
        'fused_video_url': fused_video_url
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
