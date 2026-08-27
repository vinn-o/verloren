import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from database.db import init_db, DB_PATH
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
    get_room_status,
    check_booking_conflict
)

app = Flask(__name__)
CORS(app)

def get_target_db():
    """Retrieve database path from app config or fallback to default DB_PATH."""
    return app.config.get('DB_PATH', DB_PATH)

def sanitize_user(user):
    """Remove sensitive password_hash field before sending user object to client."""
    if not user:
        return None
    user_copy = dict(user)
    user_copy.pop('password_hash', None)
    return user_copy

# ---------------------------------------------------------------------------
# Health & General Routes
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "ClassSpace JKUAT Lecture Room Finder & Booking API",
        "version": "1.0.0"
    }), 200

# ---------------------------------------------------------------------------
# User Authentication & Management Routes
# ---------------------------------------------------------------------------

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
        return jsonify({"error": "Invalid email or password."}), 401

    if not verify_password(password, user['password_hash']):
        return jsonify({"error": "Invalid email or password."}), 401

    return jsonify({
        "message": "Login successful",
        "user": sanitize_user(user)
    }), 200

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

    return jsonify({
        "queried_date": date_str,
        "queried_time": time_str,
        "rooms": results
    }), 200

# ---------------------------------------------------------------------------
# Bookings Routes
# ---------------------------------------------------------------------------

@app.route('/api/rooms/<int:room_id>/bookings', methods=['GET'])
def get_room_bookings(room_id):
    date_str = request.args.get('date')
    db_path = get_target_db()
    bookings = get_bookings_by_room(room_id, date_str=date_str, db_path=db_path)
    return jsonify(bookings), 200

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
        return jsonify({
            "error": "Missing required fields: room_id, user_id, course_unit, date, start_time, end_time."
        }), 400

    try:
        db_path = get_target_db()
        booking = create_booking(
            room_id=int(room_id),
            user_id=int(user_id),
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
    
    db_path = get_target_db()
    try:
        cancel_booking(booking_id, user_id=user_id, db_path=db_path)
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
    app.run(host='0.0.0.0', port=port, debug=debug)
