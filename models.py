from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    personal_video_url = db.Column(db.String(255))
    reference_video_url = db.Column(db.String(255))
    reference_video_title = db.Column(db.String(255))
    reference_video_thumbnail = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('videos', lazy=True))
