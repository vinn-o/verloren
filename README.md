# 🎓 ClassSpace JKUAT - Lecture Room Finder & Campus Navigation

**ClassSpace** is a lecture room scheduling, real-time occupancy tracking, and interactive walking navigation system for **JKUAT (Jomo Kenyatta University of Agriculture and Technology, Juja Main Campus)**.

---

## 🏗️ System Architecture

- **Primary Application**: Flask REST API & Web Application ([`my_main.py`](my_main.py)) serving a responsive browser frontend ([`templates/index.html`](templates/index.html) + [`static/css/style.css`](static/css/style.css) + [`static/js/app.js`](static/js/app.js)) and dynamic Folium campus maps.
- **Secondary / Prototype Interface**: Standalone Streamlit dashboard ([`app.py`](app.py)).
- **Domain & Business Logic**: Models and double-booking conflict prevention engine in [`models.py`](models.py).
- **Persistence Layer**: SQLite database ([`database/classspace.db`](database/classspace.db)) with relational schema ([`database/schema.sql`](database/schema.sql)).

---

## 🚀 Getting Started

### 1. Installation

Install project dependencies:

```bash
pip install -r requirements.txt
```

### 2. Seed Campus Database

Seed the database with real JKUAT Main Campus lecture buildings (CLB, Science Complex, NSC, ELB, COHES, LTB, Technology House, IPB), rooms, and sample bookings:

```bash
python3 database/seed.py
```

### 3. Run the Primary Application (Flask Web App)

Start the primary web application on port 5000:

```bash
python3 my_main.py
```

Open your browser at: **`http://localhost:5000`**

### 4. Run the Secondary Interface (Streamlit)

Alternatively, launch the Streamlit prototype dashboard:

```bash
streamlit run app.py
```

---

## 🧪 Running Tests

Run the full automated test suite:

```bash
# Run database and business logic unit tests
python3 -m unittest tests/test_db.py -v

# Run Flask REST API integration tests
python3 -m unittest tests/test_api.py -v

# Or run all tests together
python3 -m unittest discover -s tests -v
```

---

## 🗺️ Key Features & Rules

1. **Real-Time Room Occupancy Tracking**:
   - 🟢 **Free Now (Green)**: Room is available now and for at least the next 60 minutes.
   - 🟡 **Booked Soon (Yellow)**: Room is currently free, but a booking begins within the next hour.
   - 🔴 **Occupied (Red)**: Room is currently occupied by a confirmed session.

2. **Double-Booking Prevention**:
   - Booking conflicts are evaluated atomically inside database transactions using the overlap condition:
     $$(b.\text{start\_time} < \text{new\_end\_time}) \land (b.\text{end\_time} > \text{new\_start\_time})$$
   - Adjacent/back-to-back bookings (e.g., `08:00 - 10:00` and `10:00 - 12:00`) are permitted.

3. **Campus Navigation & Distance Calculator**:
   - Computes walking distance (in meters) and estimated walking time (in minutes) from campus landmarks (e.g. Main Gate, Library, Student Centre) to any lecture hall using the Haversine formula at $1.4\text{ m/s}$ walking speed.

4. **Security & Session Authentication**:
   - Password hashing with Werkzeug (scrypt/pbkdf2) with SHA-256 backward compatibility.
   - Session-based authentication where identity is derived server-side.
   - Cross-user cancellation protection and admin registration restrictions.

---

## 📡 REST API Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves the browser web interface | No |
| `GET` | `/api/health` | Health check endpoint | No |
| `GET` | `/map-html` | Interactive Folium campus map HTML | No |
| `GET` | `/api/auth/me` | Current authenticated session user | No |
| `POST` | `/api/users/register` | Register new class rep or lecturer account | No |
| `POST` | `/api/users/login` | Sign in with email & password | No |
| `POST` | `/api/users/logout` | Sign out and clear session | Yes |
| `GET` | `/api/buildings` | List all campus buildings | No |
| `GET` | `/api/rooms` | List rooms (supports `building_id`, `min_capacity`) | No |
| `GET` | `/api/rooms/<id>/status` | Real-time occupancy status for a specific room | No |
| `GET` | `/api/rooms/status-map` | Real-time status for all rooms (used by map & directory) | No |
| `GET` | `/api/users/<id>/bookings` | Confirmed bookings for a user | Yes |
| `POST` | `/api/bookings` | Book a lecture room (conflict checked) | Yes |
| `POST` | `/api/bookings/<id>/cancel` | Cancel an active booking | Yes |
| `POST` | `/api/db/seed` | Reset & re-seed JKUAT sample data | No |
