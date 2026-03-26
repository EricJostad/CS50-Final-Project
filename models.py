# Standard library
from datetime import datetime

# Third-party libraries
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)


class WatchList(db.Model):
    __tablename__ = 'watch_list'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String, nullable=False)
    watched = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Integer, nullable=True)
    thoughts = db.Column(db.String, nullable=True)

    user = db.relationship("User", backref="watch_list")
