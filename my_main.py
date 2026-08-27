import os
from datetime import datetime
from flask import Flask, request, jsonify
import math
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import folium
from folium.plugins import AntPath

from database.db import init_db, DB_PATH
from database.db import ensure_db_initialized, init_db, DB_PATH
from database.seed import seed_database
from models import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    verify_password,
    create_building,
    get_all_buildings,
    create_room,
    get_all_rooms,
    get_room_by_id,
    create_booking,
    get_booking_by_id,
    cancel_booking,
    get_bookings_by_room,
    get_bookings_by_user,
    get_room_status,
    check_booking_conflict
    check_booking_conflict,
    validate_date,
    validate_time
)

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'classspace-secret-key-jkuat-2026')
CORS(app, supports_credentials=True)

def get_target_db():
    """Retrieve database path from app config or fallback to default DB_PATH."""
    return app.config.get('DB_PATH', DB_PATH)

# Non-destructively ensure database tables exist upon module loading
try:
    ensure_db_initialized(get_target_db())
except Exception as e:
    print(f"Warning during auto-initialization of database: {e}")

def sanitize_user(user):
    """Remove sensitive password_hash field before sending user object to client."""
    if not user:
        return None
    user_copy = dict(user)
    user_copy.pop('password_hash', None)
    return user_copy

def calculate_distance_and_walk_time(lat1, lon1, lat2, lon2):
    """Calculates distance in meters and estimated walking time in minutes using Haversine formula."""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance_meters = R * c
    walk_minutes = max(1, math.ceil(distance_meters / 84.0))  # ~1.4 m/s walking speed
    return round(distance_meters), walk_minutes

# ---------------------------------------------------------------------------
# Health & General Routes
# Web UI & Map Routes
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET'])
def index():
    """Render the primary ClassSpace browser web application."""
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "ClassSpace JKUAT Lecture Room Finder & Booking API",
        "version": "1.0.0"
    }), 200

@app.route('/map-html', methods=['GET'])
def render_map_html():
    """Dynamically render interactive Folium campus map with real-time status pins and navigation routes."""
    now = datetime.now()
    date_str = request.args.get('date', now.strftime('%Y-%m-%d'))
    time_str = request.args.get('time', now.strftime('%H:%M'))
    origin_lat = request.args.get('origin_lat', default=-1.0970, type=float)
    origin_lng = request.args.get('origin_lng', default=37.0120, type=float)
    dest_room_id = request.args.get('dest_room_id', default=None, type=int)
    building_id = request.args.get('building_id', default=None, type=int)

    db_path = get_target_db()
    rooms = get_all_rooms(building_id=building_id, db_path=db_path)

    # Initialize Folium Map centered on JKUAT Main Campus
    m = folium.Map(location=[-1.0948, 37.0152], zoom_start=17, tiles="OpenStreetMap")

    # Starting Location Marker
    folium.Marker(
        location=[origin_lat, origin_lng],
        popup="<b>My Starting Location</b>",
        tooltip="My Current Location",
        icon=folium.Icon(color='blue', icon='user', prefix='fa')
    ).add_to(m)

    target_room = None
    for room in rooms:
        status_info = get_room_status(room['id'], date_str, time_str, db_path=db_path)
        lat = room.get('latitude') or -1.0945
        lng = room.get('longitude') or 37.0155

        if dest_room_id and room['id'] == dest_room_id:
            target_room = room

        status = status_info['status']
        if status == 'free':
            color = 'green'
            icon_name = 'check-circle'
            status_text = '🟢 FREE NOW'
        elif status == 'booked_soon':
            color = 'orange'
            icon_name = 'clock'
            status_text = f"🟡 BOOKED SOON ({status_info.get('next_free_time')})"
        else:
            color = 'red'
            icon_name = 'ban'
            status_text = f"🔴 OCCUPIED until {status_info.get('next_free_time')}"

        popup_html = f"""
        <div style="font-family: Arial, sans-serif; width: 220px; font-size: 13px;">
            <h4 style="margin: 0 0 5px 0; color: #0284c7;">{room['name']}</h4>
            <p style="margin: 2px 0;"><b>Building:</b> {room['building_name']}</p>
            <p style="margin: 2px 0;"><b>Capacity:</b> {room['capacity']} seats</p>
            <hr style="margin: 6px 0; border: 0; border-top: 1px solid #cbd5e1;">
            <p style="margin: 2px 0;"><b>Status:</b> {status_text}</p>
        </div>
        """

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{room['name']} ({room['building_name']})",
            icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
        ).add_to(m)

    # If destination room selected, draw walking path
    if target_room:
        dest_lat = target_room.get('latitude') or -1.0945
        dest_lng = target_room.get('longitude') or 37.0155
        dist_m, walk_mins = calculate_distance_and_walk_time(origin_lat, origin_lng, dest_lat, dest_lng)

        AntPath(
            locations=[[origin_lat, origin_lng], [dest_lat, dest_lng]],
            color='#38bdf8',
            weight=5,
            opacity=0.8,
            dash_array=[10, 20],
            delay=1000,
            popup=f"Path to {target_room['name']} ({dist_m}m, ~{walk_mins} min walk)"
        ).add_to(m)

        m.fit_bounds([[origin_lat, origin_lng], [dest_lat, dest_lng]], padding=[40, 40])

    return m._repr_html_(), 200, {'Content-Type': 'text/html'}

