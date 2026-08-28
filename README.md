# ClassSpace JKUAT

ClassSpace is a prototype lecture-room finder and booking system for JKUAT. It stores campus buildings, rooms, users, and bookings in SQLite. The project currently contains two separate application surfaces:

- **Streamlit UI:** the primary interactive application in `app.py`.
- **Flask API:** a JSON backend in `my_main.py` for programmatic access and API tests.

These surfaces are not currently connected to each other. The Streamlit app calls the database models directly; the Flask API serves JSON routes and does not render the HTML template.

## Current Features

### Streamlit application

- View room counts for total, free, booked-soon, and occupied rooms.
- Filter rooms by starting landmark, date, time, building, capacity, and status.
- View an interactive Folium satellite map with room markers.
- Calculate approximate walking distance and time from a selected campus landmark.
- Open a Google Maps walking route for a selected room.
- Search the room directory and inspect confirmed bookings.
- Create bookings and prevent overlapping confirmed bookings.
- Look up active bookings by email and cancel a booking.
- Seed the database with JKUAT sample data from the sidebar.
- Use the dashboard on smaller screens with Streamlit's responsive layout behavior. The current source still contains some fixed desktop-oriented columns and should be tested on a real phone.

### Flask API

The Flask service in `my_main.py` provides routes for:

- Health checks: `GET /` and `GET /api/health`
- User registration and login
- User lookup by ID or email
- Building and room creation/listing
- Individual room lookup and room status
- Room status-map data for all rooms
- Room booking listing and individual booking lookup
- Booking creation and cancellation
- Database initialization and seeding

## Technology

- Python 3
- Streamlit
- Flask and Flask-CORS
- Folium and `streamlit-folium`
- SQLite
- Raw SQL through Python's `sqlite3` module
- `pytest` and `unittest`-style test cases

## Repository Structure

```text
.
├── app.py                    # Streamlit UI entry point
├── my_main.py                # Flask JSON API entry point
├── models.py                 # Users, rooms, bookings, and status logic
├── requirements.txt          # Python dependencies
├── database/
│   ├── db.py                 # SQLite connection and schema initialization
│   ├── schema.sql            # Database tables and indexes
│   ├── seed.py               # JKUAT sample data generator
│   └── classspace.db         # Local SQLite database, when present
├── static/css/style.css      # Standalone stylesheet for the unused template UI
├── templates/index.html      # Standalone HTML prototype, not served by my_main.py
└── tests/
    ├── test_api.py           # Flask API tests
    └── test_db.py            # Database/model tests
```

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The active Python interpreter must be the same environment used by VS Code, Streamlit, and pytest. This avoids import errors such as missing `streamlit`, `folium`, or `flask_cors`.

## Initialize Sample Data

The seed script deletes the selected database file, recreates its schema, and inserts sample users, buildings, rooms, and bookings:

```bash
python database/seed.py
```

The default database is `database/classspace.db`.

Sample accounts are created for demonstration only:

| Role | Email | Password |
| --- | --- | --- |
| Class representative | `brian.kiprop@students.jkuat.ac.ke` | `rep123` |
| Lecturer | `jane.muthoni@jkuat.ac.ke` | `doc123` |
| Administrator | `admin@jkuat.ac.ke` | `admin123` |

Do not use these credentials in a deployed system.

## Run the Streamlit UI

```bash
streamlit run app.py
```

Streamlit normally opens at <http://localhost:8501>.

To open it from a phone on the same local network, expose the development server on the network interface:

```bash
streamlit run app.py --server.address 0.0.0.0
```

Then open `http://YOUR_COMPUTER_IP:8501` on the phone. The computer and phone must be on the same network, and the firewall must allow port `8501`.

## Run the Flask API

```bash
python my_main.py
```

The development API listens on <http://localhost:5000>. A health check is available at:

```bash
curl http://localhost:5000/api/health
```

The API reads the same default SQLite database as the Streamlit app. `DB_PATH` can be overridden in Flask tests through `app.config['DB_PATH']`; there is currently no environment-based production database configuration.

## Test

After installing `requirements.txt`:

```bash
pytest -q
```

The tests cover:

- User creation, password hashing, and login behavior
- Building and room CRUD operations
- Booking creation and overlap prevention
- Booking cancellation and ownership checks
- Room availability status calculations
- The Flask health, room, user, booking, and status-map endpoints

## Booking Rules

Bookings are stored with `confirmed` or `cancelled` status. A new confirmed booking is rejected when its interval overlaps an existing confirmed booking for the same room and date:

```text
existing.start_time < requested.end_time
AND existing.end_time > requested.start_time
```

Adjacent bookings, such as `08:00-10:00` and `10:00-12:00`, are allowed.

Room status is calculated as follows:

- **Occupied:** a confirmed booking is active at the requested time.
- **Booked soon:** the next confirmed booking starts within 60 minutes.
- **Free:** neither condition applies.

## Important Current Limitations

This is not production-ready yet:

- The Streamlit app has no real login/session authentication. Its booking form looks up an email and automatically creates an unknown user with a hardcoded password.
- The Flask API returns login results but does not issue sessions or tokens, and most data-changing routes do not enforce authentication or roles.
- CORS is enabled globally in `my_main.py`.
- The database uses SQLite and has no migration system or deployment backup process.
- The development Flask server and Streamlit server should not be used as production servers.
- The standalone `templates/index.html` and `static/css/style.css` prototype are not wired into the Flask application. There is currently no `static/js/app.js` in the repository.
- The Streamlit map uses external Folium tile and image resources, so those resources need network access.
- The current automated tests target the database and Flask API, not the Streamlit UI, map rendering, mobile layout, or browser workflows.

## Recommended Next Steps

1. Choose whether Streamlit or a Flask-served frontend is the official product surface.
2. Implement real authentication and role-based authorization before public deployment.
3. Remove the hardcoded password and restrict database seed/reset operations to administrators.
4. Add validation for email, dates, time ranges, room IDs, and user IDs at every API boundary.
5. Add browser/UI tests and verify the Streamlit layout on common phone widths.
6. Add production configuration, a database migration/backup strategy, restricted CORS, and a production deployment server.
