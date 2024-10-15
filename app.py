import os
import logging
import traceback
import boto3
from botocore.exceptions import ClientError
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Video
from utils.youtube_api import get_youtube_video_info
from werkzeug.utils import secure_filename
from uuid import uuid4
from urllib.parse import urlparse

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.urandom(24)  # Add a secret key for session management

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()  # Create all tables

# S3 client configuration
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
)
S3_BUCKET = os.environ.get('S3_BUCKET')

def generate_presigned_url(file_name, file_type):
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registered successfully')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_videos = Video.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', videos=user_videos)

@app.route('/get-upload-url', methods=['POST'])
@login_required
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
@login_required
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

        personal_video_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{personal_video_s3_key}"
        logger.debug(f"Personal video URL: {personal_video_url}")

        # Process reference video (YouTube)
        youtube_info = get_youtube_video_info(youtube_url)
        if not youtube_info:
            logger.error("Failed to get YouTube video info")
            return jsonify({'status': 'error', 'message': 'Invalid YouTube URL'}), 400

        logger.debug(f"YouTube video info: {youtube_info}")

        # Save video information to database
        new_video = Video(
            personal_video_url=personal_video_url,
            reference_video_url=youtube_url,
            reference_video_title=youtube_info['title'],
            reference_video_thumbnail=youtube_info['thumbnail'],
            user_id=current_user.id
        )
        db.session.add(new_video)
        db.session.commit()
        logger.debug("Video information saved to database")

        # TODO: Implement actual video fusion logic
        # For now, we'll just return the personal video URL as the fused video
        fused_video_url = personal_video_url

        logger.debug("Video processing completed successfully")
        return jsonify({
            'status': 'success',
            'message': 'Video processing completed successfully.',
            'fused_video_url': fused_video_url
        })

    except Exception as e:
        logger.error(f"Error processing videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': f'An error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
