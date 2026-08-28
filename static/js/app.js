/**
 * ClassSpace JKUAT - Primary Browser Application Logic
 * Lecture Room Finder & Walking Campus Navigation
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Application State ---
    const state = {
        originLat: -1.0970,
        originLng: 37.0120,
        originName: 'JKUAT Main Gate',
        selectedDate: '',
        selectedTime: '',
        selectedBuildingId: '',
        selectedStatus: 'all',
        searchQuery: '',
        destRoomId: null,
        rooms: [],
        buildings: [],
        currentUser: null
    };

    // --- DOM Elements ---
    const userLocationSelect = document.getElementById('user-location-select');
    const filterDateInput = document.getElementById('filter-date');
    const filterTimeInput = document.getElementById('filter-time');
    const btnRefreshStatus = document.getElementById('btn-refresh-status');
    const userNavContainer = document.getElementById('user-nav-container');

    const statTotalRooms = document.getElementById('stat-total-rooms');
    const statFreeRooms = document.getElementById('stat-free-rooms');
    const statSoonRooms = document.getElementById('stat-soon-rooms');
    const statOccupiedRooms = document.getElementById('stat-occupied-rooms');

    const filterCardFree = document.getElementById('filter-card-free');
    const filterCardSoon = document.getElementById('filter-card-soon');
    const filterCardOccupied = document.getElementById('filter-card-occupied');

    const foliumMapFrame = document.getElementById('folium-map-frame');
    const searchInput = document.getElementById('search-input');
    const filterBuilding = document.getElementById('filter-building');
    const filterStatus = document.getElementById('filter-status');
    const roomsListContainer = document.getElementById('rooms-list-container');
    const btnSeedData = document.getElementById('btn-seed-data');

    // Modals
    const modalBooking = document.getElementById('modal-booking');
    const btnCloseBooking = document.getElementById('btn-close-booking');
    const btnCancelModal = document.getElementById('btn-cancel-modal');
    const formCreateBooking = document.getElementById('form-create-booking');
    const bookingRoomSelect = document.getElementById('booking-room-select');
    const bookingCourseUnit = document.getElementById('booking-course-unit');
    const bookingUserEmail = document.getElementById('booking-user-email');
    const bookingDate = document.getElementById('booking-date');
    const bookingStartTime = document.getElementById('booking-start-time');
    const bookingEndTime = document.getElementById('booking-end-time');
    const bookingErrorAlert = document.getElementById('booking-error-alert');

    const modalAuth = document.getElementById('modal-auth');
    const btnCloseAuth = document.getElementById('btn-close-auth');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const formLogin = document.getElementById('form-login');
    const formRegister = document.getElementById('form-register');
    const loginErrorAlert = document.getElementById('login-error-alert');
    const regErrorAlert = document.getElementById('reg-error-alert');

    const modalMyBookings = document.getElementById('modal-my-bookings');
    const btnCloseMyBookings = document.getElementById('btn-close-my-bookings');
    const myBookingsContainer = document.getElementById('my-bookings-container');

    // --- Helper: Format Date & Time ---
    function initDateTimeDefaults() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        state.selectedDate = `${year}-${month}-${day}`;

        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        state.selectedTime = `${hours}:${minutes}`;

        if (filterDateInput) filterDateInput.value = state.selectedDate;
        if (filterTimeInput) filterTimeInput.value = state.selectedTime;

        if (bookingDate) bookingDate.value = state.selectedDate;
        if (bookingStartTime) bookingStartTime.value = "08:00";
        if (bookingEndTime) bookingEndTime.value = "10:00";
    }

    // --- Distance & Walk Time Calculation (Haversine Formula) ---
    function calculateDistanceAndWalkTime(lat1, lon1, lat2, lon2) {
        const R = 6371000; // meters
        const phi1 = (lat1 * Math.PI) / 180;
        const phi2 = (lat2 * Math.PI) / 180;
        const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
        const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

        const a = Math.sin(deltaPhi / 2) ** 2 +
                  Math.cos(phi1) * Math.cos(phi2) *
                  Math.sin(deltaLambda / 2) ** 2;
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distanceMeters = Math.round(R * c);
        const walkMinutes = Math.max(1, Math.ceil(distanceMeters / 84.0)); // ~1.4 m/s walking speed
        return { distanceMeters, walkMinutes };
    }

    // --- Update Folium Map Iframe ---
    function updateMapIframe() {
        if (!foliumMapFrame) return;
        let url = `/map-html?origin_lat=${state.originLat}&origin_lng=${state.originLng}&date=${state.selectedDate}&time=${state.selectedTime}`;
        if (state.destRoomId) {
            url += `&dest_room_id=${state.destRoomId}`;
        }
        if (state.selectedBuildingId) {
            url += `&building_id=${state.selectedBuildingId}`;
        }
        foliumMapFrame.src = url;
    }

    // --- Authentication & Session Management ---
    async function checkAuthSession() {
        try {
            const res = await fetch('/api/auth/me');
            const data = await res.json();
            if (data.authenticated && data.user) {
                state.currentUser = data.user;
                renderUserNavLoggedIn(data.user);
            } else {
                state.currentUser = null;
                renderUserNavLoggedOut();
            }
        } catch (err) {
            console.error('Error verifying auth session:', err);
            renderUserNavLoggedOut();
        }
    }

    function renderUserNavLoggedIn(user) {
        if (!userNavContainer) return;
        userNavContainer.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.8rem;">
                <span style="font-size: 0.88rem; color: #38bdf8;">
                    <i class="fa-solid fa-user-check"></i> ${user.name} <small style="color: #94a3b8;">(${user.role})</small>
                </span>
                <button id="btn-view-my-bookings" class="btn btn-secondary btn-sm" title="View My Bookings">
                    <i class="fa-solid fa-bookmark"></i> My Bookings
                </button>
                <button id="btn-logout" class="btn btn-outline btn-sm" title="Sign Out">
                    <i class="fa-solid fa-right-from-bracket"></i>
                </button>
            </div>
        `;
        document.getElementById('btn-view-my-bookings').addEventListener('click', openMyBookingsModal);
        document.getElementById('btn-logout').addEventListener('click', handleLogout);
    }

    function renderUserNavLoggedOut() {
        if (!userNavContainer) return;
        userNavContainer.innerHTML = `
            <button id="btn-open-login" class="btn btn-primary">
                <i class="fa-solid fa-user-lock"></i> Login / Register
            </button>
        `;
        document.getElementById('btn-open-login').addEventListener('click', () => openAuthModal('login'));
    }

    async function handleLogout() {
        try {
            await fetch('/api/users/logout', { method: 'POST' });
            state.currentUser = null;
            renderUserNavLoggedOut();
            await fetchRoomsAndStatus();
        } catch (err) {
            console.error('Error logging out:', err);
        }
    }

    // --- Fetch Buildings ---
    async function fetchBuildings() {
        try {
            const res = await fetch('/api/buildings');
            const buildings = await res.json();
            state.buildings = buildings;

            // Populate filter building dropdown
            if (filterBuilding) {
                filterBuilding.innerHTML = '<option value="">All Campus Buildings</option>';
                buildings.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.id;
                    opt.textContent = b.name;
                    filterBuilding.appendChild(opt);
                });
            }

            // Populate room select in booking form
            populateBookingRoomOptions();
        } catch (err) {
            console.error('Error fetching campus buildings:', err);
        }
    }

    function populateBookingRoomOptions() {
        if (!bookingRoomSelect) return;
        bookingRoomSelect.innerHTML = '<option value="">-- Select Lecture Room --</option>';
        state.rooms.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.room_id || r.id;
            opt.textContent = `${r.room_name || r.name} (${r.building_name} - Cap: ${r.capacity} seats)`;
            bookingRoomSelect.appendChild(opt);
        });
    }

    // --- Fetch Rooms & Live Status ---
    async function fetchRoomsAndStatus() {
        if (roomsListContainer) {
            roomsListContainer.innerHTML = `
                <div class="loading-spinner">
                    <i class="fa-solid fa-circle-notch fa-spin"></i> Fetching live lecture room data...
                </div>
            `;
        }

        try {
            let url = `/api/rooms/status-map?date=${state.selectedDate}&time=${state.selectedTime}`;
            if (state.selectedBuildingId) {
                url += `&building_id=${state.selectedBuildingId}`;
            }

            const res = await fetch(url);
            const data = await res.json();
            state.rooms = data.rooms || [];

            renderStats(state.rooms);
            renderRoomsList(state.rooms);
            populateBookingRoomOptions();
        } catch (err) {
            console.error('Error fetching rooms status map:', err);
            if (roomsListContainer) {
                roomsListContainer.innerHTML = `
                    <div style="padding: 1.5rem; text-align: center; color: #ef4444;">
                        <i class="fa-solid fa-triangle-exclamation"></i> Unable to load room data. Please check database connection.
                    </div>
                `;
            }
        }
    }

    // --- Render Stat Metric Cards ---
    function renderStats(rooms) {
        let freeCount = 0;
        let soonCount = 0;
        let occupiedCount = 0;

        rooms.forEach(r => {
            if (r.status === 'free') freeCount++;
            else if (r.status === 'booked_soon') soonCount++;
            else if (r.status === 'occupied') occupiedCount++;
        });

        if (statTotalRooms) statTotalRooms.textContent = rooms.length;
        if (statFreeRooms) statFreeRooms.textContent = freeCount;
        if (statSoonRooms) statSoonRooms.textContent = soonCount;
        if (statOccupiedRooms) statOccupiedRooms.textContent = occupiedCount;
    }

    // --- Render Rooms Directory Cards ---
    function renderRoomsList(rooms) {
        if (!roomsListContainer) return;

        let filtered = rooms.filter(r => {
            const matchesSearch = !state.searchQuery ||
                r.room_name.toLowerCase().includes(state.searchQuery.toLowerCase()) ||
                r.building_name.toLowerCase().includes(state.searchQuery.toLowerCase());

            const matchesStatus = (state.selectedStatus === 'all') || (r.status === state.selectedStatus);
            return matchesSearch && matchesStatus;
        });

        if (filtered.length === 0) {
            roomsListContainer.innerHTML = `
                <div style="padding: 2rem; text-align: center; color: #94a3b8;">
                    <i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 0.5rem; display: block;"></i>
                    No lecture rooms found matching your filters.
                </div>
            `;
            return;
        }

        roomsListContainer.innerHTML = '';
        filtered.forEach(room => {
            const card = document.createElement('div');
            card.className = 'room-item-card';

            const roomLat = room.latitude || -1.0945;
            const roomLng = room.longitude || 37.0155;
            const { distanceMeters, walkMinutes } = calculateDistanceAndWalkTime(state.originLat, state.originLng, roomLat, roomLng);

            let statusBadgeClass = 'status-free';
            let statusText = '🟢 Free Now';
            let statusDetail = 'Free for next hour';

            if (room.status === 'booked_soon') {
                statusBadgeClass = 'status-booked_soon';
                statusText = '🟡 Booked Soon';
                statusDetail = room.next_free_time || 'Starting soon';
            } else if (room.status === 'occupied') {
                statusBadgeClass = 'status-occupied';
                statusText = '🔴 Occupied';
                statusDetail = `Until ${room.next_free_time || 'end of session'}`;
            }

            card.innerHTML = `
                <div class="room-info">
                    <h4>${room.room_name} <span class="status-badge ${statusBadgeClass}">${statusText}</span></h4>
                    <p class="building-name"><i class="fa-solid fa-building"></i> ${room.building_name} &bull; Capacity: ${room.capacity} seats</p>
                    <div class="room-details-row">
                        <span><i class="fa-solid fa-clock"></i> ${statusDetail}</span>
                        <span><i class="fa-solid fa-person-walking"></i> ~${distanceMeters}m from ${state.originName} (~${walkMinutes} min walk)</span>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="btn btn-primary btn-sm btn-map-route" data-room-id="${room.room_id}">
                        <i class="fa-solid fa-route"></i> Map Path
                    </button>
                    <button class="btn btn-secondary btn-sm btn-quick-book" data-room-id="${room.room_id}" data-room-name="${room.room_name}">
                        <i class="fa-solid fa-calendar-plus"></i> Book
                    </button>
                </div>
            `;

            card.querySelector('.btn-map-route').addEventListener('click', () => {
                mapPathToRoom(room.room_id);
            });

            card.querySelector('.btn-quick-book').addEventListener('click', () => {
                openBookingModal(room.room_id);
            });

            roomsListContainer.appendChild(card);
        });
    }

    // --- Map Walking Route to Picked Room ---
    function mapPathToRoom(roomId) {
        state.destRoomId = roomId;
        updateMapIframe();
        if (foliumMapFrame) {
            foliumMapFrame.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    // --- Booking Modal Logic ---
    function openBookingModal(preselectedRoomId = null) {
        if (!state.currentUser) {
            openAuthModal('login');
            alert('Please sign in to book a lecture room.');
            return;
        }

        if (bookingErrorAlert) bookingErrorAlert.style.display = 'none';
        if (bookingUserEmail) bookingUserEmail.value = state.currentUser.email;
        if (bookingDate) bookingDate.value = state.selectedDate;

        if (preselectedRoomId && bookingRoomSelect) {
            bookingRoomSelect.value = preselectedRoomId;
        }

        modalBooking.classList.add('active');
    }

    function closeBookingModal() {
        modalBooking.classList.remove('active');
        if (formCreateBooking) formCreateBooking.reset();
        if (bookingErrorAlert) bookingErrorAlert.style.display = 'none';
    }

    if (btnCloseBooking) btnCloseBooking.addEventListener('click', closeBookingModal);
    if (btnCancelModal) btnCancelModal.addEventListener('click', closeBookingModal);

    if (formCreateBooking) {
        formCreateBooking.addEventListener('submit', async (e) => {
            e.preventDefault();
            bookingErrorAlert.style.display = 'none';

            const payload = {
                room_id: parseInt(bookingRoomSelect.value, 10),
                course_unit: bookingCourseUnit.value.trim(),
                date: bookingDate.value,
                start_time: bookingStartTime.value,
                end_time: bookingEndTime.value
            };

            try {
                const res = await fetch('/api/bookings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                const data = await res.json();
                if (!res.ok) {
                    bookingErrorAlert.textContent = data.error || 'Failed to complete booking.';
                    bookingErrorAlert.style.display = 'block';
                    return;
                }

                alert(`🎉 Booking confirmed! '${payload.course_unit}' booked successfully.`);
                closeBookingModal();
                await fetchRoomsAndStatus();
                updateMapIframe();
            } catch (err) {
                bookingErrorAlert.textContent = 'A network error occurred. Please try again.';
                bookingErrorAlert.style.display = 'block';
            }
        });
    }

    // --- Authentication Modal Logic ---
    function openAuthModal(tab = 'login') {
        modalAuth.classList.add('active');
        switchAuthTab(tab);
    }

    function closeAuthModal() {
        modalAuth.classList.remove('active');
        if (formLogin) formLogin.reset();
        if (formRegister) formRegister.reset();
        if (loginErrorAlert) loginErrorAlert.style.display = 'none';
        if (regErrorAlert) regErrorAlert.style.display = 'none';
    }

    function switchAuthTab(tab) {
        if (tab === 'login') {
            tabLogin.classList.add('active');
            tabRegister.classList.remove('active');
            formLogin.style.display = 'block';
            formRegister.style.display = 'none';
        } else {
            tabRegister.classList.add('active');
            tabLogin.classList.remove('active');
            formRegister.style.display = 'block';
            formLogin.style.display = 'none';
        }
    }

    if (btnCloseAuth) btnCloseAuth.addEventListener('click', closeAuthModal);
    if (tabLogin) tabLogin.addEventListener('click', () => switchAuthTab('login'));
    if (tabRegister) tabRegister.addEventListener('click', () => switchAuthTab('register'));

    // Login Form Submit
    if (formLogin) {
        formLogin.addEventListener('submit', async (e) => {
            e.preventDefault();
            loginErrorAlert.style.display = 'none';

            const payload = {
                email: document.getElementById('login-email').value.trim(),
                password: document.getElementById('login-password').value
            };

            try {
                const res = await fetch('/api/users/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (!res.ok) {
                    loginErrorAlert.textContent = data.error || 'Invalid credentials.';
                    loginErrorAlert.style.display = 'block';
                    return;
                }

                state.currentUser = data.user;
                renderUserNavLoggedIn(data.user);
                closeAuthModal();
            } catch (err) {
                loginErrorAlert.textContent = 'Network error during login.';
                loginErrorAlert.style.display = 'block';
            }
        });
    }

    // Register Form Submit
    if (formRegister) {
        formRegister.addEventListener('submit', async (e) => {
            e.preventDefault();
            regErrorAlert.style.display = 'none';

            const payload = {
                name: document.getElementById('reg-name').value.trim(),
                email: document.getElementById('reg-email').value.trim(),
                role: document.getElementById('reg-role').value,
                course: document.getElementById('reg-course').value.trim(),
                password: document.getElementById('reg-password').value
            };

            try {
                const res = await fetch('/api/users/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (!res.ok) {
                    regErrorAlert.textContent = data.error || 'Registration failed.';
                    regErrorAlert.style.display = 'block';
                    return;
                }

                state.currentUser = data.user;
                renderUserNavLoggedIn(data.user);
                closeAuthModal();
                alert('Account created successfully!');
            } catch (err) {
                regErrorAlert.textContent = 'Network error during registration.';
                regErrorAlert.style.display = 'block';
            }
        });
    }

    // --- My Bookings Modal Logic ---
    async function openMyBookingsModal() {
        if (!state.currentUser) return;
        modalMyBookings.classList.add('active');
        myBookingsContainer.innerHTML = '<p class="text-muted"><i class="fa-solid fa-spinner fa-spin"></i> Loading your bookings...</p>';

        try {
            const res = await fetch(`/api/users/${state.currentUser.id}/bookings`);
            const bookings = await res.json();

            if (!bookings || bookings.length === 0) {
                myBookingsContainer.innerHTML = `
                    <div style="padding: 2rem; text-align: center; color: #94a3b8;">
                        <p>You have no active bookings scheduled.</p>
                    </div>
                `;
                return;
            }

            myBookingsContainer.innerHTML = '';
            bookings.forEach(b => {
                const item = document.createElement('div');
                item.className = 'room-item-card';
                item.style.marginBottom = '1rem';
                item.innerHTML = `
                    <div>
                        <h4>${b.course_unit} &bull; <small style="color: #38bdf8;">${b.room_name} (${b.building_name})</small></h4>
                        <p style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">
                            <i class="fa-regular fa-calendar"></i> Date: <strong>${b.date}</strong> &bull;
                            <i class="fa-regular fa-clock"></i> Time: <strong>${b.start_time} - ${b.end_time}</strong>
                        </p>
                    </div>
                    <div class="card-actions">
                        <button class="btn btn-secondary btn-sm btn-map-my-booking" data-room-id="${b.room_id}">
                            <i class="fa-solid fa-route"></i> Map Route
                        </button>
                        <button class="btn btn-outline btn-sm btn-cancel-booking" data-booking-id="${b.id}" style="color: #ef4444; border-color: #ef4444;">
                            <i class="fa-solid fa-trash-can"></i> Cancel
                        </button>
                    </div>
                `;

                item.querySelector('.btn-map-my-booking').addEventListener('click', () => {
                    closeMyBookingsModal();
                    mapPathToRoom(b.room_id);
                });

                item.querySelector('.btn-cancel-booking').addEventListener('click', async () => {
                    if (confirm(`Are you sure you want to cancel the booking for '${b.course_unit}'?`)) {
                        await cancelBooking(b.id);
                    }
                });

                myBookingsContainer.appendChild(item);
            });
        } catch (err) {
            myBookingsContainer.innerHTML = '<p class="alert alert-error">Failed to load bookings.</p>';
        }
    }

    function closeMyBookingsModal() {
        modalMyBookings.classList.remove('active');
    }

    if (btnCloseMyBookings) btnCloseMyBookings.addEventListener('click', closeMyBookingsModal);

    async function cancelBooking(bookingId) {
        try {
            const res = await fetch(`/api/bookings/${bookingId}/cancel`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();

            if (!res.ok) {
                alert(data.error || 'Failed to cancel booking.');
                return;
            }

            alert('Booking cancelled successfully.');
            await openMyBookingsModal();
            await fetchRoomsAndStatus();
            updateMapIframe();
        } catch (err) {
            alert('Network error while cancelling booking.');
        }
    }

    // --- Seed / Reset Database ---
    if (btnSeedData) {
        btnSeedData.addEventListener('click', async () => {
            if (confirm('Reset and re-seed the JKUAT campus database with default sample data? This will clear active custom bookings.')) {
                try {
                    const res = await fetch('/api/db/seed', { method: 'POST' });
                    const data = await res.json();
                    alert(data.message || 'Database seeded successfully.');
                    await fetchBuildings();
                    await fetchRoomsAndStatus();
                    updateMapIframe();
                } catch (err) {
                    alert('Error seeding database.');
                }
            }
        });
    }

    // --- Event Listeners for Filters ---
    if (userLocationSelect) {
        userLocationSelect.addEventListener('change', (e) => {
            const [lat, lng] = e.target.value.split(',').map(Number);
            state.originLat = lat;
            state.originLng = lng;
            state.originName = e.target.options[e.target.selectedIndex].text;
            renderRoomsList(state.rooms);
            updateMapIframe();
        });
    }

    if (filterDateInput) {
        filterDateInput.addEventListener('change', (e) => {
            state.selectedDate = e.target.value;
            fetchRoomsAndStatus();
            updateMapIframe();
        });
    }

    if (filterTimeInput) {
        filterTimeInput.addEventListener('change', (e) => {
            state.selectedTime = e.target.value;
            fetchRoomsAndStatus();
            updateMapIframe();
        });
    }

    if (btnRefreshStatus) {
        btnRefreshStatus.addEventListener('click', () => {
            fetchRoomsAndStatus();
            updateMapIframe();
        });
    }

    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            state.searchQuery = e.target.value;
            renderRoomsList(state.rooms);
        });
    }

    if (filterBuilding) {
        filterBuilding.addEventListener('change', (e) => {
            state.selectedBuildingId = e.target.value;
            fetchRoomsAndStatus();
            updateMapIframe();
        });
    }

    if (filterStatus) {
        filterStatus.addEventListener('change', (e) => {
            state.selectedStatus = e.target.value;
            renderRoomsList(state.rooms);
        });
    }

    // Stat card quick filters
    if (filterCardFree) {
        filterCardFree.addEventListener('click', () => {
            state.selectedStatus = (state.selectedStatus === 'free') ? 'all' : 'free';
            if (filterStatus) filterStatus.value = state.selectedStatus;
            renderRoomsList(state.rooms);
        });
    }
    if (filterCardSoon) {
        filterCardSoon.addEventListener('click', () => {
            state.selectedStatus = (state.selectedStatus === 'booked_soon') ? 'all' : 'booked_soon';
            if (filterStatus) filterStatus.value = state.selectedStatus;
            renderRoomsList(state.rooms);
        });
    }
    if (filterCardOccupied) {
        filterCardOccupied.addEventListener('click', () => {
            state.selectedStatus = (state.selectedStatus === 'occupied') ? 'all' : 'occupied';
            if (filterStatus) filterStatus.value = state.selectedStatus;
            renderRoomsList(state.rooms);
        });
    }

    // --- App Initialization ---
    initDateTimeDefaults();
    checkAuthSession();
    fetchBuildings();
    fetchRoomsAndStatus();
    updateMapIframe();
});
