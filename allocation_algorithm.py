"""
Hostel Room Allocation System - Allocation Algorithm

This module implements the core room allocation algorithm as specified in
SRS Section 3.2.2: Allocation Algorithms.

Algorithm Overview (Hierarchical Processing):
1. Year-Based Priority (REQ-RA-02)
   - Final Year (4th) > Third Year (3rd) > Second Year (2nd) > First Year (1st)
   - Ensures continuity of accommodation for continuing students

2. CGPA-Based Priority (REQ-RA-03)
   - Within each year, students ranked by CGPA (descending)
   - Higher CGPA = Higher priority
   - Incentivizes academic performance

3. First-Come-First-Serve (FCFS) (REQ-RA-04)
   - Within same year and CGPA, process by application timestamp
   - Ensures fairness within priority tiers

4. Constraints Enforcement (REQ-RA-05)
   - Gender-specific allocation
   - Special needs accommodation
   - Room type preference matching
   - Capacity limits

Tie-Breaking Rules:
- Same year + same CGPA → FCFS (application timestamp)
- Same timestamp → Random selection
- No room available → Add to waitlist
"""

from datetime import datetime
from models import User, Room, Application, Allocation, RoomOccupant
from extensions import db
import random


def run_allocation_algorithm():
    """
    Main allocation algorithm function.
    
    This function processes all pending applications and allocates rooms
    based on the hierarchical priority system defined in the SRS.
    
    Returns:
        dict: Result with keys:
            - success (bool): Whether allocation completed successfully
            - allocated_count (int): Number of students allocated
            - waitlisted_count (int): Number of students waitlisted
            - message (str): Status message
    """
    
    # Initialize counters
    allocated_count = 0
    waitlisted_count = 0
    
    try:
        # Step 1: Get all pending applications
        pending_apps = Application.query.filter_by(status='pending').all()
        
        if not pending_apps:
            return {
                'success': True,
                'allocated_count': 0,
                'waitlisted_count': 0,
                'message': 'No pending applications to process.'
            }
        
        # Step 2: Get all available rooms
        available_rooms = Room.query.filter_by(status='available').all()
        
        if not available_rooms:
            # No rooms available - add all to waitlist
            for app in pending_apps:
                app.status = 'waitlisted'
                waitlisted_count += 1
            db.session.commit()
            return {
                'success': True,
                'allocated_count': 0,
                'waitlisted_count': waitlisted_count,
                'message': 'No rooms available. All applications added to waitlist.'
            }
        
        # Step 3: Sort applications by priority
        # This implements Year-Based + CGPA-Based + FCFS sorting
        sorted_apps = sort_applications_by_priority(pending_apps)
        
        # Step 4: Process each application
        for application in sorted_apps:
            # Get student details
            student = User.query.get(application.student_id)
            
            if not student:
                continue
            
            # Find suitable room for this student
            allocated_room = find_suitable_room(student, application, available_rooms)
            
            if allocated_room:
                # Allocate the room
                allocate_room_to_student(application, allocated_room, 'system')
                allocated_count += 1
                
                # Update room status if full
                if allocated_room.is_full():
                    allocated_room.status = 'occupied'
                    # Remove from available list
                    available_rooms = [r for r in available_rooms if r.id != allocated_room.id]
            else:
                # No suitable room - add to waitlist
                application.status = 'waitlisted'
                waitlisted_count += 1
        
        # Commit all changes
        db.session.commit()
        
        return {
            'success': True,
            'allocated_count': allocated_count,
            'waitlisted_count': waitlisted_count,
            'message': f'Allocation completed. {allocated_count} allocated, {waitlisted_count} waitlisted.'
        }
        
    except Exception as e:
        # Rollback on error (SAF-02)
        db.session.rollback()
        return {
            'success': False,
            'allocated_count': allocated_count,
            'waitlisted_count': waitlisted_count,
            'message': f'Error during allocation: {str(e)}'
        }


