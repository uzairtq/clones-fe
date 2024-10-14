import os
from flask import Flask, render_template, request, jsonify
from models import db, Video
from utils.youtube_api import get_youtube_video_info

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_videos', methods=['POST'])
def process_videos():
    personal_video = request.files.get('personal_video')
    youtube_url = request.form.get('youtube_url')

    # TODO: Implement video processing logic
    # For now, we'll just return a mock response
    
    if personal_video:
        # Save personal video to S3 (to be implemented)
        personal_video_url = "https://example-s3-bucket.s3.amazonaws.com/personal_video.mp4"
    else:
        personal_video_url = None

    if youtube_url:
        youtube_info = get_youtube_video_info(youtube_url)
    else:
        youtube_info = None

    # Save video information to database
    new_video = Video(
        personal_video_url=personal_video_url,
        youtube_url=youtube_url,
        youtube_title=youtube_info['title'] if youtube_info else None,
        youtube_thumbnail=youtube_info['thumbnail'] if youtube_info else None
    )
    db.session.add(new_video)
    db.session.commit()

    # Mock response for fused video
    fused_video_url = "https://example-s3-bucket.s3.amazonaws.com/fused_video.mp4"

    return jsonify({
        'status': 'success',
        'fused_video_url': fused_video_url
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
