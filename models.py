from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

db = SQLAlchemy()

# ============== USER MODEL ==============
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Profile Info
    full_name = db.Column(db.String(150), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    avatar = db.Column(db.String(300), default='default.png')
    location = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    
    # Social Links
    instagram = db.Column(db.String(100), nullable=True)
    twitter = db.Column(db.String(100), nullable=True)
    youtube = db.Column(db.String(200), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Password Reset
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    folders = db.relationship('Folder', backref='owner', lazy='dynamic', foreign_keys='Folder.owner_id')
    files = db.relationship('File', backref='uploader', lazy='dynamic', foreign_keys='File.uploaded_by')
    favourites = db.relationship('Favourite', backref='user', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    ratings = db.relationship('Rating', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expiry = datetime.utcnow() + timedelta(hours=24)
        return self.reset_token
    
    def get_total_uploads(self):
        return self.files.count()
    
    def get_total_downloads(self):
        return sum(f.download_count for f in self.files)
    
    def get_total_storage_used(self):
        return sum(f.size for f in self.files)
    
    def get_unread_notifications_count(self):
        return self.notifications.filter_by(is_read=False).count()
    
    def __repr__(self):
        return f'<User {self.username}>'


# ============== CATEGORY MODEL ==============
class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(50), default='bi-folder')
    color = db.Column(db.String(20), default='primary')
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Relationships
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    folders = db.relationship('Folder', backref='category', lazy='dynamic')
    
    def get_folder_count(self):
        return self.folders.count()
    
    def __repr__(self):
        return f'<Category {self.name}>'


# ============== FOLDER MODEL ==============
class Folder(db.Model):
    __tablename__ = 'folders'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Hierarchy
    parent_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Settings
    is_public = db.Column(db.Boolean, default=False)
    is_featured = db.Column(db.Boolean, default=False)
    password = db.Column(db.String(256), nullable=True)
    
    # Metadata
    subject = db.Column(db.String(50), nullable=True)
    class_level = db.Column(db.String(50), nullable=True)
    
    # Stats
    view_count = db.Column(db.Integer, default=0)
    
    # Share Link
    share_token = db.Column(db.String(50), unique=True, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    children = db.relationship('Folder', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    files = db.relationship('File', backref='folder', lazy='dynamic', cascade='all, delete-orphan')
    
    def generate_share_token(self):
        self.share_token = secrets.token_urlsafe(16)
        return self.share_token
    
    def set_password(self, password):
        if password:
            self.password = generate_password_hash(password)
        else:
            self.password = None
    
    def check_password(self, password):
        if not self.password:
            return True
        return check_password_hash(self.password, password)
    
    def get_path(self):
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return '/'.join(path)
    
    def get_all_subfolders(self):
        subfolders = []
        for child in self.children:
            subfolders.append(child)
            subfolders.extend(child.get_all_subfolders())
        return subfolders
    
    def get_star_count(self):
        return Favourite.query.filter_by(folder_id=self.id).count()
    
    def get_total_files(self):
        count = self.files.count()
        for subfolder in self.children:
            count += subfolder.get_total_files()
        return count
    
    def get_total_size(self):
        size = sum(f.size for f in self.files)
        for subfolder in self.children:
            size += subfolder.get_total_size()
        return size
    
    def __repr__(self):
        return f'<Folder {self.name}>'


# ============== FILE MODEL ==============
class File(db.Model):
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)
    stored_filename = db.Column(db.String(300), nullable=False, unique=True)
    file_type = db.Column(db.String(20), nullable=False)
    mime_type = db.Column(db.String(100), nullable=True)
    
    # Metadata
    description = db.Column(db.Text, nullable=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    size = db.Column(db.BigInteger, nullable=False)
    
    # Stats
    download_count = db.Column(db.Integer, default=0)
    view_count = db.Column(db.Integer, default=0)
    
    # Share
    share_token = db.Column(db.String(50), unique=True, nullable=True)
    
    # Timestamps
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    comments = db.relationship('Comment', backref='file', lazy='dynamic', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='file', lazy='dynamic', cascade='all, delete-orphan')
    tags = db.relationship('Tag', secondary='file_tags', backref='files', lazy='dynamic')
    
    def generate_share_token(self):
        self.share_token = secrets.token_urlsafe(16)
        return self.share_token
    
    def get_size_formatted(self):
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def get_icon(self):
        icons = {
            'pdf': 'bi-file-earmark-pdf text-danger',
            'image': 'bi-file-earmark-image text-success',
            'audio': 'bi-file-earmark-music text-warning',
            'video': 'bi-file-earmark-play text-primary',
            'document': 'bi-file-earmark-word text-info',
            'presentation': 'bi-file-earmark-ppt text-orange',
            'text': 'bi-file-earmark-text text-secondary'
        }
        return icons.get(self.file_type, 'bi-file-earmark text-secondary')
    
    def get_star_count(self):
        return Favourite.query.filter_by(file_id=self.id).count()
    
    def get_average_rating(self):
        ratings = self.ratings.all()
        if not ratings:
            return 0
        return sum(r.rating for r in ratings) / len(ratings)
    
    def get_rating_count(self):
        return self.ratings.count()
    
    def get_comments_count(self):
        return self.comments.count()
    
    def __repr__(self):
        return f'<File {self.filename}>'


# ============== TAG MODEL ==============
class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tag {self.name}>'


# File-Tag Association Table
file_tags = db.Table('file_tags',
    db.Column('file_id', db.Integer, db.ForeignKey('files.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


# ============== COMMENT MODEL ==============
class Comment(db.Model):
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    
    # References
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    
    # Status
    is_approved = db.Column(db.Boolean, default=True)
    is_edited = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Replies
    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')
    
    def __repr__(self):
        return f'<Comment {self.id}>'


# ============== RATING MODEL ==============
class Rating(db.Model):
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    
    # References
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('file_id', 'user_id', name='unique_file_rating'),
    )
    
    def __repr__(self):
        return f'<Rating {self.rating} for File {self.file_id}>'


# ============== FAVOURITE MODEL ==============
class Favourite(db.Model):
    __tablename__ = 'favourites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    item_type = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    file = db.relationship('File', backref='favourited_by')
    folder = db.relationship('Folder', backref='favourited_by')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'file_id', 'folder_id', name='unique_favourite'),
    )


# ============== NOTIFICATION MODEL ==============
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Content
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(300), nullable=True)
    icon = db.Column(db.String(50), default='bi-bell')
    
    # Type
    notification_type = db.Column(db.String(50), default='system')
    
    # Status
    is_read = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.title}>'


# ============== REPORT MODEL (FIXED!) ==============
class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Reporter - EXPLICITLY DEFINE FOREIGN KEY
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # What's being reported
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # RENAMED!
    
    # Report Details
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Status
    status = db.Column(db.String(20), default='pending')
    admin_notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # EXPLICIT RELATIONSHIPS WITH FOREIGN_KEYS SPECIFIED
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='reports_made')
    reported_user = db.relationship('User', foreign_keys=[reported_user_id], backref='reports_against')
    
    reported_file = db.relationship('File', backref='reports')
    reported_folder = db.relationship('Folder', backref='reports')
    reported_comment = db.relationship('Comment', backref='reports')
    
    def __repr__(self):
        return f'<Report {self.id}>'


# ============== ACTIVITY LOG MODEL ==============
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Activity Details
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # References
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=True)
    folder_id = db.Column(db.Integer, db.ForeignKey('folders.id'), nullable=True)
    
    # Extra Info
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(300), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='activities')
    
    def __repr__(self):
        return f'<ActivityLog {self.action}>'


# ============== ANNOUNCEMENT MODEL ==============
class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Type
    announcement_type = db.Column(db.String(20), default='info')
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_pinned = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


# ============== DOWNLOAD HISTORY MODEL ==============
class DownloadHistory(db.Model):
    __tablename__ = 'download_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False)
    
    # Info
    ip_address = db.Column(db.String(50), nullable=True)
    
    # Timestamps
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='downloads')
    file = db.relationship('File', backref='download_history')
    
    def __repr__(self):
        return f'<Download {self.file_id}>'