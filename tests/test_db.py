import unittest
import os
import sys
from datetime import datetime

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db, get_db
from models import (
    create_user, get_user_by_email, verify_password,
    create_building, get_all_buildings,
    create_room, get_all_rooms, get_room_by_id,
    check_booking_conflict, create_booking, cancel_booking,
    get_room_status, get_bookings_by_room
    get_room_status, get_bookings_by_room, get_bookings_by_user
)

class TestDatabaseAndModels(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(os.path.dirname(__file__), 'test_classspace.db')
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        init_db(db_path=self.test_db)
        
        # Setup basic data
        self.user = create_user("Test Rep", "rep@test.jkuat.ac.ke", "class_rep", "BSc CS Y1", "password123", db_path=self.test_db)
        self.building_id = create_building("Test Building (CLB)", -1.0945, 37.0155, db_path=self.test_db)
        self.room_id = create_room("CLB 001", self.building_id, 150, db_path=self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_user_creation_and_auth(self):
        user = get_user_by_email("rep@test.jkuat.ac.ke", db_path=self.test_db)
        self.assertIsNotNone(user)
        self.assertEqual(user['role'], "class_rep")
        self.assertTrue(verify_password("password123", user['password_hash']))
        self.assertFalse(verify_password("wrongpassword", user['password_hash']))

    def test_duplicate_user_email_fails(self):
        with self.assertRaises(ValueError):
            create_user("Duplicate User", "rep@test.jkuat.ac.ke", "lecturer", "CS", "pass", db_path=self.test_db)

    def test_building_and_room_creation(self):
        buildings = get_all_buildings(db_path=self.test_db)
        self.assertEqual(len(buildings), 1)
        
        rooms = get_all_rooms(db_path=self.test_db)
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]['name'], "CLB 001")
        self.assertEqual(rooms[0]['capacity'], 150)

    def test_successful_booking(self):
        date_str = "2026-09-01"
        booking = create_booking(
            self.room_id, self.user['id'], "ICS 2101", date_str, "08:00", "10:00", db_path=self.test_db
        )
        self.assertIsNotNone(booking)
        self.assertEqual(booking['course_unit'], "ICS 2101")
        self.assertEqual(booking['status'], "confirmed")

    def test_double_booking_prevention(self):
        date_str = "2026-09-01"
        # Initial booking: 08:00 - 10:00
        create_booking(self.room_id, self.user['id'], "ICS 2101", date_str, "08:00", "10:00", db_path=self.test_db)
        
        # Test Case 1: Exact same time slot (08:00 - 10:00) -> Should fail
        with self.assertRaises(ValueError) as ctx:
            create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "08:00", "10:00", db_path=self.test_db)
        self.assertIn("Double-booking prevented", str(ctx.exception))

        # Test Case 2: Partial overlap start (07:30 - 08:30) -> Should fail
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "07:30", "08:30", db_path=self.test_db)

        # Test Case 3: Partial overlap end (09:30 - 10:30) -> Should fail
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "09:30", "10:30", db_path=self.test_db)

        # Test Case 4: Enclosing overlap (07:00 - 11:00) -> Should fail
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "07:00", "11:00", db_path=self.test_db)

        # Test Case 5: Inside overlap (08:30 - 09:30) -> Should fail
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "08:30", "09:30", db_path=self.test_db)

        # Test Case 6: Adjacent prior time slot (06:00 - 08:00) -> Should succeed
        b_prev = create_booking(self.room_id, self.user['id'], "ICS 2100", date_str, "06:00", "08:00", db_path=self.test_db)
        self.assertIsNotNone(b_prev)

        # Test Case 7: Adjacent subsequent time slot (10:00 - 12:00) -> Should succeed
        b_next = create_booking(self.room_id, self.user['id'], "ICS 2103", date_str, "10:00", "12:00", db_path=self.test_db)
        self.assertIsNotNone(b_next)

    def test_booking_cancellation(self):
        date_str = "2026-09-01"
        b = create_booking(self.room_id, self.user['id'], "ICS 2101", date_str, "14:00", "16:00", db_path=self.test_db)
        self.assertEqual(b['status'], "confirmed")
        
        cancel_booking(b['id'], user_id=self.user['id'], db_path=self.test_db)
        
        # After cancellation, a new booking in the same slot should now succeed
        b_new = create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "14:00", "16:00", db_path=self.test_db)
        self.assertEqual(b_new['course_unit'], "ICS 2102")

    def test_room_status_color_coding(self):
        date_str = "2026-09-01"
        create_booking(self.room_id, self.user['id'], "ICS 2101", date_str, "10:00", "12:00", db_path=self.test_db)
        
        # At 10:30 -> Occupied (Red)
        status_occupied = get_room_status(self.room_id, date_str, "10:30", db_path=self.test_db)
        self.assertEqual(status_occupied['status'], "occupied")
        self.assertEqual(status_occupied['color'], "red")

        # At 09:15 -> Starting in 45 mins -> Booked soon (Yellow)
        status_soon = get_room_status(self.room_id, date_str, "09:15", db_path=self.test_db)
        self.assertEqual(status_soon['status'], "booked_soon")
        self.assertEqual(status_soon['color'], "yellow")

        # At 07:00 -> Free (Green)
        status_free = get_room_status(self.room_id, date_str, "07:00", db_path=self.test_db)
        self.assertEqual(status_free['status'], "free")
        self.assertEqual(status_free['color'], "green")

    def test_get_bookings_by_user(self):
        date_str = "2026-09-01"
        b1 = create_booking(self.room_id, self.user['id'], "ICS 2101", date_str, "08:00", "10:00", db_path=self.test_db)
        b2 = create_booking(self.room_id, self.user['id'], "ICS 2102", date_str, "10:00", "12:00", db_path=self.test_db)

        user_bookings = get_bookings_by_user(self.user['id'], db_path=self.test_db)
        self.assertEqual(len(user_bookings), 2)
        self.assertEqual(user_bookings[0]['course_unit'], "ICS 2101")
        self.assertEqual(user_bookings[0]['room_name'], "CLB 001")

    def test_invalid_inputs_and_boundary_conditions(self):
        # 1. Start time >= End time
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2101", "2026-09-01", "10:00", "10:00", db_path=self.test_db)
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2101", "2026-09-01", "12:00", "10:00", db_path=self.test_db)

        # 2. Invalid date
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2101", "invalid-date", "08:00", "10:00", db_path=self.test_db)

        # 3. Invalid time
        with self.assertRaises(ValueError):
            create_booking(self.room_id, self.user['id'], "ICS 2101", "2026-09-01", "25:00", "10:00", db_path=self.test_db)

        # 4. Nonexistent room ID
        with self.assertRaises(ValueError):
            create_booking(9999, self.user['id'], "ICS 2101", "2026-09-01", "08:00", "10:00", db_path=self.test_db)

        # 5. Nonexistent user ID
        with self.assertRaises(ValueError):
            create_booking(self.room_id, 9999, "ICS 2101", "2026-09-01", "08:00", "10:00", db_path=self.test_db)

        # 6. Cancel nonexistent booking
        with self.assertRaises(ValueError):
            cancel_booking(9999, user_id=self.user['id'], db_path=self.test_db)

        # 7. Cancel already cancelled booking
        b = create_booking(self.room_id, self.user['id'], "ICS 2101", "2026-09-01", "14:00", "16:00", db_path=self.test_db)
        cancel_booking(b['id'], user_id=self.user['id'], db_path=self.test_db)
        with self.assertRaises(ValueError):
            cancel_booking(b['id'], user_id=self.user['id'], db_path=self.test_db)

        # 8. Cancel another user's booking
        other_user = create_user("Other Rep", "other@jkuat.ac.ke", "class_rep", "BSc CS", "pass", db_path=self.test_db)
        b_other = create_booking(self.room_id, other_user['id'], "ICS 2105", "2026-09-01", "16:00", "18:00", db_path=self.test_db)
        with self.assertRaises(PermissionError):
            cancel_booking(b_other['id'], user_id=self.user['id'], db_path=self.test_db)

    def test_admin_registration_guard(self):
        # Public admin creation must be blocked
        with self.assertRaises(ValueError):
            create_user("Admin User", "admin1@jkuat.ac.ke", "admin", "Admin", "pass", allow_admin=False, db_path=self.test_db)

        # Admin creation with allow_admin=True succeeds
        admin = create_user("Admin User", "admin1@jkuat.ac.ke", "admin", "Admin", "pass", allow_admin=True, db_path=self.test_db)
        self.assertEqual(admin['role'], 'admin')

if __name__ == '__main__':
    unittest.main()

