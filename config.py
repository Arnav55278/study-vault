import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'aditya-study-hub-super-secret-key-2024'
    
    # Database
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASEDIR, 'studyvault.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File Upload Settings
    UPLOAD_FOLDER = os.path.join(BASEDIR, 'static', 'uploads')
    AVATAR_FOLDER = os.path.join(BASEDIR, 'static', 'avatars')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'mp4', 'doc', 'docx', 'ppt', 'pptx', 'txt'}
    ALLOWED_AVATAR_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Pagination
    FILES_PER_PAGE = 20
    COMMENTS_PER_PAGE = 10
    
    # App Settings
    APP_NAME = "StudyVault"
    ADMIN_EMAIL = "admin@studyvault.com"
    
    # WhatsApp Channel (APNA LINK DALO)
    WHATSAPP_CHANNEL = "https://whatsapp.com/channel/YOUR_CHANNEL_LINK"
    
    # Categories
    CATEGORIES = [
        ('class_10', 'Class 10'),
        ('class_11', 'Class 11'),
        ('class_12', 'Class 12'),
        ('college', 'College'),
        ('competitive', 'Competitive Exams'),
        ('other', 'Other')
    ]
    
    SUBJECTS = [
        ('maths', 'Mathematics'),
        ('physics', 'Physics'),
        ('chemistry', 'Chemistry'),
        ('biology', 'Biology'),
        ('english', 'English'),
        ('hindi', 'Hindi'),
        ('history', 'History'),
        ('geography', 'Geography'),
        ('economics', 'Economics'),
        ('computer', 'Computer Science'),
        ('other', 'Other')
    ]