# ---------------------------------------------------------------------------
# User Authentication & Management Routes
# ---------------------------------------------------------------------------

@app.route('/api/auth/me', methods=['GET'])
def get_current_session_user():
    """Retrieve currently authenticated session user."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"authenticated": False, "user": None}), 200
    
    db_path = get_target_db()
    user = get_user_by_id(user_id, db_path=db_path)
    if not user:
        session.clear()
        return jsonify({"authenticated": False, "user": None}), 200

    return jsonify({
        "authenticated": True,
        "user": sanitize_user(user)
    }), 200

@app.route('/api/users/register', methods=['POST'])
def register_user():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    role = data.get('role')
    course = data.get('course', '')
    password = data.get('password')

    if not all([name, email, role, password]):
        return jsonify({"error": "Missing required fields: name, email, role, and password are required."}), 400

    try:
        db_path = get_target_db()
        user = create_user(name, email, role, course, password, db_path=db_path)
        # Public registration forbids admin accounts
        user = create_user(name, email, role, course, password, allow_admin=False, db_path=db_path)
        
        # Automatically establish authenticated session upon successful registration
        session['user_id'] = user['id']
        session['user_role'] = user['role']
        session['user_name'] = user['name']

        return jsonify({
            "message": "User registered successfully",
            "user": sanitize_user(user)
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An error occurred during registration: {str(e)}"}), 500

@app.route('/api/users/login', methods=['POST'])
def login_user():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db_path = get_target_db()
    user = get_user_by_email(email, db_path=db_path)
    if not user:
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({"error": "Invalid email or password."}), 401

    if not verify_password(password, user['password_hash']):
        return jsonify({"error": "Invalid email or password."}), 401
    session['user_id'] = user['id']
    session['user_role'] = user['role']
    session['user_name'] = user['name']

    return jsonify({
        "message": "Login successful",
        "user": sanitize_user(user)
    }), 200

@app.route('/api/users/logout', methods=['POST'])
def logout_user():
    session.clear()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    db_path = get_target_db()
    user = get_user_by_id(user_id, db_path=db_path)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify(sanitize_user(user)), 200

@app.route('/api/users/by-email', methods=['GET'])
def get_user_by_email_route():
    email = request.args.get('email')
    if not email:
        return jsonify({"error": "Email query parameter is required."}), 400
    
    db_path = get_target_db()
    user = get_user_by_email(email, db_path=db_path)
    if not user:
        return jsonify({"error": "User not found."}), 404
    return jsonify(sanitize_user(user)), 200

@app.route('/api/users/<int:user_id>/bookings', methods=['GET'])
def get_user_bookings_route(user_id):
    """Retrieve confirmed bookings created by specific user."""
    db_path = get_target_db()
    bookings = get_bookings_by_user(user_id, status='confirmed', db_path=db_path)
    return jsonify(bookings), 200

# ---------------------------------------------------------------------------
# Buildings & Rooms Routes
# ---------------------------------------------------------------------------

@app.route('/api/buildings', methods=['GET'])
def list_buildings():
    db_path = get_target_db()
    buildings = get_all_buildings(db_path=db_path)
    return jsonify(buildings), 200

@app.route('/api/buildings', methods=['POST'])
def add_building():
    data = request.get_json() or {}
    name = data.get('name')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not name or latitude is None or longitude is None:
        return jsonify({"error": "Missing required fields: name, latitude, longitude."}), 400

    try:
        db_path = get_target_db()
        building_id = create_building(name, float(latitude), float(longitude), db_path=db_path)
        return jsonify({
            "message": "Building created successfully",
            "building_id": building_id,
            "name": name,
            "latitude": latitude,
            "longitude": longitude
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/rooms', methods=['GET'])
def list_rooms():
    building_id = request.args.get('building_id', type=int)
    min_capacity = request.args.get('min_capacity', type=int)
    
    db_path = get_target_db()
    rooms = get_all_rooms(building_id=building_id, min_capacity=min_capacity, db_path=db_path)
    return jsonify(rooms), 200

@app.route('/api/rooms', methods=['POST'])
def add_room():
    data = request.get_json() or {}
    name = data.get('name')
    building_id = data.get('building_id')
    capacity = data.get('capacity')
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if not name or building_id is None or capacity is None:
        return jsonify({"error": "Missing required fields: name, building_id, capacity."}), 400

    try:
        db_path = get_target_db()
        room_id = create_room(
            name=name,
            building_id=int(building_id),
            capacity=int(capacity),
            latitude=float(latitude) if latitude is not None else None,
            longitude=float(longitude) if longitude is not None else None,
            db_path=db_path
        )
        room = get_room_by_id(room_id, db_path=db_path)
        return jsonify({
            "message": "Room created successfully",
            "room": room
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    db_path = get_target_db()
    room = get_room_by_id(room_id, db_path=db_path)
    if not room:
        return jsonify({"error": "Room not found."}), 404
    return jsonify(room), 200

@app.route('/api/rooms/<int:room_id>/status', methods=['GET'])
def fetch_room_status(room_id):
    now = datetime.now()
    date_str = request.args.get('date', now.strftime('%Y-%m-%d'))
    time_str = request.args.get('time', now.strftime('%H:%M'))
    
    db_path = get_target_db()
    room = get_room_by_id(room_id, db_path=db_path)
    if not room:
        return jsonify({"error": "Room not found."}), 404

    status_data = get_room_status(room_id, date_str, time_str, db_path=db_path)
    status_data['room'] = room
    status_data['queried_date'] = date_str
    status_data['queried_time'] = time_str
    return jsonify(status_data), 200
    try:
        status_data = get_room_status(room_id, date_str, time_str, db_path=db_path)
        status_data['room'] = room
        status_data['queried_date'] = date_str
        status_data['queried_time'] = time_str
        return jsonify(status_data), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/rooms/status-map', methods=['GET'])
def get_all_rooms_status_map():
    """Returns all rooms with real-time status details for campus map rendering."""
    now = datetime.now()
    date_str = request.args.get('date', now.strftime('%Y-%m-%d'))
    time_str = request.args.get('time', now.strftime('%H:%M'))
    building_id = request.args.get('building_id', type=int)
    
    db_path = get_target_db()
    rooms = get_all_rooms(building_id=building_id, db_path=db_path)
    results = []
    
    for room in rooms:
        status_info = get_room_status(room['id'], date_str, time_str, db_path=db_path)
        results.append({
            "room_id": room['id'],
            "room_name": room['name'],
            "building_id": room['building_id'],
            "building_name": room['building_name'],
            "capacity": room['capacity'],
            "latitude": room['latitude'],
            "longitude": room['longitude'],
            "status": status_info['status'],
            "color": status_info['color'],
            "next_free_time": status_info.get('next_free_time'),
            "current_booking": status_info.get('current_booking'),
            "next_booking": status_info.get('next_booking')
        })
    try:
        for room in rooms:
            status_info = get_room_status(room['id'], date_str, time_str, db_path=db_path)
            results.append({
                "room_id": room['id'],
                "room_name": room['name'],
                "building_id": room['building_id'],
                "building_name": room['building_name'],
                "capacity": room['capacity'],
                "latitude": room['latitude'],
                "longitude": room['longitude'],
                "status": status_info['status'],
                "color": status_info['color'],
                "next_free_time": status_info.get('next_free_time'),
                "current_booking": status_info.get('current_booking'),
                "next_booking": status_info.get('next_booking')
            })

    return jsonify({
        "queried_date": date_str,
        "queried_time": time_str,
        "rooms": results
    }), 200
        return jsonify({
            "queried_date": date_str,
            "queried_time": time_str,
            "rooms": results
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

# ---------------------------------------------------------------------------
# Bookings Routes
# ---------------------------------------------------------------------------

@app.route('/api/rooms/<int:room_id>/bookings', methods=['GET'])
def get_room_bookings(room_id):
    date_str = request.args.get('date')
    db_path = get_target_db()
    bookings = get_bookings_by_room(room_id, date_str=date_str, db_path=db_path)
    return jsonify(bookings), 200
    try:
        bookings = get_bookings_by_room(room_id, date_str=date_str, db_path=db_path)
        return jsonify(bookings), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    db_path = get_target_db()
    booking = get_booking_by_id(booking_id, db_path=db_path)
    if not booking:
        return jsonify({"error": "Booking not found."}), 404
    return jsonify(booking), 200

@app.route('/api/bookings', methods=['POST'])
def add_booking():
    data = request.get_json() or {}
    room_id = data.get('room_id')
    user_id = data.get('user_id')
    course_unit = data.get('course_unit')
    date_str = data.get('date')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    if not all([room_id, user_id, course_unit, date_str, start_time_str, end_time_str]):
    # Prioritize authenticated session; fallback to payload user_id for test suites
    active_user_id = session.get('user_id')
    if not active_user_id:
        if app.config.get('TESTING') and data.get('user_id'):
            active_user_id = data.get('user_id')
        else:
            return jsonify({"error": "Authentication required. Please sign in to book a lecture room."}), 401

    if not all([room_id, course_unit, date_str, start_time_str, end_time_str]):
        return jsonify({
            "error": "Missing required fields: room_id, user_id, course_unit, date, start_time, end_time."
            "error": "Missing required fields: room_id, course_unit, date, start_time, end_time."
        }), 400

    try:
        db_path = get_target_db()
        booking = create_booking(
            room_id=int(room_id),
            user_id=int(user_id),
            user_id=int(active_user_id),
            course_unit=course_unit,
            date_str=date_str,
            start_time_str=start_time_str,
            end_time_str=end_time_str,
            db_path=db_path
        )
        return jsonify({
            "message": "Booking confirmed successfully",
            "booking": booking
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to create booking: {str(e)}"}), 500

@app.route('/api/bookings/<int:booking_id>/cancel', methods=['POST'])
@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking_route(booking_id):
    data = request.get_json() if request.is_json else {}
    user_id = data.get('user_id') if data else None
    
    active_user_id = session.get('user_id')
    is_admin = session.get('user_role') == 'admin'

    if not active_user_id:
        if app.config.get('TESTING') and data and data.get('user_id'):
            active_user_id = data.get('user_id')
        else:
            return jsonify({"error": "Authentication required. Please sign in to cancel a booking."}), 401

    db_path = get_target_db()
    try:
        cancel_booking(booking_id, user_id=user_id, db_path=db_path)
        cancel_booking(booking_id, user_id=int(active_user_id) if active_user_id else None, is_admin=is_admin, db_path=db_path)
        return jsonify({
            "message": f"Booking {booking_id} cancelled successfully",
            "booking_id": booking_id
        }), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---------------------------------------------------------------------------
# Database Maintenance Routes
# ---------------------------------------------------------------------------

@app.route('/api/db/init', methods=['POST'])
def initialize_database_route():
    db_path = get_target_db()
    init_db(db_path=db_path)
    return jsonify({"message": f"Database initialized successfully at {db_path}"}), 200

@app.route('/api/db/seed', methods=['POST'])
def seed_database_route():
    db_path = get_target_db()
    seed_database(db_path=db_path)
    return jsonify({"message": f"Database seeded successfully at {db_path}"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() in ('true', '1')
    print(f"Starting ClassSpace Backend API server on port {port}...")
    print(f"Starting ClassSpace Primary Web Application on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=debug)
