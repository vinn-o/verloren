ClassSpace — JKUAT Lecture Room Finder & Booking System

ClassSpace is a real-time lecture room finder and booking system designed for JKUAT students, class representatives, lecturers, and administrators. It helps users locate available lecture rooms, view their current occupancy status, and make bookings while preventing double bookings.

Features

🔐 User authentication — Registration, login, and logout.

🏫 Lecture room discovery — Browse available JKUAT lecture rooms.

🗺️ Interactive campus map — Folium map with color-coded room availability.

📅 Room booking — Book rooms for specific dates and time slots.

🚫 Double-booking prevention — Prevents overlapping confirmed bookings for the same room.

📋 Booking management — View booking history and cancel bookings.

🔄 Real-time status updates — Room occupancy information can be refreshed automatically.

🎨 JKUAT-themed interface — Bootstrap 5.3 with custom JKUAT green and gold styling.

Technology Stack

Component                                   Technology

Backend                                     Flask / Python 3

Database                                    SQLite

Database access                             Raw SQL

Maps                                        Folium

Frontend                                    Jinja2 Templates

UI Framework                                Bootstrap 5.3

Styling                                     Custom CSS

Client-side functionality                   JavaScript

Project Structure

classspace/
├── app.py                  # Flask application entry point
├── models.py               # Database initialization and SQL queries
├── map_builder.py          # Folium campus map builder
├── seed_data.py            # Database seeding script
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py      # Authentication routes
│   ├── room_routes.py      # Room browsing and dashboard routes
│   └── booking_routes.py   # Booking and cancellation routes
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── map.html
│   ├── rooms.html
│   ├── book.html
│   ├── my_bookings.html
│   ├── login.html
│   └── register.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── database/
│   └── classspace.db
├── requirements.txt
├── .gitignore
└── README.md

How Room Availability Works

The campus map uses three main status colors:

🟢 Green — Free: The room has no current booking.

🔴 Red — Occupied: The room is currently occupied.

🟠 Orange — Upcoming: The room has a booking starting within the next 30 minutes.

Map markers provide room information and a direct link to the room booking page.

DOUBLE BOOKING PREVENTION

Before creating a booking, ClassSpace checks whether another confirmed booking overlaps with the requested time for the same room and date.

The core check is:

SELECT id FROM bookings
WHERE room_id = ? AND date = ? AND status = 'confirmed'
  AND start_time < ? AND end_time > ?

If an overlap is found, the booking is rejected and the user receives a friendly error message.

This ensures that two users cannot create conflicting confirmed bookings for the same lecture room and time period.

DATABASE SEEDING

The project includes a seed_data.py script for initializing the database and inserting sample users, buildings, rooms, and bookings.

Run:

python seed_data.py

Expected output:

Initializing database...
Seeding users...
Seeding buildings...
Seeding rooms...
Seeding bookings...
Seed complete!

Demo Accounts

Role                                     Email                              Password

Class Representative                     rep@jkuat.ac.ke                    demo123

Lecturer                                 lecturer@jkuat.ac.ke                demo123

Admin                                    admin@jkuat.ac.ke                   admin123

Security note: These are demonstration credentials. Change or remove seeded passwords before using the application in a real deployment.

Installation

1. Clone the repository

git clone <your-github-repository-url>
cd classspace

2. Install dependencies

Make sure Python 3 is installed, then run:

pip install -r requirements.txt

3. Initialize the database

python seed_data.py

4. Start the application

python app.py

5. Open ClassSpace

Visit:

http://127.0.0.1:5000

MAIN USER FLOW

Register / Login
       ↓
Dashboard
       ↓
View Available Rooms
       ↓
Check Interactive Campus Map
       ↓
Select a Room
       ↓
Choose Date & Time
       ↓
Check for Conflicts
       ↓
Confirm Booking
       ↓
View / Cancel Booking

BUG FIXES AND INTEGRATION IMPROVEMENTS

During development, several integration issues were identified and resolved:

Password verification

 - Corrected the argument order used when calling the password verification function.

User creation

 - Corrected argument alignment between the registration route and user-creation function.

Flask blueprints

 - Removed conflicting route definitions from app.py and registered the application blueprints cleanly.

Jinja2 template variables

 - Corrected mismatched variable names between room routes and the dashboard template.

Verification

Database initialization and seeding were tested successfully using:

python seed_data.py

The seed process completed successfully for users, buildings, rooms, and bookings.

FUTURE IMPROVEMENTS

Potential improvements include:

Deploying the application to a production server.

Adding administrator tools for managing rooms and buildings.

Integrating the official JKUAT timetable.

Adding email or notification reminders for upcoming bookings.

Adding stronger role-based access control.

Replacing demonstration credentials with secure production authentication.

Adding automated tests for booking conflicts and authentication.

Using a production database such as PostgreSQL for larger-scale deployment.

Project Purpose

ClassSpace aims to make lecture-room management easier by providing a single platform where users can find, verify, and book available rooms in real time, reducing confusion and preventing double bookings.

Built With

Python • Flask • SQLite • Folium • Jinja2 • Bootstrap 5.3 • JavaScript