def sort_applications_by_priority(applications):
    """
    Sort applications by hierarchical priority.
    
    Priority Order:
    1. Year of Study (descending) - Final Year first
    2. CGPA (descending) - Higher CGPA first
    3. Application Date (ascending) - Earlier application first (FCFS)
    
    Args:
        applications: List of Application objects
        
    Returns:
        List of sorted Application objects
    """
    
    def get_sort_key(app):
        """
        Generate sort key for an application.
        
        Returns tuple: (-year, -cgpa, application_date)
        Negative for descending order
        """
        student = User.query.get(app.student_id)
        
        if not student:
            return (0, 0, app.application_date)
        
        # Priority: Year (4 > 3 > 2 > 1)
        year_priority = -(student.year_of_study or 0)
        
        # Priority: CGPA (higher is better)
        cgpa_priority = -(student.cgpa or 0)
        
        # FCFS: Earlier application gets priority
        application_time = app.application_date
        
        return (year_priority, cgpa_priority, application_time)
    
    # Sort applications using the custom key
    return sorted(applications, key=get_sort_key)


def find_suitable_room(student, application, available_rooms):
    """
    Find a suitable room for a student based on constraints (REQ-RA-05).
    
    Constraints Checked:
    1. Gender-specific allocation
    2. Room type preference matching
    3. Special needs (ground floor for disabled)
    4. Room capacity availability
    
    Args:
        student: User object (the student)
        application: Application object
        available_rooms: List of available Room objects
        
    Returns:
        Room object if suitable room found, None otherwise
    """
    
    # Filter rooms based on constraints
    suitable_rooms = []
    
    for room in available_rooms:
        # Check 1: Room has vacancy
        if room.is_full():
            continue
        
        # Check 2: Gender constraint
        # Get current occupants' gender
        current_occupants = RoomOccupant.query.filter_by(
            room_id=room.id,
            moved_out_date=None
        ).all()
        
        if current_occupants:
            # Check if any occupant has different gender
            occupant_ids = [o.student_id for o in current_occupants]
            occupants = User.query.filter(User.id.in_(occupant_ids)).all()
            
            for occupant in occupants:
                if occupant.gender != student.gender:
                    # Gender mismatch - skip this room
                    break
            else:
                # All occupants have same gender
                suitable_rooms.append(room)
        else:
            # Room is empty - any gender can occupy
            suitable_rooms.append(room)
    
    # If no rooms pass gender check, return None
    if not suitable_rooms:
        return None
    
    # Check 3: Room type preference
    if application.room_type_preference:
        preferred_rooms = [r for r in suitable_rooms 
                          if r.room_type == application.room_type_preference]
        if preferred_rooms:
            suitable_rooms = preferred_rooms
    
    # Check 4: Special requirements (ground floor)
    if application.special_requirements:
        requirements = application.special_requirements.lower()
        if 'ground' in requirements or 'disabled' in requirements or 'wheelchair' in requirements:
            ground_floor_rooms = [r for r in suitable_rooms if r.floor == 0 or r.floor == 1]
            if ground_floor_rooms:
                suitable_rooms = ground_floor_rooms
    
    # Return the first suitable room (or random for fairness)
    if suitable_rooms:
        # Sort by capacity utilization (prefer rooms with more existing occupants)
        # This helps fill rooms efficiently
        suitable_rooms.sort(key=lambda r: r.get_current_occupancy(), reverse=True)
        return suitable_rooms[0]
    
    return None


def allocate_room_to_student(application, room, allotted_by_email):
    """
    Allocate a room to a student.
    
    This function:
    1. Creates an Allocation record
    2. Creates a RoomOccupant record
    3. Updates application status
    4. Updates room status if needed
    
    Args:
        application: Application object
        room: Room object to allocate
        allotted_by_email: Email of admin who ran allocation (for audit)
    """
    
    # Capture occupancy before adding the new occupant.
    # This avoids checking is_full() before pending inserts are reflected.
    current_occupancy = room.get_current_occupancy()

    # Create allocation record
    allocation = Allocation(
        application_id=application.id,
        room_id=room.id,
        allotted_by=allotted_by_email
    )
    db.session.add(allocation)
    
    # Create room occupant record
    occupant = RoomOccupant(
        room_id=room.id,
        student_id=application.student_id
    )
    db.session.add(occupant)
    
    # Update application status
    application.status = 'allocated'
    
    # Update room status if this allocation fills the room.
    if current_occupancy + 1 >= room.capacity:
        room.status = 'occupied'


