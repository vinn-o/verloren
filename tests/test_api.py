import unittest
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db
from my_main import app

class TestAPIBackend(unittest.TestCase):
    def setUp(self):
        self.test_db = os.path.join(os.path.dirname(__file__), 'test_api_classspace.db')
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        init_db(db_path=self.test_db)
        
        app.config['TESTING'] = True
        app.config['DB_PATH'] = self.test_db
        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_health_check(self):
        res = self.client.get('/api/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('ClassSpace', data['service'])

    def test_user_registration_and_login(self):
        # 1. Register User
        reg_payload = {
            "name": "Jane Rep",
            "email": "janerep@jkuat.ac.ke",
            "role": "class_rep",
            "course": "BSc CS",
            "password": "secretpassword"
        }
        res = self.client.post('/api/users/register', json=reg_payload)
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['user']['email'], "janerep@jkuat.ac.ke")
        self.assertNotIn('password_hash', data['user'])

        # 2. Duplicate email should fail
        res_dup = self.client.post('/api/users/register', json=reg_payload)
        self.assertEqual(res_dup.status_code, 400)
        self.assertIn("already exists", res_dup.get_json()['error'])

        # 3. Login User
        login_payload = {
            "email": "janerep@jkuat.ac.ke",
            "password": "secretpassword"
        }
        res_login = self.client.post('/api/users/login', json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        self.assertEqual(res_login.get_json()['user']['name'], "Jane Rep")

        # 4. Wrong password login
        wrong_login = {
            "email": "janerep@jkuat.ac.ke",
            "password": "wrongpassword"
        }
        res_bad = self.client.post('/api/users/login', json=wrong_login)
        self.assertEqual(res_bad.status_code, 401)

    def test_building_and_room_endpoints(self):
        # 1. Create Building
        b_payload = {
            "name": "CLB Block",
            "latitude": -1.0945,
            "longitude": 37.0155
        }
        res_b = self.client.post('/api/buildings', json=b_payload)
        self.assertEqual(res_b.status_code, 201)
        b_id = res_b.get_json()['building_id']

        # 2. Get Buildings
        res_blist = self.client.get('/api/buildings')
        self.assertEqual(res_blist.status_code, 200)
        buildings = res_blist.get_json()
        self.assertEqual(len(buildings), 1)

        # 3. Create Room
        r_payload = {
            "name": "CLB 001",
            "building_id": b_id,
            "capacity": 150
        }
        res_r = self.client.post('/api/rooms', json=r_payload)
        self.assertEqual(res_r.status_code, 201)
        r_id = res_r.get_json()['room']['id']

        # 4. Get Rooms
        res_rlist = self.client.get('/api/rooms')
        self.assertEqual(res_rlist.status_code, 200)
        rooms = res_rlist.get_json()
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]['name'], "CLB 001")

    def test_booking_creation_and_double_booking_prevention(self):
        # Setup building, room, and user
        b_res = self.client.post('/api/buildings', json={"name": "CLB", "latitude": -1.0, "longitude": 37.0})
        b_id = b_res.get_json()['building_id']

        r_res = self.client.post('/api/rooms', json={"name": "CLB 101", "building_id": b_id, "capacity": 100})
        r_id = r_res.get_json()['room']['id']

        u_res = self.client.post('/api/users/register', json={
            "name": "User 1", "email": "u1@test.com", "role": "class_rep", "password": "pass"
        })
        u_id = u_res.get_json()['user']['id']

        # 1. Create first booking (08:00 - 10:00)
        booking1_payload = {
            "room_id": r_id,
            "user_id": u_id,
            "course_unit": "ICS 2101",
            "date": "2026-09-10",
            "start_time": "08:00",
            "end_time": "10:00"
        }
        res1 = self.client.post('/api/bookings', json=booking1_payload)
        self.assertEqual(res1.status_code, 201)
        booking1_id = res1.get_json()['booking']['id']

        # 2. Overlapping booking (09:00 - 11:00) -> Must fail with 400
        booking2_payload = {
            "room_id": r_id,
            "user_id": u_id,
            "course_unit": "ICS 2102",
            "date": "2026-09-10",
            "start_time": "09:00",
            "end_time": "11:00"
        }
        res2 = self.client.post('/api/bookings', json=booking2_payload)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Double-booking prevented", res2.get_json()['error'])

        # 3. Check room status color coding
        # At 08:30 -> Occupied (red)
        status_res = self.client.get(f'/api/rooms/{r_id}/status?date=2026-09-10&time=08:30')
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.get_json()['status'], 'occupied')
        self.assertEqual(status_res.get_json()['color'], 'red')

        # At 07:15 -> Booked soon (yellow)
        status_res_soon = self.client.get(f'/api/rooms/{r_id}/status?date=2026-09-10&time=07:15')
        self.assertEqual(status_res_soon.get_json()['status'], 'booked_soon')
        self.assertEqual(status_res_soon.get_json()['color'], 'yellow')

        # 4. Cancel booking
        res_cancel = self.client.post(f'/api/bookings/{booking1_id}/cancel', json={"user_id": u_id})
        self.assertEqual(res_cancel.status_code, 200)

        # 5. Overlapping booking should now succeed
        res2_retry = self.client.post('/api/bookings', json=booking2_payload)
        self.assertEqual(res2_retry.status_code, 201)

    def test_status_map_endpoint(self):
        b_res = self.client.post('/api/buildings', json={"name": "Science Complex", "latitude": -1.0944, "longitude": 37.0170})
        b_id = b_res.get_json()['building_id']

        self.client.post('/api/rooms', json={"name": "SCC 101", "building_id": b_id, "capacity": 120})
        self.client.post('/api/rooms', json={"name": "SCC 102", "building_id": b_id, "capacity": 120})

        res_map = self.client.get('/api/rooms/status-map?date=2026-09-10&time=10:00')
        self.assertEqual(res_map.status_code, 200)
        data = res_map.get_json()
        self.assertIn('rooms', data)
        self.assertEqual(len(data['rooms']), 2)

if __name__ == '__main__':
    unittest.main()
