import os
import uuid
import re
from werkzeug.utils import secure_filename
from datetime import datetime
from functools import wraps
from flask import current_app, abort, request
from flask_login import current_user

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'mp3', 'mp4', 'doc', 'docx', 'ppt', 'pptx', 'txt'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    """Determine file type category"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext == 'pdf':
        return 'pdf'
    elif ext in ['jpg', 'jpeg', 'png', 'gif']:
        return 'image'
    elif ext == 'mp3':
        return 'audio'
    elif ext == 'mp4':
        return 'video'
    elif ext in ['doc', 'docx']:
        return 'document'
    elif ext in ['ppt', 'pptx']:
        return 'presentation'
    elif ext == 'txt':
        return 'text'
    return 'unknown'

def get_mime_type(filename):
    """Get MIME type of file"""
    ext = filename.rsplit('.', 1)[1].lower()
    mime_types = {
        'pdf': 'application/pdf',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'mp3': 'audio/mpeg',
        'mp4': 'video/mp4',
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'ppt': 'application/vnd.ms-powerpoint',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'txt': 'text/plain'
    }
    return mime_types.get(ext, 'application/octet-stream')

def generate_unique_filename(original_filename):
    """Generate unique filename while preserving extension"""
    ext = original_filename.rsplit('.', 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    return unique_name

def save_file(file, upload_folder):
    """Save file and return stored filename and size"""
    original_filename = secure_filename(file.filename)
    stored_filename = generate_unique_filename(original_filename)
    filepath = os.path.join(upload_folder, stored_filename)
    
    os.makedirs(upload_folder, exist_ok=True)
    
    file.save(filepath)
    file_size = os.path.getsize(filepath)
    
    return stored_filename, file_size

def delete_file(stored_filename, upload_folder):
    """Delete file from storage"""
    filepath = os.path.join(upload_folder, stored_filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text

def build_folder_tree(folders, parent_id=None):
    """Build hierarchical folder tree structure for jsTree"""
    tree = []
    for folder in folders:
        if folder.parent_id == parent_id:
            children = build_folder_tree(folders, folder.id)
            node = {
                'id': folder.id,
                'text': folder.name,
                'icon': 'bi bi-folder-fill text-warning' if not folder.is_public else 'bi bi-folder2-open text-success',
                'state': {'opened': False},
                'children': children,
                'a_attr': {'href': f'/folder/{folder.id}'}
            }
            tree.append(node)
    return tree

def get_folder_choices(user_id, exclude_id=None):
    """Get folder choices for select field"""
    from models import Folder
    folders = Folder.query.filter_by(owner_id=user_id).all()
    choices = [(0, '-- Root (No Parent) --')]
    
    exclude_ids = []
    if exclude_id:
        folder = Folder.query.get(exclude_id)
        if folder:
            exclude_ids = [exclude_id] + [f.id for f in folder.get_all_subfolders()]
    
    def add_choices(folder, level=0):
        if folder.id not in exclude_ids:
            prefix = '—' * level + ' ' if level > 0 else ''
            choices.append((folder.id, prefix + folder.name))
            for child in folder.children:
                add_choices(child, level + 1)
    
    root_folders = [f for f in folders if f.parent_id is None]
    for folder in root_folders:
        add_choices(folder)
    
    return choices

def get_category_choices():
    """Get category choices for select field"""
    from models import Category
    categories = Category.query.all()
    choices = [(0, '-- Select Category --')]
    for cat in categories:
        choices.append((cat.id, cat.name))
    return choices

def format_datetime(dt):
    """Format datetime for display"""
    if not dt:
        return ''
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days == 0:
        if diff.seconds < 60:
            return 'Just now'
        elif diff.seconds < 3600:
            minutes = diff.seconds // 60
            return f'{minutes} min ago'
        else:
            hours = diff.seconds // 3600
            return f'{hours} hr ago'
    elif diff.days == 1:
        return 'Yesterday'
    elif diff.days < 7:
        return f'{diff.days} days ago'
    else:
        return dt.strftime('%d %b %Y')

def format_number(num):
    """Format large numbers (1000 -> 1K, etc.)"""
    if num >= 1000000:
        return f'{num/1000000:.1f}M'
    elif num >= 1000:
        return f'{num/1000:.1f}K'
    return str(num)

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def log_activity(user_id, action, description=None, file_id=None, folder_id=None):
    """Log user activity"""
    from models import db, ActivityLog
    
    log = ActivityLog(
        user_id=user_id,
        action=action,
        description=description,
        file_id=file_id,
        folder_id=folder_id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:300] if request.user_agent.string else None
    )
    db.session.add(log)
    db.session.commit()

def create_notification(user_id, title, message, link=None, notification_type='system', icon='bi-bell'):
    """Create a notification for user"""
    from models import db, Notification
    
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        notification_type=notification_type,
        icon=icon
    )
    db.session.add(notification)
    db.session.commit()

def parse_tags(tags_string):
    """Parse comma-separated tags string"""
    if not tags_string:
        return []
    tags = [tag.strip().lower() for tag in tags_string.split(',')]
    return [tag for tag in tags if tag and len(tag) <= 50]

def get_or_create_tag(tag_name):
    """Get existing tag or create new one"""
    from models import db, Tag
    
    slug = slugify(tag_name)
    tag = Tag.query.filter_by(slug=slug).first()
    if not tag:
        tag = Tag(name=tag_name, slug=slug)
        db.session.add(tag)
        db.session.commit()
    return tag

def get_leaderboard(limit=10):
    """Get top uploaders leaderboard"""
    from models import db, User, File
    
    leaderboard = db.session.query(
        User,
        db.func.count(File.id).label('upload_count'),
        db.func.sum(File.download_count).label('total_downloads')
    ).join(File, User.id == File.uploaded_by)\
     .group_by(User.id)\
     .order_by(db.desc('total_downloads'))\
     .limit(limit).all()
    
    return leaderboard

def get_popular_tags(limit=20):
    """Get most popular tags"""
    from models import db, Tag, file_tags
    
    popular = db.session.query(
        Tag,
        db.func.count(file_tags.c.file_id).label('count')
    ).join(file_tags)\
     .group_by(Tag.id)\
     .order_by(db.desc('count'))\
     .limit(limit).all()
    
    return popular

def get_stats():
    """Get overall platform statistics"""
    from models import User, File, Folder, DownloadHistory
    
    return {
        'total_users': User.query.count(),
        'total_files': File.query.count(),
        'total_folders': Folder.query.filter_by(is_public=True).count(),
        'total_downloads': DownloadHistory.query.count()
    }