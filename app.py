import os
from flask import (Flask, render_template, redirect, url_for, flash, request, 
                   send_from_directory, abort, jsonify, session)
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from functools import wraps

from config import Config
from models import (db, User, Folder, File, Favourite, Comment, Rating, 
                   Notification, Report, ActivityLog, Category, Tag, 
                   DownloadHistory, Announcement, file_tags)
from forms import (RegistrationForm, LoginForm, FolderForm, UploadForm, 
                  SearchForm, CommentForm, RatingForm, ProfileForm, 
                  ReportForm, ForgotPasswordForm, ResetPasswordForm,
                  ChangePasswordForm, AvatarForm, FileEditForm,
                  CategoryForm, AnnouncementForm, AdvancedSearchForm,
                  FolderPasswordForm, UserEditForm)
from utils import (allowed_file, get_file_type, get_mime_type, save_file, 
                  delete_file, build_folder_tree, get_folder_choices,
                  get_category_choices, format_datetime, format_number,
                  admin_required, log_activity, create_notification,
                  parse_tags, get_or_create_tag, slugify, get_leaderboard,
                  get_popular_tags, get_stats)

# ============== APP SETUP ==============
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and folders
with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['AVATAR_FOLDER'], exist_ok=True)
    
    # Create default categories
    if Category.query.count() == 0:
        default_categories = [
            Category(name='Class 10', slug='class-10', icon='bi-book', color='primary'),
            Category(name='Class 11', slug='class-11', icon='bi-book', color='success'),
            Category(name='Class 12', slug='class-12', icon='bi-book', color='info'),
            Category(name='College', slug='college', icon='bi-mortarboard', color='warning'),
            Category(name='Competitive Exams', slug='competitive', icon='bi-trophy', color='danger'),
            Category(name='Other', slug='other', icon='bi-folder', color='secondary'),
        ]
        for cat in default_categories:
            db.session.add(cat)
        db.session.commit()


# ============== CONTEXT PROCESSORS ==============
@app.context_processor
def utility_processor():
    def get_unread_count():
        if current_user.is_authenticated:
            return current_user.get_unread_notifications_count()
        return 0
    
    def get_announcements():
        return Announcement.query.filter_by(is_active=True).order_by(Announcement.is_pinned.desc(), Announcement.created_at.desc()).limit(3).all()
    
    return dict(
        format_datetime=format_datetime,
        format_number=format_number,
        get_unread_count=get_unread_count,
        get_announcements=get_announcements,
        whatsapp_link=app.config.get('WHATSAPP_CHANNEL', '#'),
        app_name=app.config.get('APP_NAME', 'StudyVault'),
        current_year=datetime.now().year
    )


# ============== HOMEPAGE ==============
@app.route('/')
def index():
    # Popular public folders
    popular_folders = Folder.query.filter_by(is_public=True)\
        .order_by(Folder.view_count.desc()).limit(8).all()
    
    # Recent files
    recent_files = File.query.join(Folder).filter(Folder.is_public == True)\
        .order_by(File.uploaded_at.desc()).limit(12).all()
    
    # Featured folders
    featured_folders = Folder.query.filter_by(is_public=True, is_featured=True).limit(4).all()
    
    # Categories
    categories = Category.query.all()
    
    # Stats
    stats = get_stats()
    
    # Leaderboard
    leaderboard = get_leaderboard(5)
    
    return render_template('index.html',
                         popular_folders=popular_folders,
                         recent_files=recent_files,
                         featured_folders=featured_folders,
                         categories=categories,
                         stats=stats,
                         leaderboard=leaderboard)


