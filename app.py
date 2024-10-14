import os
from flask import Flask, render_template, request, jsonify
from models import db, Video
from utils.youtube_api import get_youtube_video_info
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
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
    reference_video = request.files.get('reference_video')
    youtube_url = request.form.get('youtube_url')

    if not personal_video:
        return jsonify({'status': 'error', 'message': 'Personal video is required'}), 400

    # Save personal video
    personal_video_filename = secure_filename(personal_video.filename)
    personal_video_path = os.path.join(app.config['UPLOAD_FOLDER'], personal_video_filename)
    personal_video.save(personal_video_path)
    personal_video_url = f"/uploads/{personal_video_filename}"

    # Process reference video
    if youtube_url:
        youtube_info = get_youtube_video_info(youtube_url)
        reference_video_url = youtube_url
        reference_video_title = youtube_info['title'] if youtube_info else 'Unknown YouTube Video'
        reference_video_thumbnail = youtube_info['thumbnail'] if youtube_info else None
    elif reference_video:
        reference_video_filename = secure_filename(reference_video.filename)
        reference_video_path = os.path.join(app.config['UPLOAD_FOLDER'], reference_video_filename)
        reference_video.save(reference_video_path)
        reference_video_url = f"/uploads/{reference_video_filename}"
        reference_video_title = reference_video_filename
        reference_video_thumbnail = None
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
    # For now, we'll just return a mock response
    fused_video_url = "/uploads/fused_video.mp4"

    return jsonify({
        'status': 'success',
        'fused_video_url': fused_video_url
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
