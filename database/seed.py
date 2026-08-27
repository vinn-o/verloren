import os
import sys
from datetime import datetime, timedelta

# Ensure parent directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import init_db
from models import create_user, create_building, create_room, create_booking

def seed_database(db_path=None):
    """Seed database with JKUAT Main Campus buildings, lecture rooms, users, and sample bookings."""
    target_db = db_path or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database', 'classspace.db')
    if os.path.exists(target_db):
        os.remove(target_db)
        print(f"Removed existing database file: {target_db}")

    print("Initializing database tables...")
    init_db(db_path=target_db)
    
    print("Seeding JKUAT users...")
    users_data = [
        ("Brian Kiprop", "brian.kiprop@students.jkuat.ac.ke", "class_rep", "BSc. Computer Science Y1", "rep123"),
        ("Mercy Wanjiru", "mercy.wanjiru@students.jkuat.ac.ke", "class_rep", "BSc. Information Technology Y1", "rep123"),
        ("Kevin Omondi", "kevin.omondi@students.jkuat.ac.ke", "class_rep", "BSc. Civil Engineering Y1", "rep123"),
        ("Dr. Jane Muthoni", "jane.muthoni@jkuat.ac.ke", "lecturer", "Department of Computer Science", "doc123"),
        ("Prof. Peter Otieno", "peter.otieno@jkuat.ac.ke", "lecturer", "Department of Mathematics", "prof123"),
        ("Admin Timetabling", "admin@jkuat.ac.ke", "admin", "Timetabling & Space Management", "admin123")
    ]
    
    created_users = {}
    for name, email, role, course, pwd in users_data:
        u = create_user(name, email, role, course, pwd, db_path=db_path)
        created_users[email] = u['id']
        print(f"  - Added user: {name} ({role})")

    print("\nSeeding JKUAT buildings and rooms...")
    # Real JKUAT Juja Campus Building Coordinates
    buildings_rooms_data = [
        {
            "building": ("Common Lecture Building (CLB)", -1.0945, 37.0155),
            "rooms": [
                ("CLB 001", 150, -1.09451, 37.01551),
                ("CLB 002", 150, -1.09452, 37.01552),
                ("CLB 101", 200, -1.09453, 37.01553),
                ("CLB 105A", 100, -1.09454, 37.01554),
                ("CLB 201", 180, -1.09455, 37.01555),
            ]
        },
        {
            "building": ("Science Complex (SC)", -1.0944, 37.0170),
            "rooms": [
                ("SCC 101", 150, -1.09441, 37.01701),
                ("SCC 102", 120, -1.09442, 37.01702),
                ("SCC 201", 100, -1.09443, 37.01703),
                ("SCC 205", 80, -1.09444, 37.01704),
            ]
        },
        {
            "building": ("New Science Complex (NSC)", -1.0938, 37.0165),
            "rooms": [
                ("NSC 001", 250, -1.09381, 37.01651),
                ("NSC 002", 250, -1.09382, 37.01652),
                ("NSC 101", 200, -1.09383, 37.01653),
                ("NSC 102", 200, -1.09384, 37.01654),
            ]
        },
        {
            "building": ("Engineering Lecture Block (ELB)", -1.0955, 37.0142),
            "rooms": [
                ("ELB 001", 160, -1.09551, 37.01421),
                ("ELB 002", 160, -1.09552, 37.01422),
                ("ELB 104", 120, -1.09553, 37.01423),
                ("ELB 202", 100, -1.09554, 37.01424),
            ]
        },
        {
            "building": ("College of Health Sciences (COHES)", -1.0930, 37.0135),
            "rooms": [
                ("COHES Hall 1", 180, -1.09301, 37.01351),
                ("COHES Hall 2", 150, -1.09302, 37.01352),
                ("COHES 102", 90, -1.09303, 37.01353),
            ]
        },
        {
            "building": ("Lecture Theatre Building (LTB)", -1.0950, 37.0160),
            "rooms": [
                ("LTB 1", 300, -1.09501, 37.01601),
                ("LTB 2", 300, -1.09502, 37.01602),
                ("LTB 3", 300, -1.09503, 37.01603),
            ]
        },
        {
            "building": ("Technology House (TH)", -1.0960, 37.0150),
            "rooms": [
                ("TH Room 1", 80, -1.09601, 37.01501),
                ("TH Room 2", 80, -1.09602, 37.01502),
                ("TH Computer Lab", 50, -1.09603, 37.01503),
            ]
        },
        {
            "building": ("Information Processing Building (IPB)", -1.0965, 37.0140),
            "rooms": [
                ("IPB Lab 1", 60, -1.09651, 37.01401),
                ("IPB Lab 2", 60, -1.09652, 37.01402),
                ("IPB Room 101", 70, -1.09653, 37.01403),
            ]
        }
    ]

    created_rooms = {}
    for item in buildings_rooms_data:
        b_name, b_lat, b_lng = item["building"]
        b_id = create_building(b_name, b_lat, b_lng, db_path=db_path)
        print(f"  - Created building: {b_name}")
        for r_name, r_cap, r_lat, r_lng in item["rooms"]:
            r_id = create_room(r_name, b_id, r_cap, r_lat, r_lng, db_path=db_path)
            created_rooms[r_name] = r_id
            print(f"    * Room: {r_name} (Capacity: {r_cap})")

    print("\nSeeding sample bookings...")
    today_str = datetime.now().strftime('%Y-%m-%d')
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    sample_bookings = [
        # (room_name, user_email, course_unit, date, start_time, end_time)
        ("CLB 001", "brian.kiprop@students.jkuat.ac.ke", "ICS 2101: Data Structures", today_str, "08:00", "10:00"),
        ("CLB 001", "jane.muthoni@jkuat.ac.ke", "ICS 2105: Software Engineering", today_str, "11:00", "13:00"),
        ("SCC 101", "mercy.wanjiru@students.jkuat.ac.ke", "BIT 2104: Database Systems", today_str, "09:00", "11:00"),
        ("NSC 001", "peter.otieno@jkuat.ac.ke", "SMA 2100: Calculus I", today_str, "08:00", "11:00"),
        ("ELB 001", "kevin.omondi@students.jkuat.ac.ke", "ECE 2102: Circuit Theory", today_str, "14:00", "16:00"),
        ("LTB 1", "brian.kiprop@students.jkuat.ac.ke", "ICS 2100: Computer Organization", tomorrow_str, "10:00", "12:00"),
    ]

    for r_name, u_email, course, d_str, st, et in sample_bookings:
        r_id = created_rooms[r_name]
        u_id = created_users[u_email]
        try:
            b = create_booking(r_id, u_id, course, d_str, st, et, db_path=db_path)
            print(f"  - Booked {r_name} for {course} on {d_str} ({st}-{et})")
        except ValueError as e:
            print(f"  - Booking failed for {r_name}: {e}")

    print("\nDatabase seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
