import hashlib
import sqlite3
from datetime import datetime, timedelta
from database.db import get_db

def hash_password(password: str) -> str:
    """Simple SHA-256 password hashing for database authentication."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored hash."""
    return hash_password(password) == password_hash

# ---------------------------------------------------------------------------
# User Models & CRUD
# ---------------------------------------------------------------------------

def create_user(name: str, email: str, role: str, course: str, password: str, db_path=None):
    """
    Create a new user (class_rep, lecturer, or admin).
    Returns created user dict or raises ValueError if email exists or role invalid.
    """
    if role not in ('class_rep', 'lecturer', 'admin'):
        raise ValueError(f"Invalid role: {role}")
    
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    pwd_hash = hash_password(password)
    
    try:
        cursor.execute("""
            INSERT INTO users (name, email, role, course, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email.lower().strip(), role, course, pwd_hash))
        conn.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id, db_path=db_path)
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError(f"User with email '{email}' already exists.")
    finally:
        conn.close()

def get_user_by_email(email: str, db_path=None):
    """Retrieve user record by email."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: int, db_path=None):
    """Retrieve user record by ID."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Building & Room Models & CRUD
# ---------------------------------------------------------------------------

def create_building(name: str, latitude: float, longitude: float, db_path=None):
    """Insert a building record into the database."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO buildings (name, latitude, longitude)
        VALUES (?, ?, ?)
    """, (name, latitude, longitude))
    conn.commit()
    building_id = cursor.lastrowid
    conn.close()
    return building_id

def get_all_buildings(db_path=None):
    """Fetch all campus buildings."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buildings ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def create_room(name: str, building_id: int, capacity: int, latitude: float = None, longitude: float = None, db_path=None):
    """Insert a lecture room record into the database."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    # If room-specific lat/long not provided, fall back to building coordinates
    if latitude is None or longitude is None:
        cursor.execute("SELECT latitude, longitude FROM buildings WHERE id = ?", (building_id,))
        b_row = cursor.fetchone()
        if b_row:
            latitude = latitude or b_row['latitude']
            longitude = longitude or b_row['longitude']
            
    cursor.execute("""
        INSERT INTO rooms (name, building_id, capacity, latitude, longitude)
        VALUES (?, ?, ?, ?, ?)
    """, (name, building_id, capacity, latitude, longitude))
    conn.commit()
    room_id = cursor.lastrowid
    conn.close()
    return room_id

def get_all_rooms(building_id: int = None, min_capacity: int = None, db_path=None):
    """Fetch rooms with optional building or minimum capacity filter."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT r.*, b.name as building_name
        FROM rooms r
        JOIN buildings b ON r.building_id = b.id
        WHERE 1=1
    """
    params = []
    
    if building_id:
        query += " AND r.building_id = ?"
        params.append(building_id)
        
    if min_capacity:
        query += " AND r.capacity >= ?"
        params.append(min_capacity)
        
    query += " ORDER BY b.name ASC, r.name ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_room_by_id(room_id: int, db_path=None):
    """Fetch room by ID along with building details."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, b.name as building_name
        FROM rooms r
        JOIN buildings b ON r.building_id = b.id
        WHERE r.id = ?
    """, (room_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Double-Booking Prevention & Booking Operations
# ---------------------------------------------------------------------------

def check_booking_conflict(room_id: int, date_str: str, start_time_str: str, end_time_str: str, exclude_booking_id: int = None, db_path=None):
    """
    Check if a booking time range overlaps with existing confirmed bookings for a given room.
    Overlap logic: (start_time < new_end_time) AND (end_time > new_start_time).
    Returns list of conflicting bookings (empty if no conflict).
    """
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT b.*, u.name as user_name, u.role as user_role
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.room_id = ?
          AND b.date = ?
          AND b.status = 'confirmed'
          AND (b.start_time < ? AND b.end_time > ?)
    """
    params = [room_id, date_str, end_time_str, start_time_str]
    
    if exclude_booking_id:
        query += " AND b.id != ?"
        params.append(exclude_booking_id)
        
    cursor.execute(query, params)
    conflicts = cursor.fetchall()
    conn.close()
    return [dict(c) for c in conflicts]

def create_booking(room_id: int, user_id: int, course_unit: str, date_str: str, start_time_str: str, end_time_str: str, db_path=None):
    """
    Create a new room booking after verifying no double-booking overlap exists.
    Raises ValueError if double-booking conflict occurs or times are invalid.
    """
    if start_time_str >= end_time_str:
        raise ValueError("Booking start time must be earlier than end time.")
        
    conflicts = check_booking_conflict(room_id, date_str, start_time_str, end_time_str, db_path=db_path)
    if conflicts:
        conflict_info = conflicts[0]
        raise ValueError(
            f"Double-booking prevented! Room is already booked for '{conflict_info['course_unit']}' "
            f"from {conflict_info['start_time']} to {conflict_info['end_time']}."
        )
        
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO bookings (room_id, user_id, course_unit, date, start_time, end_time, status)
        VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
    """, (room_id, user_id, course_unit, date_str, start_time_str, end_time_str))
    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()
    return get_booking_by_id(booking_id, db_path=db_path)

def get_booking_by_id(booking_id: int, db_path=None):
    """Fetch booking record by ID with room and user details."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, r.name as room_name, bldg.name as building_name, u.name as user_name, u.email as user_email
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        JOIN buildings bldg ON r.building_id = bldg.id
        JOIN users u ON b.user_id = u.id
        WHERE b.id = ?
    """, (booking_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def cancel_booking(booking_id: int, user_id: int = None, db_path=None):
    """Cancel a confirmed booking."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute("SELECT user_id FROM bookings WHERE id = ?", (booking_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise ValueError("Booking not found.")
        if row['user_id'] != user_id:
            conn.close()
            raise PermissionError("You can only cancel your own bookings.")
            
    cursor.execute("""
        UPDATE bookings
        SET status = 'cancelled'
        WHERE id = ?
    """, (booking_id,))
    conn.commit()
    conn.close()
    return True

def get_bookings_by_room(room_id: int, date_str: str = None, db_path=None):
    """Fetch all confirmed bookings for a specific room."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    query = """
        SELECT b.*, u.name as user_name, u.role as user_role
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.room_id = ? AND b.status = 'confirmed'
    """
    params = [room_id]
    
    if date_str:
        query += " AND b.date = ?"
        params.append(date_str)
        
    query += " ORDER BY b.date ASC, b.start_time ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_room_status(room_id: int, date_str: str, time_str: str, db_path=None):
    """
    Calculates room occupancy status at a specific date & time.
    Returns:
    - 'occupied' (red): currently occupied by a confirmed booking
    - 'booked_soon' (yellow): will become occupied within 60 minutes
    - 'free' (green): free now and for at least the next hour
    Also returns next_free_time or current_booking details for map popup markers.
    """
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    # 1. Check if occupied currently
    cursor.execute("""
        SELECT b.*, u.name as user_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.room_id = ?
          AND b.date = ?
          AND b.status = 'confirmed'
          AND (b.start_time <= ? AND b.end_time > ?)
    """, (room_id, date_str, time_str, time_str))
    current = cursor.fetchone()
    
    if current:
        conn.close()
        return {
            'status': 'occupied',
            'color': 'red',
            'current_booking': dict(current),
            'next_free_time': current['end_time']
        }
        
    # 2. Check if starting within next 60 mins
    # Calculate target_time + 1 hr
    try:
        t_dt = datetime.strptime(time_str, '%H:%M')
        t_soon_dt = t_dt + timedelta(hours=1)
        soon_time_str = t_soon_dt.strftime('%H:%M')
    except ValueError:
        soon_time_str = time_str
        
    cursor.execute("""
        SELECT b.*, u.name as user_name
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        WHERE b.room_id = ?
          AND b.date = ?
          AND b.status = 'confirmed'
          AND (b.start_time > ? AND b.start_time <= ?)
        ORDER BY b.start_time ASC
    """, (room_id, date_str, time_str, soon_time_str))
    soon = cursor.fetchone()
    
    conn.close()
    
    if soon:
        return {
            'status': 'booked_soon',
            'color': 'yellow',
            'next_booking': dict(soon),
            'next_free_time': f"Free until {soon['start_time']}"
        }
        
    return {
        'status': 'free',
        'color': 'green',
        'next_free_time': 'Free all day'
    }
