from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_bcrypt import Bcrypt
from flask_moment import Moment
import json
import os
import re
from datetime import datetime, timedelta # Import datetime directly, and timedelta
from functools import wraps
import uuid # ADDED: Import uuid for unique IDs

app = Flask(__name__)
moment = Moment(app)
app.config['SECRET_KEY'] = 'cf8b472947bbaba36d954f2e989a654bc6050dc87bac3d80'
bcrypt = Bcrypt(app)

# --- JSON Database Paths ---
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
VIDEOS_FILE = os.path.join(DATA_DIR, 'videos.json')
LIKES_FILE = os.path.join(DATA_DIR, 'likes.json')
ENROLLMENTS_FILE = os.path.join(DATA_DIR, 'enrollments.json')
SUGGESTIONS_FILE = os.path.join(DATA_DIR, 'suggestions.json')
ADS_FILE = os.path.join(DATA_DIR, 'ads.json')
DONATION_COMMENTS_FILE = os.path.join(DATA_DIR, 'donation_comments.json')

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helper Functions for JSON DB ---

def load_json(filepath):
    """Loads data from a JSON file. Initializes with empty list if file is empty or non-existent."""
    if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
        # Ensure file exists and contains an empty JSON array if it was empty/missing
        with open(filepath, 'w') as f:
            json.dump([], f)
        return [] # Return empty list immediately
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json(filepath, data):
    """Saves data to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

# Ensure all JSON files exist and are initialized with an empty list if they are new or empty
for f in [USERS_FILE, VIDEOS_FILE, LIKES_FILE, ENROLLMENTS_FILE, SUGGESTIONS_FILE, ADS_FILE, DONATION_COMMENTS_FILE]:
    load_json(f) # Calling load_json will ensure the file is created with '[]' if not present or empty

# --- User Authentication Decorators ---

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        users = load_json(USERS_FILE)
        current_user = next(
            (u for u in users if u['id'] == session['user_id']), None)
        if not current_user or not current_user.get('is_admin'):
            flash('You do not have administrative access.', 'danger')
            return redirect(url_for('library'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---

@app.route('/')
@app.route('/library')
def library():
    videos = load_json(VIDEOS_FILE)
    # Ensure all videos have a 'category' key to prevent errors if some are missing
    categories = sorted(list(set(v.get('category', 'Uncategorized') for v in videos)))

    # Filtering and Sorting
    category_filter = request.args.get('category')
    sort_by = request.args.get('sort_by', 'recently_uploaded')

    if category_filter and category_filter != 'all':
        videos = [v for v in videos if v.get('category') == category_filter]

    if sort_by == 'most_liked':
        videos.sort(key=lambda x: x.get('likes_count', 0), reverse=True)
    elif sort_by == 'most_viewed':
        videos.sort(key=lambda x: x.get('views', 0), reverse=True)
    else:  # recently_uploaded (default)
        # Ensure 'uploaded_at' exists for sorting, default to a very old date if not
        videos.sort(key=lambda x: x.get('uploaded_at', '1970-01-01T00:00:00'), reverse=True)

    # Get dismissed ads for the current user
    active_ads = []
    if 'user_id' in session:
        ads = load_json(ADS_FILE)
        user_id = session['user_id']
        active_ads = [ad for ad in ads if ad.get(
            'is_active') and user_id not in ad.get('dismissed_by_users', [])]
    else:
        # Show all active ads to non-logged-in users (they can't dismiss them)
        ads = load_json(ADS_FILE)
        active_ads = [ad for ad in ads if ad.get('is_active')]

    return render_template('library.html', videos=videos, categories=categories,
                           current_category=category_filter, current_sort=sort_by,
                           ads=active_ads)

@app.route('/video/<video_id>')
@login_required
def video_detail(video_id):
    videos = load_json(VIDEOS_FILE)
    video = next((v for v in videos if v['id'] == video_id), None)

    if not video:
        flash('Video not found.', 'danger')
        return redirect(url_for('library'))

    # Increment view count
    video['views'] = video.get('views', 0) + 1
    save_json(VIDEOS_FILE, videos)

    # Check if user has liked this video
    user_id = session['user_id']
    likes = load_json(LIKES_FILE)
    is_liked = any(l['user_id'] == user_id and l['video_id']
                   == video_id for l in likes)

    # Check if user is enrolled
    enrollments = load_json(ENROLLMENTS_FILE)
    is_enrolled = any(e['user_id'] == user_id and e['video_id']
                      == video_id for e in enrollments)

    # Get user's suggestion for this video if they are enrolled and have submitted one
    user_suggestion = None
    if is_enrolled:
        suggestions = load_json(SUGGESTIONS_FILE)
        user_suggestion_entry = next(
            (s for s in suggestions if s['user_id'] == user_id and s['video_id'] == video_id), None)
        if user_suggestion_entry:
            user_suggestion = user_suggestion_entry['suggestion_text']

    return render_template('video_detail.html', video=video, is_liked=is_liked,
                           is_enrolled=is_enrolled, user_suggestion=user_suggestion)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session: # Check if already logged in using 'user_id'
        return redirect(url_for('library'))

    if request.method == 'POST':
        email = request.form.get('email') # Use .get() for safer access
        password = request.form.get('password') # Use .get() for safer access

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')

        users = load_json(USERS_FILE)
        user = next((u for u in users if u['email'] == email), None)

        if user:
            if bcrypt.check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['is_admin'] = user.get('is_admin', False)
                flash('Login successful!', 'success')
                return redirect(url_for('library'))
            else:
                # This handles both wrong password and malformed hash if user is found
                flash('Invalid email or password.', 'danger')
        else:
            flash('Invalid email or password.', 'danger') # User not found
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session: # Check if already logged in using 'user_id'
        return redirect(url_for('library'))

    if request.method == 'POST':
        username = request.form.get('username') # Use .get()
        email = request.form.get('email')       # Use .get()
        password = request.form.get('password') # Use .get()
        confirm_password = request.form.get('confirm_password') # Use .get()

        users = load_json(USERS_FILE)

        # Basic validations
        if not username or not email or not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return render_template('signup.html', username=username, email=email)

        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            flash('Username must be 3-20 characters long and contain only letters, numbers, or underscores.', 'danger')
            return render_template('signup.html', username=username, email=email)

        if any(u['email'] == email for u in users):
            flash('Account with that email already exists.', 'warning')
            return render_template('signup.html', username=username, email=email)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html', username=username, email=email)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('signup.html', username=username, email=email)

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = {
            'id': str(uuid.uuid4()),
            'username': username,
            'email': email,
            'password': hashed_password,
            'is_admin': False,
            'created_at': datetime.now().isoformat()
        }
        users.append(new_user)
        save_json(USERS_FILE, users)
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('library'))

@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    users = load_json(USERS_FILE)
    current_user = next((u for u in users if u['id'] == user_id), None)

    if not current_user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('logout'))

    likes = load_json(LIKES_FILE)
    videos = load_json(VIDEOS_FILE)

    liked_video_ids = [l['video_id'] for l in likes if l['user_id'] == user_id]
    liked_videos = [v for v in videos if v['id'] in liked_video_ids]

    enrollments = load_json(ENROLLMENTS_FILE)
    enrolled_video_ids = [e['video_id']
                          for e in enrollments if e['user_id'] == user_id]
    enrolled_videos = [v for v in videos if v['id'] in enrolled_video_ids]

    # Get dismissed ads for the current user
    ads = load_json(ADS_FILE)
    active_ads = [ad for ad in ads if ad.get(
        'is_active') and user_id not in ad.get('dismissed_by_users', [])]

    # Don't pass the hashed password to the template directly
    display_user = {k: v for k, v in current_user.items() if k != 'password'}

    return render_template('profile.html', user=display_user, liked_videos=liked_videos,
                           enrolled_videos=enrolled_videos, ads=active_ads)

@app.route('/like_video/<video_id>', methods=['POST'])
@login_required
def like_video(video_id):
    user_id = session['user_id']
    likes = load_json(LIKES_FILE)
    videos = load_json(VIDEOS_FILE)

    video_exists = any(v['id'] == video_id for v in videos)
    if not video_exists:
        return jsonify({'success': False, 'message': 'Video not found.'})

    existing_like = next(
        (l for l in likes if l['user_id'] == user_id and l['video_id'] == video_id), None)

    if existing_like:
        # Unlike
        likes.remove(existing_like)
        liked = False
    else:
        # Like
        likes.append({'user_id': user_id, 'video_id': video_id,
                      'timestamp': datetime.now().isoformat()})
        liked = True

    save_json(LIKES_FILE, likes)

    # Update likes_count in videos.json (denormalization)
    for video in videos:
        if video['id'] == video_id:
            video['likes_count'] = len(
                [l for l in likes if l['video_id'] == video_id])
            break
    save_json(VIDEOS_FILE, videos)

    # Find the updated video to send its likes_count
    updated_video = next((v for v in videos if v['id'] == video_id), {})
    return jsonify({'success': True, 'liked': liked, 'likes_count': updated_video.get('likes_count', 0)})

@app.route('/enroll_video/<video_id>', methods=['POST'])
@login_required
def enroll_video(video_id):
    user_id = session['user_id']
    enrollments = load_json(ENROLLMENTS_FILE)
    videos = load_json(VIDEOS_FILE)

    video_exists = any(v['id'] == video_id for v in videos)
    if not video_exists:
        return jsonify({'success': False, 'message': 'Video not found.'})

    existing_enrollment = next(
        (e for e in enrollments if e['user_id'] == user_id and e['video_id'] == video_id), None)

    if existing_enrollment:
        return jsonify({'success': False, 'message': 'Already enrolled.'})

    enrollments.append({
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'video_id': video_id,
        'timestamp': datetime.now().isoformat()
    })
    save_json(ENROLLMENTS_FILE, enrollments)
    return jsonify({'success': True, 'message': 'Enrolled successfully!'})

@app.route('/submit_suggestion/<video_id>', methods=['POST'])
@login_required
def submit_suggestion(video_id):
    user_id = session['user_id']
    suggestion_text = request.form.get('suggestion')

    if not suggestion_text:
        flash('Suggestion cannot be empty.', 'danger')
        return redirect(url_for('video_detail', video_id=video_id))

    enrollments = load_json(ENROLLMENTS_FILE)
    suggestions = load_json(SUGGESTIONS_FILE)

    # Check if user is actually enrolled in this video
    enrolled = any(e['user_id'] == user_id and e['video_id']
                   == video_id for e in enrollments)
    if not enrolled:
        flash('You must be enrolled in this video to submit a suggestion.', 'danger')
        return redirect(url_for('video_detail', video_id=video_id))

    # Update existing suggestion or add new one
    existing_suggestion = next(
        (s for s in suggestions if s['user_id'] == user_id and s['video_id'] == video_id), None)
    if existing_suggestion:
        existing_suggestion['suggestion_text'] = suggestion_text
        existing_suggestion['timestamp'] = datetime.now().isoformat()
    else:
        suggestions.append({
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'video_id': video_id,
            'suggestion_text': suggestion_text,
            'timestamp': datetime.now().isoformat()
        })
    save_json(SUGGESTIONS_FILE, suggestions)
    flash('Suggestion submitted successfully!', 'success')
    return redirect(url_for('video_detail', video_id=video_id))

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'POST':
        comment = request.form.get('comment')

        donation_comments = load_json(DONATION_COMMENTS_FILE)

        user_email = "Anonymous"
        if 'user_id' in session:
            users = load_json(USERS_FILE)
            current_user = next(
                (u for u in users if u['id'] == session['user_id']), None)
            if current_user:
                user_email = current_user.get('email', 'Anonymous')

        donation_comments.append({
            'id': str(uuid.uuid4()),
            'user_email': user_email,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        })
        save_json(DONATION_COMMENTS_FILE, donation_comments)
        # Actual payment is handled client-side/externally
        flash('Thank you for your donation!', 'success')
        return redirect(url_for('donate'))
    return render_template('donate.html')

@app.route('/dismiss_ad/<ad_id>', methods=['POST'])
@login_required
def dismiss_ad(ad_id):
    user_id = session['user_id']
    ads = load_json(ADS_FILE)

    ad_found = False
    for ad in ads:
        if ad['id'] == ad_id:
            if 'dismissed_by_users' not in ad:
                ad['dismissed_by_users'] = []
            if user_id not in ad['dismissed_by_users']:
                ad['dismissed_by_users'].append(user_id)
            ad_found = True
            break

    if ad_found:
        save_json(ADS_FILE, ads)
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Ad not found or already dismissed.'})

# --- Admin Routes ---
@app.route('/admin')
@admin_required
def admin_dashboard():
    users = load_json(USERS_FILE)
    videos = load_json(VIDEOS_FILE)
    enrollments = load_json(ENROLLMENTS_FILE)
    likes = load_json(LIKES_FILE)
    donation_comments = load_json(DONATION_COMMENTS_FILE)

    total_users = len(users)
    total_videos = len(videos)
    total_enrollments = len(enrollments)
    unique_enrollments_users = len(set(e['user_id'] for e in enrollments))
    total_likes = len(likes)

    # New users/videos in last 7 days
    seven_days_ago_dt = datetime.now() - timedelta(days=7)
    # Use .get() with a default for robustness in case 'created_at' or 'uploaded_at' is missing
    new_users_7days = [u for u in users if datetime.fromisoformat(u.get('created_at', '1970-01-01T00:00:00')) >= seven_days_ago_dt]
    new_videos_7days = [v for v in videos if datetime.fromisoformat(v.get('uploaded_at', '1970-01-01T00:00:00')) >= seven_days_ago_dt]

    return render_template('admin_dashboard.html',
                           total_users=total_users,
                           total_videos=total_videos,
                           total_enrollments=total_enrollments,
                           unique_enrollments_users=unique_enrollments_users,
                           total_likes=total_likes,
                           new_users_7days_count=len(new_users_7days),
                           new_videos_7days_count=len(new_videos_7days),
                           donation_comments=donation_comments)

@app.route('/admin/users')
@admin_required
def admin_manage_users():
    users = load_json(USERS_FILE)
    return render_template('admin_manage_users.html', users=users)

@app.route('/admin/users/edit/<user_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    users = load_json(USERS_FILE)
    user = next((u for u in users if u['id'] == user_id), None)

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_manage_users'))

    if request.method == 'POST':
        user['username'] = request.form['username']
        user['email'] = request.form['email']
        new_password = request.form['password']
        if new_password:
            user['password'] = bcrypt.generate_password_hash(
                new_password).decode('utf-8')
        user['is_admin'] = 'is_admin' in request.form
        save_json(USERS_FILE, users)
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin_manage_users'))
    return render_template('admin_edit_user.html', user=user)

@app.route('/admin/users/delete/<user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    users = load_json(USERS_FILE)
    users = [u for u in users if u['id'] != user_id]
    save_json(USERS_FILE, users)
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/videos')
@admin_required
def admin_manage_videos():
    videos = load_json(VIDEOS_FILE)
    return render_template('admin_manage_videos.html', videos=videos)

@app.route('/admin/videos/add', methods=['GET', 'POST'])
@admin_required
def admin_add_video():
    categories = ["Cartography", "GIS", "Remote Sensing", "Survey",
                  "Photogrammetry", "Web Development", "Community Contributions"]
    if request.method == 'POST':
        new_video = {
            'id': str(uuid.uuid4()),
            'title': request.form['title'],
            'description': request.form['description'],
            'category': request.form['category'],
            'video_url': request.form['video_url'],
            'thumbnail_url': request.form['thumbnail_url'],
            'uploaded_at': datetime.now().isoformat(),
            'views': 0,
            'likes_count': 0
        }
        videos = load_json(VIDEOS_FILE)
        videos.append(new_video)
        save_json(VIDEOS_FILE, videos)
        flash('Video added successfully!', 'success')
        return redirect(url_for('admin_manage_videos'))
    return render_template('admin_add_video.html', categories=categories)

@app.route('/admin/videos/edit/<video_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_video(video_id):
    videos = load_json(VIDEOS_FILE)
    video = next((v for v in videos if v['id'] == video_id), None)
    categories = ["Cartography", "GIS", "Remote Sensing", "Survey",
                  "Photogrammetry", "Web Development", "Community Contributions"]

    if not video:
        flash('Video not found.', 'danger')
        return redirect(url_for('admin_manage_videos'))

    if request.method == 'POST':
        video['title'] = request.form['title']
        video['description'] = request.form['description']
        video['category'] = request.form['category']
        video['video_url'] = request.form['video_url']
        video['thumbnail_url'] = request.form['thumbnail_url']
        save_json(VIDEOS_FILE, videos)
        flash('Video updated successfully!', 'success')
        return redirect(url_for('admin_manage_videos'))
    return render_template('admin_edit_video.html', video=video, categories=categories)

@app.route('/admin/videos/delete/<video_id>', methods=['POST'])
@admin_required
def admin_delete_video(video_id):
    videos = load_json(VIDEOS_FILE)
    videos = [v for v in videos if v['id'] != video_id]
    save_json(VIDEOS_FILE, videos)

    # Also remove any likes/enrollments/suggestions related to this video
    likes = load_json(LIKES_FILE)
    likes = [l for l in likes if l['video_id'] != video_id]
    save_json(LIKES_FILE, likes)

    enrollments = load_json(ENROLLMENTS_FILE)
    enrollments = [e for e in enrollments if e['video_id'] != video_id]
    save_json(ENROLLMENTS_FILE, enrollments)

    suggestions = load_json(SUGGESTIONS_FILE)
    suggestions = [s for s in suggestions if s['video_id'] != video_id]
    save_json(SUGGESTIONS_FILE, suggestions)

    flash('Video deleted successfully!', 'success')
    return redirect(url_for('admin_manage_videos'))

@app.route('/admin/ads')
@admin_required
def admin_manage_ads():
    ads = load_json(ADS_FILE)
    return render_template('admin_manage_ads.html', ads=ads)

@app.route('/admin/ads/add', methods=['GET', 'POST'])
@admin_required
def admin_add_ad():
    if request.method == 'POST':
        new_ad = {
            'id': str(uuid.uuid4()),
            'title': request.form['title'],
            'content': request.form['content'],
            'image_url': request.form['image_url'],
            'link_url': request.form['link_url'],
            'is_active': 'is_active' in request.form,
            'created_at': datetime.now().isoformat(),
            'dismissed_by_users': []
        }
        ads = load_json(ADS_FILE)
        ads.append(new_ad)
        save_json(ADS_FILE, ads)
        flash('Announcement/Ad added successfully!', 'success')
        return redirect(url_for('admin_manage_ads'))
    return render_template('admin_add_ad.html')

@app.route('/admin/ads/edit/<ad_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_ad(ad_id):
    ads = load_json(ADS_FILE)
    ad = next((a for a in ads if a['id'] == ad_id), None)

    if not ad:
        flash('Announcement/Ad not found.', 'danger')
        return redirect(url_for('admin_manage_ads'))

    if request.method == 'POST':
        ad['title'] = request.form['title']
        ad['content'] = request.form['content']
        ad['image_url'] = request.form['image_url']
        ad['link_url'] = request.form['link_url']
        ad['is_active'] = 'is_active' in request.form
        save_json(ADS_FILE, ads)
        flash('Announcement/Ad updated successfully!', 'success')
        return redirect(url_for('admin_manage_ads'))
    return render_template('admin_edit_ad.html', ad=ad)

@app.route('/admin/ads/delete/<ad_id>', methods=['POST'])
@admin_required
def admin_delete_ad(ad_id):
    ads = load_json(ADS_FILE)
    ads = [a for a in ads if a['id'] != ad_id]
    save_json(ADS_FILE, ads)
    flash('Announcement/Ad deleted successfully!', 'success')
    return redirect(url_for('admin_manage_ads'))

@app.route('/admin/enrollments')
@admin_required
def admin_enrollment_report():
    enrollments = load_json(ENROLLMENTS_FILE)
    users = load_json(USERS_FILE)
    videos = load_json(VIDEOS_FILE)
    suggestions = load_json(SUGGESTIONS_FILE)

    report_data = []
    for e in enrollments:
        user = next((u for u in users if u['id'] == e['user_id']), {
                            'email': 'Unknown User', 'username': 'Unknown User'})
        video = next((v for v in videos if v['id'] == e['video_id']), {
                             'title': 'Unknown Video'})
        suggestion = next(
            (s for s in suggestions if s['user_id'] == e['user_id'] and s['video_id'] == e['video_id']), None)

        report_data.append({
            'user_email': user['email'],
            'user_username': user['username'],
            'video_title': video['title'],
            'enrollment_timestamp': e['timestamp'],
            'suggestion_text': suggestion['suggestion_text'] if suggestion else 'No suggestion yet'
        })

    return render_template('admin_enrollment_report.html', report_data=report_data)

# --- API Endpoints for Charting (Admin Dashboard) ---

@app.route('/admin/api/video_views')
@admin_required
def api_video_views():
    videos = load_json(VIDEOS_FILE)
    view_data = {}
    for video in videos:
        category = video.get('category', 'Uncategorized')
        view_data[category] = view_data.get(
            category, 0) + video.get('views', 0)

    labels = list(view_data.keys())
    data = list(view_data.values())

    return jsonify({'labels': labels, 'data': data, 'chart_type': 'bar', 'title': 'Video Views by Category'})

@app.route('/admin/api/enrollment_trends')
@admin_required
def api_enrollment_trends():
    enrollments = load_json(ENROLLMENTS_FILE)
    # Group enrollments by day
    enrollment_counts = {}
    for e in enrollments:
        date = datetime.fromisoformat(
            e['timestamp']).strftime('%Y-%m-%d')
        enrollment_counts[date] = enrollment_counts.get(date, 0) + 1

    # Sort by date
    sorted_dates = sorted(enrollment_counts.keys())
    data = [enrollment_counts[date] for date in sorted_dates]

    return jsonify({'labels': sorted_dates, 'data': data, 'chart_type': 'line', 'title': 'Enrollment Trends Over Time'})

@app.route('/admin/api/likes_distribution')
@admin_required
def api_likes_distribution():
    videos = load_json(VIDEOS_FILE)
    # Get top 5 most liked videos for a pie chart or bar chart
    sorted_videos = sorted(videos, key=lambda x: x.get(
        'likes_count', 0), reverse=True)[:5]

    labels = [v['title'] for v in sorted_videos]
    data = [v.get('likes_count', 0) for v in sorted_videos]

    return jsonify({'labels': labels, 'data': data, 'chart_type': 'pie', 'title': 'Top 5 Most Liked Videos'})
@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/admin/api/user_activity')
@admin_required
def api_user_activity():
    users = load_json(USERS_FILE)
    # Simple example: users created per month
    user_creation_counts = {}
    for u in users:
        if 'created_at' in u:
            month = datetime.fromisoformat(
                u['created_at']).strftime('%Y-%m')
            user_creation_counts[month] = user_creation_counts.get(
                month, 0) + 1

    sorted_months = sorted(user_creation_counts.keys())
    data = [user_creation_counts[month] for month in sorted_months]

    return jsonify({'labels': sorted_months, 'data': data, 'chart_type': 'bar', 'title': 'User Registrations Over Time'})

if __name__ == '__main__':
    app.run(debug=True)