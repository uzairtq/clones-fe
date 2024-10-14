from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_video_url = db.Column(db.String(255))
    youtube_url = db.Column(db.String(255))
    youtube_title = db.Column(db.String(255))
    youtube_thumbnail = db.Column(db.String(255))
