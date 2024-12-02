from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique = True)
    email = db.Column(db.String(50), unique = True)
    password = db.Column(db.String(80))
    # courses = db.relationship('Course', backref='user', lazy=True)
    date_joined = db.Column(db.DateTime, default=datetime.now)

class UserProficiency(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    proficiency_level = db.Column(db.Float, default=0.0)  # might have to be a beginner, mid, expert
    quizzes_taken = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.now)

    # New columns for tracking consecutive performance
    consecutive_successes = db.Column(db.Integer, default=0)
    consecutive_failures = db.Column(db.Integer, default=0)

    @property
    def proficiency_category(self):
        if self.proficiency_level < 30:
            return "Beginner"
        elif self.proficiency_level < 60:
            return "Intermediate"
        else:
            return "Advanced"
    
    @property
    def recommended_quizzes(self):
        base_recommendations = {
            "Beginner": 10,
            "Intermediate": 7,
            "Advanced": 5
        }
        remaining = base_recommendations[self.proficiency_category] - self.quizzes_taken
        return max(0, remaining)
