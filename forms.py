from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import (StringField, PasswordField, BooleanField, TextAreaField, 
                     SelectField, IntegerField, HiddenField, SelectMultipleField)
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, URL, NumberRange
from models import User

# ============== AUTH FORMS ==============
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(), 
        Length(min=3, max=80, message='Username must be 3-80 characters')
    ])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(), 
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('password', message='Passwords must match')
    ])


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(), 
        Length(min=6, message='Password must be at least 6 characters')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(), 
        EqualTo('new_password', message='Passwords must match')
    ])


# ============== PROFILE FORMS ==============
class ProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[Optional(), Length(max=150)])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    location = StringField('Location', validators=[Optional(), Length(max=100)])
    website = StringField('Website', validators=[Optional(), URL(), Length(max=200)])
    instagram = StringField('Instagram Username', validators=[Optional(), Length(max=100)])
    twitter = StringField('Twitter Username', validators=[Optional(), Length(max=100)])
    youtube = StringField('YouTube Channel URL', validators=[Optional(), URL(), Length(max=200)])


class AvatarForm(FlaskForm):
    avatar = FileField('Profile Picture', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])


# ============== FOLDER FORMS ==============
class FolderForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    parent_id = SelectField('Parent Folder', coerce=int, choices=[])
    category_id = SelectField('Category', coerce=int, choices=[], validators=[Optional()])
    class_level = SelectField('Class Level', choices=[
        ('', 'Select Class'),
        ('class_10', 'Class 10'),
        ('class_11', 'Class 11'),
        ('class_12', 'Class 12'),
        ('college', 'College'),
        ('competitive', 'Competitive Exams'),
        ('other', 'Other')
    ], validators=[Optional()])
    subject = SelectField('Subject', choices=[
        ('', 'Select Subject'),
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
    ], validators=[Optional()])
    is_public = BooleanField('Make Public')
    folder_password = PasswordField('Folder Password (Optional)', validators=[Optional(), Length(max=50)])


class FolderPasswordForm(FlaskForm):
    password = PasswordField('Folder Password', validators=[DataRequired()])


# ============== FILE FORMS ==============
class UploadForm(FlaskForm):
    files = MultipleFileField('Select Files', validators=[DataRequired()])
    folder_id = SelectField('Upload to Folder', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Description (Optional)', validators=[Optional(), Length(max=500)])
    tags = StringField('Tags (comma separated)', validators=[Optional(), Length(max=200)])


class FileEditForm(FlaskForm):
    filename = StringField('File Name', validators=[DataRequired(), Length(max=300)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    tags = StringField('Tags (comma separated)', validators=[Optional(), Length(max=200)])


# ============== COMMENT FORM ==============
class CommentForm(FlaskForm):
    content = TextAreaField('Comment', validators=[DataRequired(), Length(min=2, max=1000)])
    parent_id = HiddenField('Parent Comment ID')


# ============== RATING FORM ==============
class RatingForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(min=1, max=5)])


# ============== SEARCH FORM ==============
class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired(), Length(min=2, max=100)])
    category = SelectField('Category', coerce=int, choices=[], validators=[Optional()])
    class_level = SelectField('Class', choices=[('', 'All Classes')], validators=[Optional()])
    subject = SelectField('Subject', choices=[('', 'All Subjects')], validators=[Optional()])
    file_type = SelectField('File Type', choices=[
        ('', 'All Types'),
        ('pdf', 'PDF'),
        ('image', 'Images'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('document', 'Documents')
    ], validators=[Optional()])


class AdvancedSearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional(), Length(max=100)])
    category_id = SelectField('Category', coerce=int, choices=[], validators=[Optional()])
    class_level = SelectField('Class Level', choices=[], validators=[Optional()])
    subject = SelectField('Subject', choices=[], validators=[Optional()])
    file_type = SelectField('File Type', choices=[], validators=[Optional()])
    sort_by = SelectField('Sort By', choices=[
        ('newest', 'Newest First'),
        ('oldest', 'Oldest First'),
        ('downloads', 'Most Downloads'),
        ('rating', 'Highest Rated'),
        ('name', 'Name A-Z')
    ], validators=[Optional()])


# ============== REPORT FORM ==============
class ReportForm(FlaskForm):
    reason = SelectField('Reason', choices=[
        ('spam', 'Spam or Misleading'),
        ('inappropriate', 'Inappropriate Content'),
        ('copyright', 'Copyright Violation'),
        ('harmful', 'Harmful or Dangerous'),
        ('other', 'Other')
    ], validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])


# ============== ADMIN FORMS ==============
class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    slug = StringField('Slug', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    icon = StringField('Icon Class', validators=[Optional(), Length(max=50)])
    color = SelectField('Color', choices=[
        ('primary', 'Blue'),
        ('success', 'Green'),
        ('danger', 'Red'),
        ('warning', 'Yellow'),
        ('info', 'Cyan'),
        ('secondary', 'Gray')
    ])
    parent_id = SelectField('Parent Category', coerce=int, choices=[], validators=[Optional()])


class AnnouncementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Content', validators=[DataRequired()])
    announcement_type = SelectField('Type', choices=[
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('danger', 'Danger')
    ])
    is_active = BooleanField('Active')
    is_pinned = BooleanField('Pinned')


class UserEditForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[Optional(), Length(max=150)])
    is_active = BooleanField('Active')
    is_admin = BooleanField('Admin')
    is_verified = BooleanField('Verified')


# ============== CONTACT FORM ==============
class ContactForm(FlaskForm):
    name = StringField('Your Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Your Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10, max=2000)])