import hashlib
import sqlite3
import re
from datetime import datetime, timedelta
from database.db import get_db

try:
    from werkzeug.security import generate_password_hash, check_password_hash
    HAS_WERKZEUG = True
except ImportError:
    HAS_WERKZEUG = False

# ---------------------------------------------------------------------------
# Password Hashing & Verification
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Simple SHA-256 password hashing for database authentication."""
    """Hash password using Werkzeug scrypt/pbkdf2 if available, or fallback to SHA-256."""
    if HAS_WERKZEUG:
        return generate_password_hash(password)
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against stored hash."""
    return hash_password(password) == password_hash
    """Verify password against stored hash (supports both Werkzeug hashes and SHA-256)."""
    if not password or not password_hash:
        return False
    if HAS_WERKZEUG and (password_hash.startswith('scrypt:') or password_hash.startswith('pbkdf2:')):
        return check_password_hash(password_hash, password)
    # Fallback to SHA-256 comparison
    return hashlib.sha256(password.encode('utf-8')).hexdigest() == password_hash

# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------

def validate_date(date_str: str) -> str:
    """Validate date format (YYYY-MM-DD) and return normalized date string."""
    if not date_str or not isinstance(date_str, str):
        raise ValueError("Invalid date: date string is required.")
    date_str = date_str.strip()
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD.")

def validate_time(time_str: str) -> str:
    """Validate time format (HH:MM or H:MM) and return normalized 24-hour HH:MM string."""
    if not time_str or not isinstance(time_str, str):
        raise ValueError("Invalid time: time string is required.")
    time_str = time_str.strip()
    # Normalize formats like 8:00 to 08:00
    match = re.match(r'^(\d{1,2}):(\d{2})$', time_str)
    if not match:
        raise ValueError(f"Invalid time format '{time_str}'. Expected HH:MM in 24-hour format.")
    hours, minutes = int(match.group(1)), int(match.group(2))
    if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
        raise ValueError(f"Invalid time '{time_str}'. Hours must be 0-23 and minutes 0-59.")
    return f"{hours:02d}:{minutes:02d}"

# ---------------------------------------------------------------------------
# User Models & CRUD
# ---------------------------------------------------------------------------

def create_user(name: str, email: str, role: str, course: str, password: str, db_path=None):
def create_user(name: str, email: str, role: str, course: str, password: str, allow_admin: bool = False, db_path=None):
    """
    Create a new user (class_rep, lecturer, or admin).
    Returns created user dict or raises ValueError if email exists or role invalid.
    Returns created user dict or raises ValueError if email exists, role is invalid, or admin registration attempted without permission.
    """
    if not name or not name.strip():
        raise ValueError("Name cannot be empty.")
    if not email or not email.strip() or '@' not in email:
        raise ValueError("Valid email address is required.")
    if not password:
        raise ValueError("Password cannot be empty.")

    role = role.strip().lower() if role else ''
    if role not in ('class_rep', 'lecturer', 'admin'):
        raise ValueError(f"Invalid role: {role}")
        raise ValueError(f"Invalid role: {role}. Must be class_rep, lecturer, or admin.")
    
    if role == 'admin' and not allow_admin:
        raise ValueError("Public registration for administrator accounts is prohibited.")

    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    pwd_hash = hash_password(password)
    
    try:
        cursor = conn.cursor()
        pwd_hash = hash_password(password)
        cursor.execute("""
            INSERT INTO users (name, email, role, course, password_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email.lower().strip(), role, course, pwd_hash))
        """, (name.strip(), email.lower().strip(), role, course.strip() if course else '', pwd_hash))
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
    if not email:
        return None
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_user_by_id(user_id: int, db_path=None):
    """Retrieve user record by ID."""
    if not user_id:
        return None
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Building & Room Models & CRUD
# ---------------------------------------------------------------------------

