import os
import sys
import math
from datetime import datetime, timedelta
import streamlit as st
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium

# Ensure project directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import DB_PATH
from database.seed import seed_database
from models import (
    get_all_buildings,
    get_all_rooms,
    get_room_status,
    create_booking,
    cancel_booking,
    get_bookings_by_room,
    get_user_by_email,
    create_user
)

# ---------------------------------------------------------------------------
# Helper: Distance & Walk Time Calculation (Haversine Formula)
# ---------------------------------------------------------------------------
def calculate_distance_and_walk_time(lat1, lon1, lat2, lon2):
    """Calculates distance in meters and estimated walking time in minutes."""
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
    walk_minutes = max(1, math.ceil(distance_meters / 84.0)) # ~1.4 m/s walking speed
    
    return round(distance_meters), walk_minutes

# ---------------------------------------------------------------------------
# Streamlit Page Config & Styling
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ClassSpace | JKUAT Navigation & Room Finder",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #94a3b8;
        margin-bottom: 1.5rem;
    }
    .nav-card {
        background-color: rgba(56, 189, 248, 0.1);
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* Keep the Streamlit layout usable on phone-sized viewports. */
    @media (max-width: 640px) {
        [data-testid="stAppViewContainer"] {
            padding: 0;
        }

        [data-testid="stMainBlockContainer"] {
            padding: 1rem 0.75rem 2rem;
        }

        [data-testid="stHorizontalBlock"] {
            gap: 0.75rem;
        }

        [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        [data-testid="stTabs"] [role="tablist"] {
            overflow-x: auto;
            scrollbar-width: none;
            white-space: nowrap;
        }

        [data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {
            display: none;
        }

        [data-testid="stTabs"] button {
            flex: 0 0 auto;
            min-height: 3rem;
            padding: 0.5rem 0.75rem;
        }

        [data-testid="stMetric"] {
            padding: 0.75rem;
        }

        [data-testid="stButton"] button,
        [data-testid="stLinkButton"] a,
        [data-testid="stFormSubmitButton"] button {
            min-height: 2.75rem;
            width: 100%;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Session State for Target Navigation Room
if 'target_room_id' not in st.session_state:
    st.session_state['target_room_id'] = None

# ---------------------------------------------------------------------------
# Sidebar Filters & Location Settings
# ---------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/isometric-folders/100/graduation-cap.png", width=64)
st.sidebar.title("ClassSpace JKUAT")
st.sidebar.markdown("**Lecture Room Finder & Campus Navigation**")

st.sidebar.divider()
st.sidebar.subheader("📍 My Current Location")

CAMPUS_LANDMARKS = {
    "🚪 JKUAT Main Gate": (-1.0970, 37.0120),
    "📚 JKUAT Main Library": (-1.0940, 37.0150),
    "🥪 Student Centre / Mess": (-1.0952, 37.0145),
    "🏢 Administration Block": (-1.0960, 37.0135),
    "🏠 Assembly Hall / Gate B": (-1.0932, 37.0175),
}

selected_landmark = st.sidebar.selectbox("Starting Location", list(CAMPUS_LANDMARKS.keys()))
user_lat, user_lng = CAMPUS_LANDMARKS[selected_landmark]

st.sidebar.divider()
st.sidebar.subheader("📅 Date & Time Filter")

selected_date = st.sidebar.date_input("Select Date", datetime.now().date())
selected_time = st.sidebar.time_input("Select Time", datetime.now().time())

date_str = selected_date.strftime('%Y-%m-%d')
time_str = selected_time.strftime('%H:%M')

st.sidebar.divider()
st.sidebar.subheader("🏢 Location & Room Filters")

buildings = get_all_buildings()
building_options = {"All Campus Buildings": None}
for b in buildings:
    building_options[b['name']] = b['id']

selected_building_name = st.sidebar.selectbox("Filter Building", list(building_options.keys()))
selected_building_id = building_options[selected_building_name]

min_capacity = st.sidebar.slider("Minimum Capacity (Seats)", min_value=0, max_value=300, value=0, step=10)
selected_status_filter = st.sidebar.selectbox("Room Status Filter", ["All Statuses", "Free Only (Green)", "Booked Soon Only (Yellow)", "Occupied Only (Red)"])

st.sidebar.divider()
if st.sidebar.button("🔄 Reset / Seed JKUAT Database"):
    seed_database()
    st.sidebar.success("Database seeded with JKUAT sample data!")
    st.rerun()

# ---------------------------------------------------------------------------
# Data Processing & Stats
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">🎓 ClassSpace JKUAT</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Real-time room occupancy & walking navigation for <strong>{date_str}</strong> at <strong>{time_str}</strong></div>', unsafe_allow_html=True)

rooms = get_all_rooms(building_id=selected_building_id, min_capacity=min_capacity)

room_status_list = []
free_count = 0
soon_count = 0
occupied_count = 0

for room in rooms:
    status_info = get_room_status(room['id'], date_str, time_str)
    status_code = status_info['status']
    
    if status_code == 'free':
        free_count += 1
    elif status_code == 'booked_soon':
        soon_count += 1
    elif status_code == 'occupied':
        occupied_count += 1
        
    room_status_list.append({
        **room,
        **status_info
    })

if selected_status_filter == "Free Only (Green)":
    filtered_rooms = [r for r in room_status_list if r['status'] == 'free']
elif selected_status_filter == "Booked Soon Only (Yellow)":
    filtered_rooms = [r for r in room_status_list if r['status'] == 'booked_soon']
elif selected_status_filter == "Occupied Only (Red)":
    filtered_rooms = [r for r in room_status_list if r['status'] == 'occupied']
else:
    filtered_rooms = room_status_list

# Stat Metrics
metric_row_one = st.columns(2)
metric_row_one[0].metric("Total Rooms", len(rooms))
metric_row_one[1].metric("🟢 Free Now", free_count)
metric_row_two = st.columns(2)
metric_row_two[0].metric("🟡 Booked Soon", soon_count)
metric_row_two[1].metric("🔴 Occupied Now", occupied_count)

st.divider()

# ---------------------------------------------------------------------------
# Tabs Navigation
# ---------------------------------------------------------------------------
tab_map, tab_rooms, tab_book, tab_my_bookings = st.tabs([
    "🗺️ Interactive Campus Map & Navigation",
    "📋 Room Directory & Schedules",
    "➕ Book a Room",
    "🔖 My Bookings"
])

# ---------------------------------------------------------------------------
# Tab 1: Map & Campus Walking Route
# ---------------------------------------------------------------------------
with tab_map:
    col_map_view, col_route_panel = st.columns([2.5, 1])
    
    # Build list of options for destination room selectbox
    nav_room_options = {"-- Select Room to Navigate --": None}
    nav_default_index = 0
    
    for idx, r in enumerate(room_status_list):
        label = f"{r['name']} ({r['building_name']})"
        nav_room_options[label] = r
        if st.session_state['target_room_id'] == r['id']:
            nav_default_index = idx + 1

    with col_route_panel:
        st.markdown("### 🚶 Campus Navigation")
        st.caption(f"Starting from: **{selected_landmark}**")
        
        target_nav_key = st.selectbox(
            "Destination Room", 
            list(nav_room_options.keys()), 
            index=nav_default_index
        )
        target_nav_room = nav_room_options[target_nav_key]
        
        if target_nav_room:
            st.session_state['target_room_id'] = target_nav_room['id']
            dest_lat = target_nav_room.get('latitude') or -1.0945
            dest_lng = target_nav_room.get('longitude') or 37.0155
            
            dist_m, walk_mins = calculate_distance_and_walk_time(user_lat, user_lng, dest_lat, dest_lng)
            
            st.markdown(f"""
            <div class="nav-card">
                <h4 style="margin:0; color:#38bdf8;">🎯 Destination: {target_nav_room['name']}</h4>
                <p style="margin:4px 0 0 0; color:#94a3b8; font-size:0.9rem;">Building: {target_nav_room['building_name']}</p>
                <hr style="margin:8px 0; border:0; border-top:1px solid rgba(255,255,255,0.1);">
                <p style="margin:0; font-size:1rem;"><strong>📏 Distance:</strong> {dist_m} meters</p>
                <p style="margin:4px 0 0 0; font-size:1rem;"><strong>⏱️ Est. Walk Time:</strong> ~{walk_mins} min{'s' if walk_mins > 1 else ''}</p>
            </div>
            """, unsafe_allow_html=True)
            
            gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lng}&destination={dest_lat},{dest_lng}&travelmode=walking"
            st.link_button("🗺️ Open Google Maps Walking Route", gmaps_url, use_container_width=True)

    with col_map_view:
        m = folium.Map(location=[-1.0948, 37.0152], zoom_start=17, tiles="ESRI.WorldImagery")
        
        # User Location Pin
        folium.Marker(
            location=[user_lat, user_lng],
            popup=f"<b>My Location</b><br>{selected_landmark}",
            tooltip=f"My Location: {selected_landmark}",
            icon=folium.Icon(color='blue', icon='user', prefix='fa')
        ).add_to(m)
        
        # Room Pins
        for room in filtered_rooms:
            lat = room.get('latitude') or -1.0945
            lng = room.get('longitude') or 37.0155
            
            status = room['status']
            if status == 'free':
                color = 'green'
                icon_name = 'check-circle'
                status_text = '🟢 FREE NOW'
            elif status == 'booked_soon':
                color = 'orange'
                icon_name = 'clock'
                status_text = '🟡 BOOKED SOON'
            else:
                color = 'red'
                icon_name = 'ban'
                status_text = '🔴 OCCUPIED'
                
            popup_html = f"""
            <div style="font-family: Arial, sans-serif; width: 210px;">
                <h4 style="margin: 0 0 5px 0;">{room['name']}</h4>
                <p style="margin: 0; font-size: 12px; color: #64748b;"><b>Building:</b> {room['building_name']}</p>
                <p style="margin: 0; font-size: 12px; color: #64748b;"><b>Capacity:</b> {room['capacity']} seats</p>
                <hr style="margin: 6px 0; border: 0; border-top: 1px solid #cbd5e1;">
                <p style="margin: 0;"><b>Status:</b> {status_text}</p>
            </div>
            """
            
            folium.Marker(
                location=[lat, lng],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{room['name']} ({room['building_name']})",
                icon=folium.Icon(color=color, icon=icon_name, prefix='fa')
            ).add_to(m)

        # Draw Animated Path to Target Room
        if target_nav_room:
            dest_lat = target_nav_room.get('latitude') or -1.0945
            dest_lng = target_nav_room.get('longitude') or 37.0155
            
            AntPath(
                locations=[[user_lat, user_lng], [dest_lat, dest_lng]],
                color='#38bdf8',
                weight=5,
                opacity=0.8,
                dash_array=[10, 20],
                delay=1000,
                popup=f"Path to {target_nav_room['name']} ({dist_m}m)"
            ).add_to(m)
            
            m.fit_bounds([[user_lat, user_lng], [dest_lat, dest_lng]], padding=[40, 40])
            
        st_folium(m, width="100%", height=530, key="folium_campus_nav_map")

# ---------------------------------------------------------------------------
# Tab 2: Room Directory & Schedules
# ---------------------------------------------------------------------------
with tab_rooms:
    st.subheader("Lecture Room Directory")
    search_query = st.text_input("🔍 Search room name or building...", "")
    
    display_rooms = [r for r in filtered_rooms if search_query.lower() in r['name'].lower() or search_query.lower() in r['building_name'].lower()]
    
    if not display_rooms:
        st.info("No lecture rooms found matching your search.")
    else:
        for room in display_rooms:
            with st.expander(f"📍 {room['name']} — {room['building_name']} (Cap: {room['capacity']} seats) | {room['status'].upper()}"):
                col_info, col_sched = st.columns([1, 1.5])
                
                with col_info:
                    st.write(f"**Building:** {room['building_name']}")
                    st.write(f"**Capacity:** {room['capacity']} seats")
                    
                    if room['status'] == 'free':
                        st.success("🟢 Status: Free now & for at least 1 hour")
                    elif room['status'] == 'booked_soon':
                        st.warning(f"🟡 Status: Booked soon ({room.get('next_free_time')})")
                    else:
                        st.error(f"🔴 Status: Occupied until {room.get('next_free_time')}")
                        
                    # --- NEW: Action Button to Map Route from My Location to Picked Room ---
                    dest_lat = room.get('latitude') or -1.0945
                    dest_lng = room.get('longitude') or 37.0155
                    dist_m, walk_mins = calculate_distance_and_walk_time(user_lat, user_lng, dest_lat, dest_lng)
                    
                    st.markdown(f"🚶 **Distance from {selected_landmark.split(' ')[1] if ' ' in selected_landmark else selected_landmark}:** {dist_m}m (~{walk_mins} mins walk)")
                    
                    if st.button(f"🗺️ Map Path to {room['name']}", key=f"btn_nav_{room['id']}", type="primary"):
                        st.session_state['target_room_id'] = room['id']
                        st.success(f"🎯 Route set to {room['name']}! Click on the **'Interactive Campus Map & Navigation'** tab to view your live map route.")
                        st.rerun()

                with col_sched:
                    st.write("**Confirmed Bookings for Today:**")
                    bookings = get_bookings_by_room(room['id'], date_str=date_str)
                    if bookings:
                        for b in bookings:
                            st.write(f"• `{b['start_time']} - {b['end_time']}`: **{b['course_unit']}** ({b['user_name']})")
                    else:
                        st.caption("No confirmed bookings scheduled for today.")

# ---------------------------------------------------------------------------
# Tab 3: Book a Room
# ---------------------------------------------------------------------------
with tab_book:
    st.subheader("➕ Book a Lecture Room")
    st.caption("Select a room, date, and time slot. The system automatically enforces double-booking prevention rules.")
    
    with st.form("booking_form"):
        room_options = {f"{r['name']} ({r['building_name']} - Cap: {r['capacity']})": r['id'] for r in rooms}
        selected_room_label = st.selectbox("Select Lecture Room", list(room_options.keys()))
        target_room_id = room_options[selected_room_label]
        
        course_unit = st.text_input("Course Unit / Event Title *", placeholder="e.g. ICS 2101: Data Structures")
        user_email = st.text_input("Your Email Address *", value="brian.kiprop@students.jkuat.ac.ke")
        
        b_date = st.date_input("Booking Date", datetime.now().date())
        
        col_start, col_end = st.columns(2)
        with col_start:
            b_start_time = st.time_input("Start Time", datetime.strptime("08:00", "%H:%M").time())
        with col_end:
            b_end_time = st.time_input("End Time", datetime.strptime("10:00", "%H:%M").time())
            
        submit_btn = st.form_submit_button("Confirm Booking", type="primary")
        
        if submit_btn:
            if not course_unit or not user_email:
                st.error("Please fill in all required fields (Course Unit & Email).")
            else:
                user = get_user_by_email(user_email)
                if not user:
                    user = create_user("Student Rep", user_email, "class_rep", "BSc CS", "password123")
                    
                b_date_str = b_date.strftime('%Y-%m-%d')
                b_start_str = b_start_time.strftime('%H:%M')
                b_end_str = b_end_time.strftime('%H:%M')
                
                try:
                    booking = create_booking(
                        room_id=target_room_id,
                        user_id=user['id'],
                        course_unit=course_unit,
                        date_str=b_date_str,
                        start_time_str=b_start_str,
                        end_time_str=b_end_str
                    )
                    st.success(f"🎉 Booking Confirmed! '{course_unit}' booked in {selected_room_label} on {b_date_str} ({b_start_str}-{b_end_str}).")
                    st.balloons()
                except ValueError as e:
                    st.error(f"❌ {str(e)}")

# ---------------------------------------------------------------------------
# Tab 4: My Active Bookings
# ---------------------------------------------------------------------------
with tab_my_bookings:
    st.subheader("🔖 Active Room Bookings")
    
    search_email = st.text_input("Enter user email to view bookings:", value="brian.kiprop@students.jkuat.ac.ke")
    user = get_user_by_email(search_email)
    
    if not user:
        st.info("User not found.")
    else:
        user_bookings = []
        for r in rooms:
            b_list = get_bookings_by_room(r['id'])
            for b in b_list:
                if b['user_id'] == user['id']:
                    user_bookings.append({**b, "room_name": r['name']})
                    
        if not user_bookings:
            st.info(f"No active bookings found for {search_email}.")
        else:
            for b in user_bookings:
                col_details, col_cancel = st.columns([3, 1])
                with col_details:
                    st.markdown(f"**{b['course_unit']}** — Room: `{b['room_name']}`")
                    st.caption(f"📅 Date: {b['date']} | ⏰ Time: {b['start_time']} - {b['end_time']}")
                    
                    # --- NEW: Action Button to Map Route from My Location to Booked Room ---
                    if st.button(f"🗺️ Map Path to {b['room_name']}", key=f"btn_nav_my_booking_{b['id']}"):
                        st.session_state['target_room_id'] = b['room_id']
                        st.success(f"🎯 Route set to {b['room_name']}! Switch to the **'Interactive Campus Map & Navigation'** tab to view your route.")
                        st.rerun()

                with col_cancel:
                    if st.button("Cancel Booking", key=f"cancel_{b['id']}"):
                        cancel_booking(b['id'], user_id=user['id'])
                        st.success("Booking cancelled successfully!")
                        st.rerun()
                st.divider()
