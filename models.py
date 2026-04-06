"""
Hostel Room Allocation System - Database Models

This file defines all database tables (models) for the system.
It uses SQLAlchemy ORM for database operations.

Entities (as per SRS Appendix B.2 ER Diagram):
- User (Student, Admin)
- Room
- Application
- Allocation
- RoomOccupant

Relationships:
- User (1) → Application (N)
- Application (1) → Allocation (1)
- Room (1) → Allocation (N)
- User (1) → RoomOccupant (N)
- Room (1) → RoomOccupant (N)
"""

from flask_login import UserMixin
from datetime import datetime
from extensions import db, bcrypt

# =============================================================================
# USER MODEL
# =============================================================================

class User(UserMixin, db.Model):
    """
    User model for both students and administrators.
    
    This model stores:
    - Authentication info (email, password_hash)
    - Profile info (name, contact)
    - Student-specific info (year_of_study, cgpa, gender)
    - Role (student/admin for access control)
    
    Attributes:
        id: Primary key, auto-increment
        email: Unique email address (used for login)
        password_hash: Hashed password (bcrypt)
        name: Full name of the user
        role: 'student' or 'admin'
        year_of_study: 1-4 (for students only)
        cgpa: Cumulative GPA 0-10 (for students only)
        gender: 'male', 'female', 'other' (for room allocation constraints)
        contact_no: Phone number
        created_at: Account creation timestamp
        is_active: Whether account is active
    """
    
    __tablename__ = 'users'  # Table name in database
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Authentication Fields
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Profile Fields
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    
    # Student-Specific Fields (for allocation algorithm)
    year_of_study = db.Column(db.Integer, nullable=True)  # 1, 2, 3, 4
    cgpa = db.Column(db.Float, nullable=True)  # 0.0 to 10.0
    gender = db.Column(db.String(10), nullable=True)  # male, female, other
    contact_no = db.Column(db.String(15), nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships (defined for easy navigation between related data)
    # A user (student) can have multiple applications
    applications = db.relationship('Application', backref='student', lazy=True)
    
    # A user can be occupant of multiple rooms (over time)
    room_occupancies = db.relationship('RoomOccupant', backref='student', lazy=True)
    
    def __init__(self, email, password, name, role='student', 
                 year_of_study=None, cgpa=None, gender=None, contact_no=None):
        """
        Initialize a new User.
        
        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            name: User's full name
            role: 'student' or 'admin'
            year_of_study: 1-4 (for students)
            cgpa: 0.0-10.0 (for students)
            gender: 'male', 'female', 'other' (for students)
            contact_no: Phone number
        """
        self.email = email.lower().strip()
        self.password = password  # Uses setter to hash
        self.name = name.strip()
        self.role = role
        self.year_of_study = year_of_study
        self.cgpa = cgpa
        self.gender = gender
        self.contact_no = contact_no
    
    @property
    def password(self):
        """Prevent reading password directly."""
        raise AttributeError('Password is not readable')
    
    @password.setter
    def password(self, plain_text_password):
        """
        Hash and store password using bcrypt (SEC-01).
        
        bcrypt automatically handles salt generation and storage.
        """
        if plain_text_password:
            self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')
    
    def check_password(self, plain_text_password):
        """
        Verify password against stored hash (SEC-01).
        
        Args:
            plain_text_password: Password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.check_password_hash(self.password_hash, plain_text_password)
    
    def is_student(self):
        """Check if user is a student."""
        return self.role == 'student'
    
    def is_admin(self):
        """Check if user is an administrator."""
        return self.role == 'admin'
    
    def get_priority_score(self):
        """
        Calculate priority score for allocation algorithm.
        
        Higher score = higher priority
        Formula: (year_of_study * 100) + cgpa
        
        Returns:
            Priority score as float
        """
        if self.year_of_study and self.cgpa:
            return (self.year_of_study * 100) + self.cgpa
        return 0
    
    def __repr__(self):
        """String representation of User."""
        return f'<User {self.email} ({self.role})>'


# =============================================================================
# ROOM MODEL
# =============================================================================

class Room(db.Model):
    """
    Room model for hostel room inventory.
    
    This model stores:
    - Room identification (room_number)
    - Capacity and type (single/double/triple)
    - Location (floor)
    - Status (available/occupied/maintenance)
    - Amenities
    
    Attributes:
        id: Primary key
        room_number: Unique room identifier (e.g., "A-101", "B-205")
        capacity: Maximum number of occupants
        room_type: 'single', 'double', 'triple' (REQ-RM-04)
        floor: Floor number
        status: 'available', 'occupied', 'maintenance' (REQ-RM-02, REQ-RM-03)
        amenities: Comma-separated list of amenities
        created_at: When room was added to system
    """
    
    __tablename__ = 'rooms'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Room Details
    room_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    room_type = db.Column(db.String(20), nullable=False, default='double')  # single/double/triple
    floor = db.Column(db.Integer, nullable=True)
    
    # Status (REQ-RM-02, REQ-RM-03)
    status = db.Column(db.String(20), nullable=False, default='available')
    # Possible values: 'available', 'occupied', 'maintenance'
    
    # Additional Info
    amenities = db.Column(db.Text, nullable=True)  # e.g., "AC, WiFi, Attached Bath"
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    # A room can have multiple allocations (over time)
    allocations = db.relationship('Allocation', backref='room', lazy=True)
    
    # A room can have multiple occupants
    occupants = db.relationship('RoomOccupant', backref='room', lazy=True)
    
    def __init__(self, room_number, capacity=2, room_type='double', 
                 floor=None, amenities=None, status='available'):
        """
        Initialize a new Room.
        
        Args:
            room_number: Unique room identifier
            capacity: Maximum occupants
            room_type: 'single', 'double', 'triple'
            floor: Floor number
            amenities: Comma-separated amenities list
            status: 'available', 'occupied', 'maintenance'
        """
        self.room_number = room_number.strip()
        self.capacity = capacity
        self.room_type = room_type
        self.floor = floor
        self.amenities = amenities
        self.status = status
    
    def get_current_occupancy(self):
        """
        Get current number of occupants in this room.
        
        Returns:
            Integer count of current occupants
        """
        return RoomOccupant.query.filter_by(
            room_id=self.id,
            moved_out_date=None
        ).count()
    
    def is_full(self):
        """Check if room is at full capacity."""
        return self.get_current_occupancy() >= self.capacity
    
    def has_vacancy(self):
        """Check if room has available space."""
        return self.status == 'available' and not self.is_full()
    
    def __repr__(self):
        """String representation of Room."""
        return f'<Room {self.room_number} ({self.status})>'


# =============================================================================
# APPLICATION MODEL
# =============================================================================

class Application(db.Model):
    """
    Room Application model for student room requests.
    
    This model stores:
    - Student reference (who applied)
    - Application timestamp (for FCFS ordering)
    - Preferences (room type, special requirements)
    - Status (pending/allocated/waitlisted/rejected)
    - Priority score (calculated for sorting)
    
    Attributes:
        id: Primary key
        student_id: Foreign key to User
        application_date: When application was submitted (for FCFS)
        room_type_preference: Preferred room type
        special_requirements: Any special needs
        status: Application status
        priority_score: Calculated priority for sorting
    """
    
    __tablename__ = 'applications'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Key - Student who applied
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Application Details
    application_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    room_type_preference = db.Column(db.String(20), nullable=True)  # single/double/triple
    special_requirements = db.Column(db.Text, nullable=True)  # e.g., "Ground floor needed"
    
    # Status
    status = db.Column(db.String(20), nullable=False, default='pending')
    # Possible values: 'pending', 'allocated', 'waitlisted', 'rejected'
    
    # Priority Score (calculated for sorting)
    priority_score = db.Column(db.Float, nullable=True)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # An application can result in one allocation
    allocation = db.relationship('Allocation', backref='application', uselist=False, lazy=True)
    
    def __init__(self, student_id, room_type_preference=None, 
                 special_requirements=None, status='pending'):
        """
        Initialize a new Application.
        
        Args:
            student_id: ID of the student applying
            room_type_preference: Preferred room type
            special_requirements: Any special needs
            status: Initial status ('pending')
        """
        self.student_id = student_id
        self.room_type_preference = room_type_preference
        self.special_requirements = special_requirements
        self.status = status
        
        # Calculate priority score based on student
        student = User.query.get(student_id)
        if student:
            self.priority_score = student.get_priority_score()
    
    def get_student_details(self):
        """Get student details for this application."""
        return User.query.get(self.student_id)
    
    def __repr__(self):
        """String representation of Application."""
        return f'<Application {self.id} by Student {self.student_id} ({self.status})>'


# =============================================================================
# ALLOCATION MODEL
# =============================================================================

class Allocation(db.Model):
    """
    Room Allocation model for assigned rooms.
    
    This model stores:
    - Application reference (which application was allocated)
    - Room reference (which room was allocated)
    - Allocation timestamp
    - Who allocated (for audit - SEC-04)
    
    Attributes:
        id: Primary key
        application_id: Foreign key to Application
        room_id: Foreign key to Room
        allocation_date: When allocation was made
        allotted_by: Email of admin who ran allocation
    """
    
    __tablename__ = 'allocations'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False, unique=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    
    # Allocation Details
    allocation_date = db.Column(db.DateTime, default=datetime.utcnow)
    allotted_by = db.Column(db.String(120), nullable=True)  # Admin email for audit (SEC-04)
    
    def __init__(self, application_id, room_id, allotted_by=None):
        """
        Initialize a new Allocation.
        
        Args:
            application_id: ID of the application being allocated
            room_id: ID of the room being allocated
            allotted_by: Email of admin who made allocation (for audit)
        """
        self.application_id = application_id
        self.room_id = room_id
        self.allotted_by = allotted_by
    
    def get_student(self):
        """Get student who was allocated this room."""
        application = Application.query.get(self.application_id)
        if application:
            return User.query.get(application.student_id)
        return None
    
    def __repr__(self):
        """String representation of Allocation."""
        return f'<Allocation {self.id} (App: {self.application_id}, Room: {self.room_id})>'


# =============================================================================
# ROOM OCCUPANT MODEL
# =============================================================================

class RoomOccupant(db.Model):
    """
    Room Occupant model for tracking who is currently in which room.
    
    This model stores:
    - Room reference
    - Student reference
    - Move-in and move-out dates (REQ-RM-05)
    
    This enables occupancy history tracking.
    
    Attributes:
        id: Primary key
        room_id: Foreign key to Room
        student_id: Foreign key to User
        moved_in_date: When student moved in
        moved_out_date: When student moved out (NULL if currently occupying)
    """
    
    __tablename__ = 'room_occupants'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Occupancy Dates
    moved_in_date = db.Column(db.DateTime, default=datetime.utcnow)
    moved_out_date = db.Column(db.DateTime, nullable=True)
    
    def __init__(self, room_id, student_id, moved_in_date=None):
        """
        Initialize a new RoomOccupant.
        
        Args:
            room_id: ID of the room
            student_id: ID of the student
            moved_in_date: When student moved in (default: now)
        """
        self.room_id = room_id
        self.student_id = student_id
        if moved_in_date:
            self.moved_in_date = moved_in_date
    
    def is_current(self):
        """Check if this is a current occupancy (not moved out)."""
        return self.moved_out_date is None
    
    def move_out(self):
        """Mark occupant as moved out."""
        self.moved_out_date = datetime.utcnow()
    
    def __repr__(self):
        """String representation of RoomOccupant."""
        status = 'Current' if self.is_current() else 'Past'
        return f'<RoomOccupant {self.id} ({status})>'


# =============================================================================
# DATABASE HELPER FUNCTIONS
# =============================================================================

def get_room_statistics():
    """
    Get room occupancy statistics for reports (REQ-RM-05).
    
    Returns:
        Dictionary with room statistics
    """
    total = Room.query.count()
    available = Room.query.filter_by(status='available').count()
    occupied = Room.query.filter_by(status='occupied').count()
    maintenance = Room.query.filter_by(status='maintenance').count()
    
    return {
        'total': total,
        'available': available,
        'occupied': occupied,
        'maintenance': maintenance,
        'occupancy_rate': (occupied / total * 100) if total > 0 else 0
    }


def get_application_statistics():
    """
    Get application statistics for reports.
    
    Returns:
        Dictionary with application statistics
    """
    total = Application.query.count()
    pending = Application.query.filter_by(status='pending').count()
    allocated = Application.query.filter_by(status='allocated').count()
    waitlisted = Application.query.filter_by(status='waitlisted').count()
    rejected = Application.query.filter_by(status='rejected').count()
    
    return {
        'total': total,
        'pending': pending,
        'allocated': allocated,
        'waitlisted': waitlisted,
        'rejected': rejected
    }


def get_students_by_year():
    """
    Get student distribution by year of study.
    
    Returns:
        List of tuples (year, count)
    """
    from sqlalchemy import func
    return db.session.query(User.year_of_study, func.count(User.id)).\
        filter_by(role='student').\
        group_by(User.year_of_study).\
        order_by(User.year_of_study).all()