# ============== AUTHENTICATION ==============
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower()
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Log activity
        log_activity(user.id, 'register', 'New user registered')
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated.', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_activity(user.id, 'login', 'User logged in')
            
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    log_activity(current_user.id, 'logout', 'User logged out')
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            # In production, send email with reset link
            # For now, show the token
            flash(f'Password reset link: /reset-password/{token}', 'info')
        else:
            flash('If email exists, reset link has been sent.', 'info')
        return redirect(url_for('login'))
    
    return render_template('forgot_password.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    if not user or (user.reset_token_expiry and user.reset_token_expiry < datetime.utcnow()):
        flash('Invalid or expired reset link.', 'danger')
        return redirect(url_for('login'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Password reset successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', form=form)


# ============== DASHBOARD ==============
@app.route('/dashboard')
@login_required
def dashboard():
    my_folders = Folder.query.filter_by(owner_id=current_user.id, parent_id=None).all()
    all_folders = Folder.query.filter_by(owner_id=current_user.id).all()
    folder_tree = build_folder_tree(all_folders)
    
    recent_uploads = File.query.filter_by(uploaded_by=current_user.id)\
        .order_by(File.uploaded_at.desc()).limit(10).all()
    
    # Stats
    total_files = File.query.filter_by(uploaded_by=current_user.id).count()
    total_folders = Folder.query.filter_by(owner_id=current_user.id).count()
    total_downloads = current_user.get_total_downloads()
    storage_used = current_user.get_total_storage_used()
    
    # Recent notifications
    notifications = current_user.notifications.order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         my_folders=my_folders,
                         folder_tree=folder_tree,
                         recent_uploads=recent_uploads,
                         total_files=total_files,
                         total_folders=total_folders,
                         total_downloads=total_downloads,
                         storage_used=storage_used,
                         notifications=notifications)


# ============== PROFILE ==============
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    avatar_form = AvatarForm()
    password_form = ChangePasswordForm()
    
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data
        current_user.bio = form.bio.data
        current_user.location = form.location.data
        current_user.website = form.website.data
        current_user.instagram = form.instagram.data
        current_user.twitter = form.twitter.data
        current_user.youtube = form.youtube.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    uploads = File.query.filter_by(uploaded_by=current_user.id)\
        .order_by(File.uploaded_at.desc()).all()
    
    fav_files = Favourite.query.filter_by(user_id=current_user.id, item_type='file').all()
    fav_folders = Favourite.query.filter_by(user_id=current_user.id, item_type='folder').all()
    
    total_storage = current_user.get_total_storage_used()
    total_downloads = current_user.get_total_downloads()
    
    return render_template('profile.html',
                         form=form,
                         avatar_form=avatar_form,
                         password_form=password_form,
                         uploads=uploads,
                         fav_files=fav_files,
                         fav_folders=fav_folders,
                         total_storage=total_storage,
                         total_downloads=total_downloads)


@app.route('/profile/avatar', methods=['POST'])
@login_required
def update_avatar():
    form = AvatarForm()
    if form.validate_on_submit():
        file = form.avatar.data
        if file and allowed_file(file.filename):
            # Delete old avatar if not default
            if current_user.avatar != 'default.png':
                old_path = os.path.join(app.config['AVATAR_FOLDER'], current_user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Save new avatar
            filename = f"{current_user.id}_{secure_filename(file.filename)}"
            filepath = os.path.join(app.config['AVATAR_FOLDER'], filename)
            file.save(filepath)
            
            current_user.avatar = filename
            db.session.commit()
            flash('Avatar updated!', 'success')
    
    return redirect(url_for('profile'))


@app.route('/profile/password', methods=['POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Password changed successfully!', 'success')
        else:
            flash('Current password is incorrect.', 'danger')
    
    return redirect(url_for('profile'))


@app.route('/user/<username>')
def public_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    public_folders = Folder.query.filter_by(owner_id=user.id, is_public=True).all()
    
    # Stats
    total_uploads = user.get_total_uploads()
    total_downloads = user.get_total_downloads()
    
    return render_template('public_profile.html',
                         profile_user=user,
                         public_folders=public_folders,
                         total_uploads=total_uploads,
                         total_downloads=total_downloads)


# ============== FOLDERS ==============
@app.route('/folder/create', methods=['GET', 'POST'])
@login_required
def create_folder():
    form = FolderForm()
    form.parent_id.choices = get_folder_choices(current_user.id)
    form.category_id.choices = get_category_choices()
    
    if form.validate_on_submit():
        folder = Folder(
            name=form.name.data,
            slug=slugify(form.name.data),
            description=form.description.data,
            owner_id=current_user.id,
            is_public=form.is_public.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            category_id=form.category_id.data if form.category_id.data != 0 else None,
            class_level=form.class_level.data if form.class_level.data else None,
            subject=form.subject.data if form.subject.data else None
        )
        
        if form.folder_password.data:
            folder.set_password(form.folder_password.data)
        
        folder.generate_share_token()
        db.session.add(folder)
        db.session.commit()
        
        log_activity(current_user.id, 'create_folder', f'Created folder: {folder.name}', folder_id=folder.id)
        
        flash(f'Folder "{folder.name}" created!', 'success')
        return redirect(url_for('folder_view', folder_id=folder.id))
    
    return render_template('create_folder.html', form=form)


@app.route('/folder/<int:folder_id>')
def folder_view(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    
    # Check access
    if not folder.is_public:
        if not current_user.is_authenticated or folder.owner_id != current_user.id:
            flash('This folder is private.', 'warning')
            return redirect(url_for('index'))
    
    # Check password protection
    if folder.password and not session.get(f'folder_access_{folder_id}'):
        if not current_user.is_authenticated or folder.owner_id != current_user.id:
            return redirect(url_for('folder_password', folder_id=folder_id))
    
    # Increment view count
    folder.view_count += 1
    db.session.commit()
    
    # Get contents
    subfolders = Folder.query.filter_by(parent_id=folder_id).all()
    files = File.query.filter_by(folder_id=folder_id).order_by(File.uploaded_at.desc()).all()
    
    # Breadcrumb
    breadcrumb = []
    current = folder
    while current:
        breadcrumb.insert(0, current)
        current = current.parent
    
    # Check if starred
    is_starred = False
    if current_user.is_authenticated:
        is_starred = Favourite.query.filter_by(
            user_id=current_user.id,
            folder_id=folder_id
        ).first() is not None
    
    return render_template('folder.html',
                         folder=folder,
                         subfolders=subfolders,
                         files=files,
                         breadcrumb=breadcrumb,
                         is_starred=is_starred)


@app.route('/folder/<int:folder_id>/password', methods=['GET', 'POST'])
def folder_password(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    
    if not folder.password:
        return redirect(url_for('folder_view', folder_id=folder_id))
    
    form = FolderPasswordForm()
    if form.validate_on_submit():
        if folder.check_password(form.password.data):
            session[f'folder_access_{folder_id}'] = True
            return redirect(url_for('folder_view', folder_id=folder_id))
        else:
            flash('Incorrect password.', 'danger')
    
    return render_template('folder_password.html', form=form, folder=folder)


@app.route('/folder/<int:folder_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    
    if folder.owner_id != current_user.id:
        abort(403)
    
    form = FolderForm(obj=folder)
    form.parent_id.choices = get_folder_choices(current_user.id, exclude_id=folder_id)
    form.category_id.choices = get_category_choices()
    
    if form.validate_on_submit():
        folder.name = form.name.data
        folder.slug = slugify(form.name.data)
        folder.description = form.description.data
        folder.is_public = form.is_public.data
        folder.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        folder.category_id = form.category_id.data if form.category_id.data != 0 else None
        folder.class_level = form.class_level.data if form.class_level.data else None
        folder.subject = form.subject.data if form.subject.data else None
        
        if form.folder_password.data:
            folder.set_password(form.folder_password.data)
        
        db.session.commit()
        flash('Folder updated!', 'success')
        return redirect(url_for('folder_view', folder_id=folder_id))
    
    form.parent_id.data = folder.parent_id if folder.parent_id else 0
    form.category_id.data = folder.category_id if folder.category_id else 0
    
    return render_template('edit_folder.html', form=form, folder=folder)


@app.route('/folder/<int:folder_id>/delete', methods=['POST'])
@login_required
def delete_folder(folder_id):
    folder = Folder.query.get_or_404(folder_id)
    
    if folder.owner_id != current_user.id:
        abort(403)
    
    # Delete all files
    for file in folder.files:
        delete_file(file.stored_filename, app.config['UPLOAD_FOLDER'])
        db.session.delete(file)
    
    # Delete subfolders recursively
    for subfolder in folder.get_all_subfolders():
        for file in subfolder.files:
            delete_file(file.stored_filename, app.config['UPLOAD_FOLDER'])
            db.session.delete(file)
        db.session.delete(subfolder)
    
    # Delete favourites
    Favourite.query.filter_by(folder_id=folder_id).delete()
    
    log_activity(current_user.id, 'delete_folder', f'Deleted folder: {folder.name}')
    
    db.session.delete(folder)
    db.session.commit()
    
    flash('Folder deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/share/folder/<token>')
def shared_folder(token):
    folder = Folder.query.filter_by(share_token=token).first_or_404()
    
    if folder.password and not session.get(f'folder_access_{folder.id}'):
        return redirect(url_for('folder_password', folder_id=folder.id))
    
    folder.view_count += 1
    db.session.commit()
    
    subfolders = Folder.query.filter_by(parent_id=folder.id).all()
    files = File.query.filter_by(folder_id=folder.id).order_by(File.uploaded_at.desc()).all()
    
    return render_template('shared_folder.html', folder=folder, subfolders=subfolders, files=files)


# ============== FILES ==============
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_files():
    form = UploadForm()
    form.folder_id.choices = [(f.id, f.get_path()) for f in 
                              Folder.query.filter_by(owner_id=current_user.id).all()]
    
    if not form.folder_id.choices:
        flash('Please create a folder first!', 'warning')
        return redirect(url_for('create_folder'))
    
    if form.validate_on_submit():
        folder_id = form.folder_id.data
        files = request.files.getlist('files')
        tags_string = form.tags.data
        description = form.description.data
        
        uploaded_count = 0
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                try:
                    original_filename = secure_filename(file.filename)
                    stored_filename, file_size = save_file(file, app.config['UPLOAD_FOLDER'])
                    
                    new_file = File(
                        filename=original_filename,
                        stored_filename=stored_filename,
                        file_type=get_file_type(original_filename),
                        mime_type=get_mime_type(original_filename),
                        folder_id=folder_id,
                        uploaded_by=current_user.id,
                        size=file_size,
                        description=description
                    )
                    new_file.generate_share_token()
                    db.session.add(new_file)
                    db.session.flush()  # Get the file ID
                    
                    # Add tags
                    if tags_string:
                        for tag_name in parse_tags(tags_string):
                            tag = get_or_create_tag(tag_name)
                            new_file.tags.append(tag)
                    
                    uploaded_count += 1
                    
                    log_activity(current_user.id, 'upload', f'Uploaded: {original_filename}', file_id=new_file.id)
                    
                except Exception as e:
                    flash(f'Error uploading {file.filename}: {str(e)}', 'danger')
        
        db.session.commit()
        
        if uploaded_count > 0:
            flash(f'Successfully uploaded {uploaded_count} file(s)!', 'success')
            return redirect(url_for('folder_view', folder_id=folder_id))
        else:
            flash('No valid files uploaded.', 'warning')
    
    return render_template('upload.html', form=form)


@app.route('/file/<int:file_id>')
def file_view(file_id):
    file = File.query.get_or_404(file_id)
    folder = file.folder
    
    # Check access
    if not folder.is_public:
        if not current_user.is_authenticated or folder.owner_id != current_user.id:
            abort(403)
    
    # Increment view count
    file.view_count += 1
    db.session.commit()
    
    # Comments
    comments = file.comments.filter_by(parent_id=None).order_by(Comment.created_at.desc()).all()
    comment_form = CommentForm()
    
    # Rating
    rating_form = RatingForm()
    user_rating = None
    if current_user.is_authenticated:
        user_rating = Rating.query.filter_by(file_id=file_id, user_id=current_user.id).first()
    
    # Check if starred
    is_starred = False
    if current_user.is_authenticated:
        is_starred = Favourite.query.filter_by(
            user_id=current_user.id,
            file_id=file_id
        ).first() is not None
    
    return render_template('file_view.html',
                         file=file,
                         folder=folder,
                         comments=comments,
                         comment_form=comment_form,
                         rating_form=rating_form,
                         user_rating=user_rating,
                         is_starred=is_starred)


@app.route('/file/<int:file_id>/download')
def download_file(file_id):
    file = File.query.get_or_404(file_id)
    folder = file.folder
    
    # Check access
    if not folder.is_public:
        if not current_user.is_authenticated or folder.owner_id != current_user.id:
            abort(403)
    
    # Increment download count
    file.download_count += 1
    
    # Log download
    download_record = DownloadHistory(
        user_id=current_user.id if current_user.is_authenticated else None,
        file_id=file_id,
        ip_address=request.remote_addr
    )
    db.session.add(download_record)
    db.session.commit()
    
    # Notify uploader
    if current_user.is_authenticated and file.uploaded_by != current_user.id:
        create_notification(
            file.uploaded_by,
            'File Downloaded',
            f'{current_user.username} downloaded your file "{file.filename}"',
            url_for('file_view', file_id=file_id),
            'download',
            'bi-download'
        )
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        file.stored_filename,
        as_attachment=True,
        download_name=file.filename
    )


@app.route('/file/<int:file_id>/preview')
def preview_file(file_id):
    file = File.query.get_or_404(file_id)
    folder = file.folder
    
    if not folder.is_public:
        if not current_user.is_authenticated or folder.owner_id != current_user.id:
            abort(403)
    
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        file.stored_filename,
        as_attachment=False
    )


@app.route('/file/<int:file_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_file(file_id):
    file = File.query.get_or_404(file_id)
    
    if file.uploaded_by != current_user.id:
        abort(403)
    
    form = FileEditForm(obj=file)
    
    if request.method == 'GET':
        form.tags.data = ', '.join([tag.name for tag in file.tags])
    
    if form.validate_on_submit():
        file.filename = form.filename.data
        file.description = form.description.data
        
        # Update tags
        file.tags = []
        if form.tags.data:
            for tag_name in parse_tags(form.tags.data):
                tag = get_or_create_tag(tag_name)
                file.tags.append(tag)
        
        db.session.commit()
        flash('File updated!', 'success')
        return redirect(url_for('file_view', file_id=file_id))
    
    return render_template('edit_file.html', form=form, file=file)


@app.route('/file/<int:file_id>/delete', methods=['POST'])
@login_required
def delete_file_route(file_id):
    file = File.query.get_or_404(file_id)
    
    if file.uploaded_by != current_user.id and not current_user.is_admin:
        abort(403)
    
    folder_id = file.folder_id
    
    # Delete physical file
    delete_file(file.stored_filename, app.config['UPLOAD_FOLDER'])
    
    # Delete related data
    Comment.query.filter_by(file_id=file_id).delete()
    Rating.query.filter_by(file_id=file_id).delete()
    Favourite.query.filter_by(file_id=file_id).delete()
    DownloadHistory.query.filter_by(file_id=file_id).delete()
    
    log_activity(current_user.id, 'delete_file', f'Deleted: {file.filename}')
    
    db.session.delete(file)
    db.session.commit()
    
    flash('File deleted.', 'success')
    return redirect(url_for('folder_view', folder_id=folder_id))


@app.route('/share/file/<token>')
def shared_file(token):
    file = File.query.filter_by(share_token=token).first_or_404()
    
    file.view_count += 1
    db.session.commit()
    
    return render_template('shared_file.html', file=file)


# ============== COMMENTS ==============
@app.route('/file/<int:file_id>/comment', methods=['POST'])
@login_required
def add_comment(file_id):
    file = File.query.get_or_404(file_id)
    form = CommentForm()
    
    if form.validate_on_submit():
        comment = Comment(
            content=form.content.data,
            file_id=file_id,
            user_id=current_user.id,
            parent_id=form.parent_id.data if form.parent_id.data else None
        )
        db.session.add(comment)
        db.session.commit()
        
        # Notify file owner
        if file.uploaded_by != current_user.id:
            create_notification(
                file.uploaded_by,
                'New Comment',
                f'{current_user.username} commented on your file "{file.filename}"',
                url_for('file_view', file_id=file_id),
                'comment',
                'bi-chat'
            )
        
        flash('Comment added!', 'success')
    
    return redirect(url_for('file_view', file_id=file_id))


@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    
    if comment.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    file_id = comment.file_id
    
    # Delete replies
    Comment.query.filter_by(parent_id=comment_id).delete()
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comment deleted.', 'success')
    return redirect(url_for('file_view', file_id=file_id))


# ============== RATINGS ==============
@app.route('/file/<int:file_id>/rate', methods=['POST'])
@login_required
def rate_file(file_id):
    file = File.query.get_or_404(file_id)
    form = RatingForm()
    
    if form.validate_on_submit():
        rating_value = form.rating.data
        
        # Check existing rating
        existing = Rating.query.filter_by(file_id=file_id, user_id=current_user.id).first()
        
        if existing:
            existing.rating = rating_value
        else:
            rating = Rating(
                rating=rating_value,
                file_id=file_id,
                user_id=current_user.id
            )
            db.session.add(rating)
            
            # Notify file owner
            if file.uploaded_by != current_user.id:
                create_notification(
                    file.uploaded_by,
                    'New Rating',
                    f'{current_user.username} rated your file "{file.filename}" {rating_value} stars',
                    url_for('file_view', file_id=file_id),
                    'rating',
                    'bi-star'
                )
        
        db.session.commit()
        flash('Rating submitted!', 'success')
    
    return redirect(url_for('file_view', file_id=file_id))


# ============== FAVOURITES ==============
@app.route('/star/<item_type>/<int:item_id>', methods=['POST'])
@login_required
def toggle_star(item_type, item_id):
    if item_type not in ['file', 'folder']:
        abort(400)
    
    if item_type == 'file':
        existing = Favourite.query.filter_by(user_id=current_user.id, file_id=item_id).first()
    else:
        existing = Favourite.query.filter_by(user_id=current_user.id, folder_id=item_id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'unstarred'})
    else:
        fav = Favourite(user_id=current_user.id, item_type=item_type)
        if item_type == 'file':
            fav.file_id = item_id
        else:
            fav.folder_id = item_id
        db.session.add(fav)
        db.session.commit()
        return jsonify({'status': 'starred'})


# ============== SEARCH ==============
@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    class_level = request.args.get('class_level', '')
    subject = request.args.get('subject', '')
    file_type = request.args.get('file_type', '')
    sort_by = request.args.get('sort', 'newest')
    page = request.args.get('page', 1, type=int)
    
    # Base queries
    folder_query = Folder.query.filter(Folder.is_public == True)
    file_query = File.query.join(Folder).filter(Folder.is_public == True)
    
    # Search term
    if query:
        folder_query = folder_query.filter(Folder.name.ilike(f'%{query}%'))
        file_query = file_query.filter(File.filename.ilike(f'%{query}%'))
    
    # Filters
    if category_id:
        folder_query = folder_query.filter(Folder.category_id == category_id)
        file_query = file_query.filter(Folder.category_id == category_id)
    
    if class_level:
        folder_query = folder_query.filter(Folder.class_level == class_level)
        file_query = file_query.filter(Folder.class_level == class_level)
    
    if subject:
        folder_query = folder_query.filter(Folder.subject == subject)
        file_query = file_query.filter(Folder.subject == subject)
    
    if file_type:
        file_query = file_query.filter(File.file_type == file_type)
    
    # Sort
    if sort_by == 'oldest':
        file_query = file_query.order_by(File.uploaded_at.asc())
    elif sort_by == 'downloads':
        file_query = file_query.order_by(File.download_count.desc())
    elif sort_by == 'name':
        file_query = file_query.order_by(File.filename.asc())
    else:
        file_query = file_query.order_by(File.uploaded_at.desc())
    
    # Include user's private content if logged in
    if current_user.is_authenticated:
        private_folders = Folder.query.filter(
            Folder.owner_id == current_user.id,
            Folder.is_public == False,
            Folder.name.ilike(f'%{query}%') if query else True
        )
        folder_query = folder_query.union(private_folders)
        
        private_files = File.query.join(Folder).filter(
            Folder.owner_id == current_user.id,
            Folder.is_public == False,
            File.filename.ilike(f'%{query}%') if query else True
        )
        file_query = file_query.union(private_files)
    
    folders = folder_query.limit(20).all()
    files = file_query.paginate(page=page, per_page=20)
    
    categories = Category.query.all()
    
    return render_template('search.html',
                         query=query,
                         folders=folders,
                         files=files,
                         categories=categories,
                         current_filters={
                             'category_id': category_id,
                             'class_level': class_level,
                             'subject': subject,
                             'file_type': file_type,
                             'sort_by': sort_by
                         })


# ============== EXPLORE ==============
@app.route('/explore')
def explore():
    page = request.args.get('page', 1, type=int)
    category_slug = request.args.get('category', '')
    
    query = Folder.query.filter_by(is_public=True)
    
    if category_slug:
        category = Category.query.filter_by(slug=category_slug).first()
        if category:
            query = query.filter_by(category_id=category.id)
    
    folders = query.order_by(Folder.created_at.desc()).paginate(page=page, per_page=20)
    categories = Category.query.all()
    
    return render_template('explore.html', folders=folders, categories=categories)


@app.route('/category/<slug>')
def category_view(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    
    folders = Folder.query.filter_by(category_id=category.id, is_public=True)\
        .order_by(Folder.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('category.html', category=category, folders=folders)


@app.route('/tags/<slug>')
def tag_view(slug):
    tag = Tag.query.filter_by(slug=slug).first_or_404()
    page = request.args.get('page', 1, type=int)
    
    files = tag.files.join(Folder).filter(Folder.is_public == True)\
        .order_by(File.uploaded_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('tag.html', tag=tag, files=files)


@app.route('/leaderboard')
def leaderboard():
    users = get_leaderboard(50)
    return render_template('leaderboard.html', users=users)


# ============== NOTIFICATIONS ==============
@app.route('/notifications')
@login_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = current_user.notifications.order_by(Notification.created_at.desc())\
        .paginate(page=page, per_page=20)
    
    return render_template('notifications.html', notifications=notifications)


@app.route('/notifications/read/<int:notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    
    if notification.user_id != current_user.id:
        abort(403)
    
    notification.is_read = True
    db.session.commit()
    
    if notification.link:
        return redirect(notification.link)
    return redirect(url_for('notifications'))


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    
    return redirect(url_for('notifications'))


# ============== REPORTS ==============
@app.route('/report/<item_type>/<int:item_id>', methods=['GET', 'POST'])
@login_required
def report_content(item_type, item_id):
    form = ReportForm()
    
    if form.validate_on_submit():
        report = Report(
            reporter_id=current_user.id,
            reason=form.reason.data,
            description=form.description.data
        )
        
        if item_type == 'file':
            report.file_id = item_id
        elif item_type == 'folder':
            report.folder_id = item_id
        elif item_type == 'comment':
            report.comment_id = item_id
        elif item_type == 'user':
            report.user_id = item_id
        
        db.session.add(report)
        db.session.commit()
        
        flash('Report submitted. Thank you!', 'success')
        return redirect(url_for('index'))
    
    return render_template('report.html', form=form, item_type=item_type, item_id=item_id)


# ============== API ENDPOINTS ==============
@app.route('/api/folder-tree')
@login_required
def api_folder_tree():
    folders = Folder.query.filter_by(owner_id=current_user.id).all()
    tree = build_folder_tree(folders)
    return jsonify(tree)


@app.route('/api/notifications/count')
@login_required
def api_notification_count():
    count = current_user.get_unread_notifications_count()
    return jsonify({'count': count})


@app.route('/api/search/suggest')
def api_search_suggest():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    
    # Search files
    files = File.query.join(Folder).filter(
        Folder.is_public == True,
        File.filename.ilike(f'%{query}%')
    ).limit(5).all()
    
    # Search folders
    folders = Folder.query.filter(
        Folder.is_public == True,
        Folder.name.ilike(f'%{query}%')
    ).limit(5).all()
    
    suggestions = []
    for folder in folders:
        suggestions.append({
            'type': 'folder',
            'name': folder.name,
            'url': url_for('folder_view', folder_id=folder.id)
        })
    for file in files:
        suggestions.append({
            'type': 'file',
            'name': file.filename,
            'url': url_for('file_view', file_id=file.id)
        })
    
    return jsonify(suggestions)


@app.route('/api/stats')
def api_stats():
    return jsonify(get_stats())


# ============== ADMIN PANEL ==============
@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    stats = {
        'users': User.query.count(),
        'files': File.query.count(),
        'folders': Folder.query.count(),
        'reports': Report.query.filter_by(status='pending').count(),
        'downloads_today': DownloadHistory.query.filter(
            DownloadHistory.downloaded_at >= datetime.utcnow().date()
        ).count()
    }
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    recent_reports = Report.query.filter_by(status='pending').order_by(Report.created_at.desc()).limit(10).all()
    recent_activities = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(20).all()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_reports=recent_reports,
                         recent_activities=recent_activities)


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )
    
    users = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/users.html', users=users, search=search)


@app.route('/admin/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.is_active = form.is_active.data
        user.is_admin = form.is_admin.data
        user.is_verified = form.is_verified.data
        db.session.commit()
        
        flash('User updated!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/edit_user.html', form=form, user=user)


@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Cannot delete yourself!', 'danger')
        return redirect(url_for('admin_users'))
    
    # Delete user's files and folders
    for folder in user.folders:
        for file in folder.files:
            delete_file(file.stored_filename, app.config['UPLOAD_FOLDER'])
        db.session.delete(folder)
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/reports')
@login_required
@admin_required
def admin_reports():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 'pending')
    
    query = Report.query
    if status:
        query = query.filter_by(status=status)
    
    reports = query.order_by(Report.created_at.desc()).paginate(page=page, per_page=20)
    
    return render_template('admin/reports.html', reports=reports, current_status=status)


@app.route('/admin/report/<int:report_id>/resolve', methods=['POST'])
@login_required
@admin_required
def admin_resolve_report(report_id):
    report = Report.query.get_or_404(report_id)
    action = request.form.get('action', 'dismiss')
    
    if action == 'dismiss':
        report.status = 'dismissed'
    elif action == 'resolve':
        report.status = 'resolved'
        # Take action based on report type
        if report.file_id:
            file = File.query.get(report.file_id)
            if file:
                delete_file(file.stored_filename, app.config['UPLOAD_FOLDER'])
                db.session.delete(file)
        elif report.comment_id:
            comment = Comment.query.get(report.comment_id)
            if comment:
                db.session.delete(comment)
    
    report.admin_notes = request.form.get('notes', '')
    report.resolved_at = datetime.utcnow()
    db.session.commit()
    
    flash('Report processed.', 'success')
    return redirect(url_for('admin_reports'))


@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_categories():
    form = CategoryForm()
    form.parent_id.choices = [(0, 'None')] + [(c.id, c.name) for c in Category.query.all()]
    
    if form.validate_on_submit():
        category = Category(
            name=form.name.data,
            slug=form.slug.data,
            description=form.description.data,
            icon=form.icon.data,
            color=form.color.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None
        )
        db.session.add(category)
        db.session.commit()
        flash('Category created!', 'success')
        return redirect(url_for('admin_categories'))
    
    categories = Category.query.all()
    return render_template('admin/categories.html', form=form, categories=categories)


@app.route('/admin/announcements', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_announcements():
    form = AnnouncementForm()
    
    if form.validate_on_submit():
        announcement = Announcement(
            title=form.title.data,
            content=form.content.data,
            announcement_type=form.announcement_type.data,
            is_active=form.is_active.data,
            is_pinned=form.is_pinned.data
        )
        db.session.add(announcement)
        db.session.commit()
        flash('Announcement created!', 'success')
        return redirect(url_for('admin_announcements'))
    
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('admin/announcements.html', form=form, announcements=announcements)


# ============== ERROR HANDLERS ==============
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(413)
def file_too_large(error):
    flash('File too large! Maximum size is 50MB.', 'danger')
    return redirect(request.url)

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# ============== RUN APP ==============
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)