def process_waitlist():
    """
    Process waitlisted applications when rooms become available.
    
    This function can be called when:
    - A student moves out
    - New rooms are added
    - Room maintenance is completed
    
    Returns:
        dict: Result with number of waitlisted students allocated
    """
    
    waitlisted_apps = Application.query.filter_by(status='waitlisted').all()
    available_rooms = Room.query.filter_by(status='available').all()
    
    allocated_count = 0
    
    # Sort waitlisted applications by priority
    sorted_apps = sort_applications_by_priority(waitlisted_apps)
    
    for application in sorted_apps:
        student = User.query.get(application.student_id)
        
        if not student:
            continue
        
        # Try to find a suitable room
        allocated_room = find_suitable_room(student, application, available_rooms)
        
        if allocated_room:
            allocate_room_to_student(application, allocated_room, 'system')
            allocated_count += 1
            
            # Update available rooms list
            if allocated_room.is_full():
                available_rooms = [r for r in available_rooms if r.id != allocated_room.id]
    
    db.session.commit()
    
    return {
        'success': True,
        'allocated_count': allocated_count,
        'message': f'{allocated_count} waitlisted students allocated.'
    }


def get_allocation_summary():
    """
    Get a summary of current allocations for reporting.
    
    Returns:
        dict: Summary statistics
    """
    
    total_allocations = Allocation.query.count()
    
    # Allocations by year
    from sqlalchemy import func
    allocations_by_year = db.session.query(
        User.year_of_study,
        func.count(Allocation.id)
    ).join(Application, Allocation.application_id == Application.id).\
    join(User, Application.student_id == User.id).\
    group_by(User.year_of_study).all()
    
    # Allocations by room type
    allocations_by_room_type = db.session.query(
        Room.room_type,
        func.count(Allocation.id)
    ).join(Room, Allocation.room_id == Room.id).\
    group_by(Room.room_type).all()
    
    return {
        'total_allocations': total_allocations,
        'by_year': allocations_by_year,
        'by_room_type': allocations_by_room_type
    }


def validate_no_duplicate_allocation(student_id):
    """
    Check if a student already has an active allocation.
    
    This prevents duplicate allocations (SAF-03).
    
    Args:
        student_id: ID of the student to check
        
    Returns:
        bool: True if student has no active allocation, False otherwise
    """
    
    existing_allocation = Allocation.query.join(Application).filter(
        Application.student_id == student_id
    ).first()
    
    return existing_allocation is None


# =============================================================================
# ALGORITHM TESTING / DEBUGGING FUNCTIONS
# =============================================================================

def print_allocation_queue():
    """
    Print the current allocation queue for debugging.
    Shows pending applications sorted by priority.
    """
    
    pending_apps = Application.query.filter_by(status='pending').all()
    sorted_apps = sort_applications_by_priority(pending_apps)
    
    print("\n=== ALLOCATION QUEUE ===")
    print(f"{'Rank':<6}{'Student':<25}{'Year':<6}{'CGPA':<8}{'Applied':<20}")
    print("-" * 70)
    
    for i, app in enumerate(sorted_apps, 1):
        student = User.query.get(app.student_id)
        if student:
            print(f"{i:<6}{student.name:<25}{student.year_of_study or 'N/A':<6}"
                  f"{student.cgpa or 'N/A':<8}{app.application_date.strftime('%Y-%m-%d %H:%M'):<20}")
    
    print("-" * 70)
    print(f"Total pending applications: {len(sorted_apps)}\n")


if __name__ == '__main__':
    # Test the algorithm
    print_allocation_queue()
