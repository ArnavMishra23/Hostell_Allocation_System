"""
Hostel Room Allocation System
Main Flask Application Entry Point

This is the main file that starts the Flask web server.
It initializes the app, database, and login manager.

Technologies Used:
- Flask: Web framework
- Flask-SQLAlchemy: Database ORM
- Flask-Login: User session management
- Flask-WTF: Form handling with CSRF protection
- Flask-Bcrypt: Password hashing
- SQLite: Database (as per SRS requirements)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
import os
import re
import secrets
from extensions import db, bcrypt, login_manager, csrf

# Initialize Flask application
app = Flask(__name__)

# Configuration
# SECRET_KEY is used for session management and CSRF protection.
# In production, set SECRET_KEY in environment variables.
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)

# Database configuration
# Uses DATABASE_URL in deployment and falls back to local SQLite.
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///hostel_allocation.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Session configuration
# Session expires after 30 minutes of inactivity (REQ-UM-05)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Initialize extensions
db.init_app(app)              # Database ORM for SQL operations
bcrypt.init_app(app)          # Password hashing using bcrypt (SEC-01)
login_manager.init_app(app)   # User session management
login_manager.login_view = 'login'  # Redirect to login page if not authenticated
login_manager.login_message = 'Please log in to access this page.'
csrf.init_app(app)            # CSRF protection for forms (SEC-03)

# Import models after db initialization to avoid circular imports
from models import User, Room, Application, Allocation, RoomOccupant

# User loader callback for Flask-Login
# This tells Flask-Login how to load a user from the database
@login_manager.user_loader
def load_user(user_id):
    """
    Load user from database by ID.
    This function is called by Flask-Login to get the current user.
    
    Args:
        user_id: The ID of the user to load
        
    Returns:
        User object if found, None otherwise
    """
    return User.query.get(int(user_id))


def is_safe_redirect_url(target_url):
    """Allow redirects only to local URLs to prevent open redirect attacks."""
    if not target_url:
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target_url))
    return redirect_url.scheme in ('http', 'https') and host_url.netloc == redirect_url.netloc


def is_valid_email(email):
    """Basic email format validation for server-side safety."""
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email or ""))


def validate_room_form_data(room_number, capacity, room_type, status=None):
    """Validate room form input used by add/edit routes."""
    errors = []
    valid_room_types = {'single', 'double', 'triple'}
    valid_statuses = {'available', 'occupied', 'maintenance'}

    if not room_number:
        errors.append('Room number is required.')
    if capacity is None or capacity <= 0:
        errors.append('Room capacity must be greater than 0.')
    if room_type not in valid_room_types:
        errors.append('Please select a valid room type.')
    if status is not None and status not in valid_statuses:
        errors.append('Please select a valid room status.')

    return errors

# Context processor to make current year available in all templates
@app.context_processor
def inject_current_year():
    """Make current year available in all templates for copyright/footer."""
    return {'current_year': datetime.now().year}

# =============================================================================
# HOME AND AUTHENTICATION ROUTES
# =============================================================================

@app.route('/')
def index():
    """
    Home page route.
    If user is logged in, redirect to their dashboard.
    Otherwise, show the landing page.
    """
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration route (REQ-UM-01).
    
    Handles student registration with:
    - Email verification (unique email check)
    - Password hashing with bcrypt (SEC-01)
    - Profile information (name, year, CGPA, gender, contact)
    
    GET: Display registration form
    POST: Process registration form data
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        year_of_study = request.form.get('year_of_study', type=int)
        cgpa = request.form.get('cgpa', type=float)
        gender = request.form.get('gender', '')
        contact_no = request.form.get('contact_no', '').strip()
        
        # Validation
        errors = []

        if not email or not is_valid_email(email):
            errors.append('Please enter a valid email address.')
        if not name:
            errors.append('Name is required.')
        if not gender:
            errors.append('Gender is required.')
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            errors.append('Email already registered. Please use a different email or login.')
        
        # Password validation (SEC-05)
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        # CGPA validation (0 to 10 scale)
        if cgpa is None or cgpa < 0 or cgpa > 10:
            errors.append('CGPA must be between 0 and 10.')
        
        # Year validation
        if year_of_study not in [1, 2, 3, 4]:
            errors.append('Year of study must be between 1 and 4.')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', 
                                 email=email, name=name, year_of_study=year_of_study,
                                 cgpa=cgpa, gender=gender, contact_no=contact_no)
        
        # Create new user
        # Password is hashed using bcrypt (SEC-01)
        new_user = User(
            email=email,
            password=password,  # Will be hashed by the model setter
            name=name,
            role='student',
            year_of_study=year_of_study,
            cgpa=cgpa,
            gender=gender,
            contact_no=contact_no
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('register.html')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login route (REQ-UM-02).
    
    Handles user authentication with:
    - Email and password verification
    - Password comparison using bcrypt
    - Session management with 30-minute timeout (REQ-UM-05)
    - Role-based redirect (Student → Dashboard, Admin → Admin Panel)
    
    GET: Display login form
    POST: Process login credentials
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember') == 'on'

        if not is_valid_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('login.html')
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        # Verify password using bcrypt
        if user and user.check_password(password):
            # Login successful
            login_user(user, remember=remember_me)
            session.permanent = True  # Enable session timeout (REQ-UM-05)
            
            # Log admin login for audit (SEC-04)
            if user.is_admin():
                app.logger.info(f'Admin login: {user.email} at {datetime.now()}')
            
            flash(f'Welcome, {user.name}!', 'success')
            
            # Redirect based on role
            next_page = request.args.get('next')
            if next_page and is_safe_redirect_url(next_page):
                return redirect(next_page)
            if user.is_admin():
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """
    User logout route.
    Clears the user session and redirects to home page.
    """
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# =============================================================================
# STUDENT ROUTES
# =============================================================================

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """
    Student dashboard route.
    
    Displays:
    - Student's profile information
    - Current application status
    - Room allocation status (if allocated)
    - Quick actions (apply for room, view status)
    """
    if not current_user.is_student():
        flash('Access denied. Student privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get student's current application
    current_application = Application.query.filter_by(
        student_id=current_user.id
    ).order_by(Application.application_date.desc()).first()
    
    # Get allocation if exists
    allocation = None
    allocated_room = None
    if current_application:
        allocation = Allocation.query.filter_by(
            application_id=current_application.id
        ).first()
        if allocation:
            allocated_room = Room.query.get(allocation.room_id)
    
    return render_template('student/dashboard.html',
                         application=current_application,
                         allocation=allocation,
                         allocated_room=allocated_room)

@app.route('/student/apply', methods=['GET', 'POST'])
@login_required
def apply_for_room():
    """
    Room application route for students (REQ-RA-01).
    
    Allows students to submit room allocation applications with preferences.
    Validates that student doesn't have a pending application.
    
    GET: Display application form
    POST: Process application submission
    """
    if not current_user.is_student():
        flash('Access denied. Student privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Check if student already has a pending application
    existing_app = Application.query.filter_by(
        student_id=current_user.id,
        status='pending'
    ).first()
    
    if existing_app:
        flash('You already have a pending application. Please wait for the allocation process.', 'warning')
        return redirect(url_for('student_dashboard'))
    
    # Check if student is already allocated
    existing_allocation = Allocation.query.join(Application).filter(
        Application.student_id == current_user.id
    ).first()
    
    if existing_allocation:
        flash('You have already been allocated a room.', 'info')
        return redirect(url_for('student_dashboard'))
    
    # Get available rooms for display
    available_rooms = Room.query.filter_by(status='available').all()
    
    if request.method == 'POST':
        room_type_preference = request.form.get('room_type_preference', '')
        special_requirements = request.form.get('special_requirements', '').strip()
        
        # Create new application
        new_application = Application(
            student_id=current_user.id,
            room_type_preference=room_type_preference,
            special_requirements=special_requirements,
            status='pending'
        )
        
        try:
            db.session.add(new_application)
            db.session.commit()
            flash('Your room application has been submitted successfully!', 'success')
            return redirect(url_for('student_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('student/apply.html', available_rooms=available_rooms)

@app.route('/student/status')
@login_required
def application_status():
    """
    Application status viewing route (REQ-RA-07).
    
    Displays detailed status of student's applications and allocation.
    """
    if not current_user.is_student():
        flash('Access denied. Student privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get all applications for this student
    applications = Application.query.filter_by(
        student_id=current_user.id
    ).order_by(Application.application_date.desc()).all()
    
    return render_template('student/status.html', applications=applications)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Student profile route for basic editable fields."""
    if not current_user.is_student():
        flash('Access denied. Student privileges required.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        contact_no = request.form.get('contact_no', '').strip()

        if not name:
            flash('Name is required.', 'danger')
            return render_template('student/profile.html')

        current_user.name = name
        current_user.contact_no = contact_no

        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('profile'))
        except Exception:
            db.session.rollback()
            flash('Unable to update profile right now. Please try again.', 'danger')

    return render_template('student/profile.html')

