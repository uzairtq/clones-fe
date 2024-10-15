from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_video_url = db.Column(db.String(255))
    reference_video_url = db.Column(db.String(255))
    reference_video_title = db.Column(db.String(255))
    reference_video_thumbnail = db.Column(db.String(255))

class FusedVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_video_url = db.Column(db.String(255), nullable=False)
    reference_video_url = db.Column(db.String(255), nullable=False)
    fused_video_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
