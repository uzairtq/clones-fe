from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_video_url = db.Column(db.String(255))
    reference_video_url = db.Column(db.String(255))
    reference_video_title = db.Column(db.String(255))
    reference_video_thumbnail = db.Column(db.String(255))