def create_building(name: str, latitude: float, longitude: float, db_path=None):
    """Insert a building record into the database."""
    if not name or not name.strip():
        raise ValueError("Building name cannot be empty.")
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
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO buildings (name, latitude, longitude)
            VALUES (?, ?, ?)
        """, (name.strip(), float(latitude), float(longitude)))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def get_all_buildings(db_path=None):
    """Fetch all campus buildings."""
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM buildings ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM buildings ORDER BY name ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def create_room(name: str, building_id: int, capacity: int, latitude: float = None, longitude: float = None, db_path=None):
    """Insert a lecture room record into the database."""
    if not name or not name.strip():
        raise ValueError("Room name cannot be empty.")
    if capacity <= 0:
        raise ValueError("Room capacity must be greater than zero.")

    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    # If room-specific lat/long not provided, fall back to building coordinates
    if latitude is None or longitude is None:
    try:
        cursor = conn.cursor()
        # Ensure building exists
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
        if not b_row:
            raise ValueError(f"Building with ID {building_id} does not exist.")
        
        # If room-specific lat/long not provided, fall back to building coordinates
        if latitude is None or longitude is None:
            latitude = latitude if latitude is not None else b_row['latitude']
            longitude = longitude if longitude is not None else b_row['longitude']
                
        cursor.execute("""
            INSERT INTO rooms (name, building_id, capacity, latitude, longitude)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), building_id, int(capacity), float(latitude), float(longitude)))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

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
    try:
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
        if min_capacity is not None and min_capacity > 0:
            query += " AND r.capacity >= ?"
            params.append(min_capacity)
            
        query += " ORDER BY b.name ASC, r.name ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

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
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, b.name as building_name
            FROM rooms r
            JOIN buildings b ON r.building_id = b.id
            WHERE r.id = ?
        """, (room_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Double-Booking Prevention & Booking Operations
# ---------------------------------------------------------------------------

def check_booking_conflict(room_id: int, date_str: str, start_time_str: str, end_time_str: str, exclude_booking_id: int = None, db_path=None):
def check_booking_conflict(room_id: int, date_str: str, start_time_str: str, end_time_str: str, exclude_booking_id: int = None, db_path=None, cursor=None):
    """
    Check if a booking time range overlaps with existing confirmed bookings for a given room.
    Overlap logic: (start_time < new_end_time) AND (end_time > new_start_time).
    Returns list of conflicting bookings (empty if no conflict).
    """
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    norm_date = validate_date(date_str)
    norm_start = validate_time(start_time_str)
    norm_end = validate_time(end_time_str)

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
    params = [room_id, norm_date, norm_end, norm_start]
    
    if exclude_booking_id:
        query += " AND b.id != ?"
        params.append(exclude_booking_id)
        
    cursor.execute(query, params)
    conflicts = cursor.fetchall()
    conn.close()
    return [dict(c) for c in conflicts]

    if cursor:
        cursor.execute(query, params)
        conflicts = cursor.fetchall()
        return [dict(c) for c in conflicts]

    conn = get_db(db_path) if db_path else get_db()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conflicts = cur.fetchall()
        return [dict(c) for c in conflicts]
    finally:
        conn.close()

def create_booking(room_id: int, user_id: int, course_unit: str, date_str: str, start_time_str: str, end_time_str: str, db_path=None):
    """
    Create a new room booking after verifying no double-booking overlap exists.
    Raises ValueError if double-booking conflict occurs or times are invalid.
    Create a new room booking atomically within a database transaction after verifying no double-booking overlap exists.
    Raises ValueError if double-booking conflict occurs, times are invalid, or referenced room/user do not exist.
    """
    if start_time_str >= end_time_str:
    if not course_unit or not course_unit.strip():
        raise ValueError("Course unit / event title is required.")
        
    norm_date = validate_date(date_str)
    norm_start = validate_time(start_time_str)
    norm_end = validate_time(end_time_str)

    if norm_start >= norm_end:
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
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")

        # 1. Verify room exists
        cursor.execute("SELECT id FROM rooms WHERE id = ?", (room_id,))
        if not cursor.fetchone():
            raise ValueError(f"Room with ID {room_id} does not exist.")

        # 2. Verify user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not cursor.fetchone():
            raise ValueError(f"User with ID {user_id} does not exist.")

        # 3. Check for conflict atomically inside this transaction
        conflicts = check_booking_conflict(room_id, norm_date, norm_start, norm_end, cursor=cursor)
        if conflicts:
            conflict_info = conflicts[0]
            raise ValueError(
                f"Double-booking prevented! Room is already booked for '{conflict_info['course_unit']}' "
                f"from {conflict_info['start_time']} to {conflict_info['end_time']}."
            )

        # 4. Insert booking
        cursor.execute("""
            INSERT INTO bookings (room_id, user_id, course_unit, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'confirmed')
        """, (room_id, user_id, course_unit.strip(), norm_date, norm_start, norm_end))
        booking_id = cursor.lastrowid
        conn.commit()

        return get_booking_by_id(booking_id, db_path=db_path)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

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
    try:
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
        return dict(row) if row else None
    finally:
        conn.close()

def cancel_booking(booking_id: int, user_id: int = None, db_path=None):
    """Cancel a confirmed booking."""
def cancel_booking(booking_id: int, user_id: int = None, is_admin: bool = False, db_path=None):
    """
    Cancel a confirmed booking.
    Raises ValueError if booking doesn't exist or is already cancelled.
    Raises PermissionError if user is not authorized to cancel.
    """
    conn = get_db(db_path) if db_path else get_db()
    cursor = conn.cursor()
    
    if user_id:
        cursor.execute("SELECT user_id FROM bookings WHERE id = ?", (booking_id,))
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
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
            raise ValueError(f"Booking with ID {booking_id} not found.")

        booking = dict(row)
        if booking['status'] == 'cancelled':
            raise ValueError(f"Booking with ID {booking_id} is already cancelled.")

        if user_id is not None and not is_admin:
            if booking['user_id'] != user_id:
                raise PermissionError("You can only cancel your own bookings.")

        cursor.execute("""
            UPDATE bookings
            SET status = 'cancelled'
            WHERE id = ?
        """, (booking_id,))
        conn.commit()
        return True
    finally:
        conn.close()

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
    try:
        cursor = conn.cursor()
        query = """
            SELECT b.*, u.name as user_name, u.role as user_role
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.room_id = ? AND b.status = 'confirmed'
        """
        params = [room_id]
        if date_str:
            norm_date = validate_date(date_str)
            query += " AND b.date = ?"
            params.append(norm_date)
            
        query += " ORDER BY b.date ASC, b.start_time ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_bookings_by_user(user_id: int, status: str = 'confirmed', db_path=None):
    """Fetch all bookings created by a specific user with room and building names."""
    conn = get_db(db_path) if db_path else get_db()
    try:
        cursor = conn.cursor()
        query = """
            SELECT b.*, r.name as room_name, bldg.name as building_name
            FROM bookings b
            JOIN rooms r ON b.room_id = r.id
            JOIN buildings bldg ON r.building_id = bldg.id
            WHERE b.user_id = ?
        """
        params = [user_id]
        if status:
            query += " AND b.status = ?"
            params.append(status)
            
        query += " ORDER BY b.date ASC, b.start_time ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_room_status(room_id: int, date_str: str, time_str: str, db_path=None):
    """
    Calculates room occupancy status at a specific date & time.
    Returns:
    - 'occupied' (red): currently occupied by a confirmed booking
    - 'booked_soon' (yellow): will become occupied within 60 minutes
    - 'free' (green): free now and for at least the next hour
    Also returns next_free_time or current_booking details for map popup markers.
    """
    norm_date = validate_date(date_str)
    norm_time = validate_time(time_str)

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
        cursor = conn.cursor()
        
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
        # 1. Check if occupied currently
        cursor.execute("""
            SELECT b.*, u.name as user_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.room_id = ?
              AND b.date = ?
              AND b.status = 'confirmed'
              AND (b.start_time <= ? AND b.end_time > ?)
        """, (room_id, norm_date, norm_time, norm_time))
        current = cursor.fetchone()
        
        if current:
            return {
                'status': 'occupied',
                'color': 'red',
                'current_booking': dict(current),
                'next_free_time': current['end_time']
            }
            
        # 2. Check if starting within next 60 mins
        try:
            t_dt = datetime.strptime(norm_time, '%H:%M')
            t_soon_dt = t_dt + timedelta(hours=1)
            # If crossed midnight, cap at 23:59 for same-day bookings
            if t_soon_dt.day != t_dt.day:
                soon_time_str = "23:59"
            else:
                soon_time_str = t_soon_dt.strftime('%H:%M')
        except ValueError:
            soon_time_str = norm_time
            
        cursor.execute("""
            SELECT b.*, u.name as user_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.room_id = ?
              AND b.date = ?
              AND b.status = 'confirmed'
              AND (b.start_time > ? AND b.start_time <= ?)
            ORDER BY b.start_time ASC
        """, (room_id, norm_date, norm_time, soon_time_str))
        soon = cursor.fetchone()
        
        if soon:
            return {
                'status': 'booked_soon',
                'color': 'yellow',
                'next_booking': dict(soon),
                'next_free_time': f"Free until {soon['start_time']}"
            }
            
        return {
            'status': 'booked_soon',
            'color': 'yellow',
            'next_booking': dict(soon),
            'next_free_time': f"Free until {soon['start_time']}"
            'status': 'free',
            'color': 'green',
            'next_free_time': 'Free all day'
        }
        
    return {
        'status': 'free',
        'color': 'green',
        'next_free_time': 'Free all day'
    }
####
    finally:
        conn.close()