# =============================================================================
# ADMIN ROUTES
# =============================================================================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """
    Admin dashboard route.
    
    Displays overview statistics:
    - Total students, rooms, applications
    - Pending applications count
    - Available rooms count
    - Recent allocations
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get statistics
    total_students = User.query.filter_by(role='student').count()
    total_rooms = Room.query.count()
    available_rooms = Room.query.filter_by(status='available').count()
    pending_applications = Application.query.filter_by(status='pending').count()
    total_allocations = Allocation.query.count()
    
    # Get recent allocations
    recent_allocations = Allocation.query.order_by(
        Allocation.allocation_date.desc()
    ).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_rooms=total_rooms,
                         available_rooms=available_rooms,
                         pending_applications=pending_applications,
                         total_allocations=total_allocations,
                         recent_allocations=recent_allocations)

@app.route('/admin/rooms')
@login_required
def manage_rooms():
    """
    Room management route (REQ-RM-01, REQ-RM-02).
    
    Displays all rooms with their status and allows management.
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    rooms = Room.query.order_by(Room.room_number).all()
    return render_template('admin/rooms.html', rooms=rooms)


@app.route('/admin/students')
@login_required
def view_students():
    """Admin route to view all registered students."""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    students = User.query.filter_by(role='student').order_by(User.name).all()
    return render_template('admin/students.html', students=students)

@app.route('/admin/rooms/add', methods=['GET', 'POST'])
@login_required
def add_room():
    """
    Add new room route (REQ-RM-01).
    
    Allows admin to add new rooms to the inventory.
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        room_number = request.form.get('room_number', '').strip()
        capacity = request.form.get('capacity', type=int)
        room_type = request.form.get('room_type', '')
        floor = request.form.get('floor', type=int)
        amenities = request.form.get('amenities', '').strip()
        
        # Validation
        errors = validate_room_form_data(room_number, capacity, room_type)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/add_room.html')
        
        # Check if room number already exists
        if Room.query.filter_by(room_number=room_number).first():
            flash('Room number already exists.', 'danger')
            return render_template('admin/add_room.html')
        
        new_room = Room(
            room_number=room_number,
            capacity=capacity,
            room_type=room_type,
            floor=floor,
            amenities=amenities,
            status='available'
        )
        
        try:
            db.session.add(new_room)
            db.session.commit()
            flash(f'Room {room_number} added successfully!', 'success')
            return redirect(url_for('manage_rooms'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/add_room.html')

@app.route('/admin/rooms/edit/<int:room_id>', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    """
    Edit room route (REQ-RM-03).
    
    Allows admin to update room details and maintenance status.
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        room_number = request.form.get('room_number', '').strip()
        capacity = request.form.get('capacity', type=int)
        room_type = request.form.get('room_type', '')
        floor = request.form.get('floor', type=int)
        amenities = request.form.get('amenities', '').strip()
        status = request.form.get('status', 'available')

        errors = validate_room_form_data(room_number, capacity, room_type, status)
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/edit_room.html', room=room)

        room.room_number = room_number
        room.capacity = capacity
        room.room_type = room_type
        room.floor = floor
        room.amenities = amenities
        room.status = status
        
        try:
            db.session.commit()
            flash(f'Room {room.room_number} updated successfully!', 'success')
            return redirect(url_for('manage_rooms'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
    
    return render_template('admin/edit_room.html', room=room)


@app.route('/admin/delete_room/<int:room_id>', methods=['POST'])
@login_required
def delete_room(room_id):
    """Delete room only when it has no active occupants."""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    room = Room.query.get_or_404(room_id)

    if room.get_current_occupancy() > 0 or room.status == 'occupied':
        flash('Cannot delete an occupied room.', 'danger')
        return redirect(url_for('manage_rooms'))

    try:
        db.session.delete(room)
        db.session.commit()
        flash(f'Room {room.room_number} deleted successfully.', 'success')
    except Exception:
        db.session.rollback()
        flash('Unable to delete room right now. Please try again.', 'danger')

    return redirect(url_for('manage_rooms'))

@app.route('/admin/applications')
@login_required
def view_applications():
    """
    View all applications route.
    
    Displays all student applications with filtering options.
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status', 'all')
    
    query = Application.query.join(User).order_by(Application.application_date.desc())
    
    if status_filter != 'all':
        query = query.filter(Application.status == status_filter)
    
    applications = query.all()
    
    return render_template('admin/applications.html', 
                         applications=applications,
                         status_filter=status_filter)


@app.route('/admin/reject_application/<int:application_id>', methods=['POST'])
@login_required
def reject_application(application_id):
    """Simple rejection flow to keep status model and UI consistent."""
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))

    application = Application.query.get_or_404(application_id)
    if application.status == 'allocated':
        flash('Allocated applications cannot be rejected.', 'warning')
        return redirect(url_for('view_applications'))

    application.status = 'rejected'
    try:
        db.session.commit()
        flash(f'Application #{application.id} rejected.', 'info')
    except Exception:
        db.session.rollback()
        flash('Unable to reject application right now. Please try again.', 'danger')

    return redirect(url_for('view_applications'))

@app.route('/admin/run-allocation', methods=['POST'])
@login_required
def run_allocation():
    """
    Run room allocation algorithm route (REQ-RA-02, REQ-RA-03, REQ-RA-04).
    
    Executes the allocation algorithm:
    1. Groups applications by year (Year-Based Priority)
    2. Sorts within each year by CGPA (CGPA-Based Priority)
    3. Processes by submission time (FCFS)
    4. Enforces constraints (REQ-RA-05)
    
    This is the core algorithm implementation as per SRS Section 3.2.2
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Import allocation service
        from services.allocation_service import run_allocation
        
        # Run the allocation algorithm
        result = run_allocation()
        
        if result['success']:
            flash(f"Allocation completed successfully! {result['allocated_count']} students allocated, {result['waitlisted_count']} added to waitlist.", 'success')
        else:
            flash(f"Allocation completed with warnings: {result['message']}", 'warning')
        
        # Log admin action for audit (SEC-04)
        app.logger.info(f'Allocation run by admin: {current_user.email} at {datetime.now()}. Result: {result}')
        
    except Exception as e:
        flash(f'An error occurred during allocation: {str(e)}', 'danger')
        app.logger.error(f'Allocation error: {str(e)}')
    
    return redirect(url_for('view_allocations'))

@app.route('/admin/allocations')
@login_required
def view_allocations():
    """
    View all allocations route.
    
    Displays all room allocations with student and room details.
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    allocations = Allocation.query.join(Application).join(User).join(Room).order_by(
        Allocation.allocation_date.desc()
    ).all()
    
    return render_template('admin/allocations.html', allocations=allocations)

@app.route('/admin/reports')
@login_required
def reports():
    """
    Reports and analytics route (REQ-RM-05).
    
    Displays various reports:
    - Occupancy statistics
    - Room utilization by type
    - Allocation statistics by year
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Room occupancy statistics
    total_rooms = Room.query.count()
    available_rooms = Room.query.filter_by(status='available').count()
    occupied_rooms = Room.query.filter_by(status='occupied').count()
    maintenance_rooms = Room.query.filter_by(status='maintenance').count()
    
    # Room type distribution
    room_types = db.session.query(Room.room_type, db.func.count(Room.id)).group_by(Room.room_type).all()
    
    # Student distribution by year
    students_by_year = db.session.query(User.year_of_study, db.func.count(User.id)).filter_by(role='student').group_by(User.year_of_study).all()
    
    # Application statistics
    total_applications = Application.query.count()
    pending_applications = Application.query.filter_by(status='pending').count()
    allocated_applications = Application.query.filter_by(status='allocated').count()
    
    return render_template('admin/reports.html',
                         total_rooms=total_rooms,
                         available_rooms=available_rooms,
                         occupied_rooms=occupied_rooms,
                         maintenance_rooms=maintenance_rooms,
                         room_types=room_types,
                         students_by_year=students_by_year,
                         total_applications=total_applications,
                         pending_applications=pending_applications,
                         allocated_applications=allocated_applications)

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors."""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors."""
    db.session.rollback()  # Rollback any failed database transactions
    return render_template('errors/500.html'), 500

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================

def init_db():
    """
    Initialize the database with tables and optional default admin.
    """
    with app.app_context():
        # Create all tables
        db.create_all()

        # Create admin only when credentials are provided via environment variables.
        admin_email = os.getenv('DEFAULT_ADMIN_EMAIL')
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD')

        if admin_email and admin_password:
            existing_admin = User.query.filter_by(email=admin_email).first()
            if not existing_admin:
                admin = User(
                    email=admin_email,
                    password=admin_password,
                    name='System Administrator',
                    role='admin',
                    year_of_study=0,
                    cgpa=0.0,
                    gender='other'
                )
                db.session.add(admin)
                db.session.commit()
                print(f"Default admin created: {admin_email}")

# Run initialization when starting the app
init_db()

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    """
    Main entry point for the application.
    Runs the Flask development server.
    
    For production, use a WSGI server like Gunicorn.
    """
    app.run(debug=False, host='0.0.0.0', port=5000)
