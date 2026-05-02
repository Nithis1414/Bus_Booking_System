function saveUsers() {
    localStorage.setItem('nexus_users', JSON.stringify(state.users));
}

const savedUsers = JSON.parse(localStorage.getItem('nexus_users')) || [];

const state = {
    user: null,
    users: savedUsers, // Array of registered user objects: { name, email, pass, bookings: [] }
    search: {
        source: '',
        destination: '',
        date: ''
    },
    buses: [],
    selectedBus: null,
    selectedSeats: [], // Array of seat IDs like '1A', '2B'
    passenger: null,
    routesCache: {}, // Cache to store generated buses per route
    notifications: [],
    unreadNotifs: 0
};

// --- Notifications ---
window.toggleNotifications = function() {
    const panel = document.getElementById('notifications-panel');
    if (panel.classList.contains('d-none')) {
        panel.classList.remove('d-none');
        state.unreadNotifs = 0;
        updateNotifBadge();
        renderNotifications();
    } else {
        panel.classList.add('d-none');
    }
};

window.addNotification = function(message, type = 'info') {
    state.notifications.unshift({
        message,
        type,
        time: new Date()
    });
    state.unreadNotifs++;
    updateNotifBadge();
    if (!document.getElementById('notifications-panel').classList.contains('d-none')) {
        renderNotifications();
    }
};

function updateNotifBadge() {
    const badges = document.querySelectorAll('.notif-badge');
    badges.forEach(badge => {
        if (state.unreadNotifs > 0) {
            badge.innerText = state.unreadNotifs;
            badge.classList.remove('d-none');
        } else {
            badge.classList.add('d-none');
        }
    });
}

function renderNotifications() {
    const list = document.getElementById('notifications-list');
    list.innerHTML = '';
    if (state.notifications.length === 0) {
        list.innerHTML = '<p class="text-muted text-center">No notifications yet.</p>';
        return;
    }
    state.notifications.forEach(n => {
        const div = document.createElement('div');
        div.className = `notif-item ${n.type}`;
        div.innerHTML = `
            <div>${n.message}</div>
            <div class="notif-time">${n.time.toLocaleTimeString()}</div>
        `;
        list.appendChild(div);
    });
}

window.showToast = function(message, type = 'error') {
    window.addNotification(message, type);
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconName = type === 'error' ? 'warning-outline' : 'checkmark-circle-outline';
    toast.innerHTML = `<ion-icon name="${iconName}"></ion-icon> <span>${message}</span>`;
    
    container.appendChild(toast);
    
    // trigger animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // remove after 3s
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000); // Wait 4 seconds for user to read
};

// --- Routing & Navigation ---
window.navigateTo = function(viewId) {
    if (viewId === 'auth') {
        state.user = null;
    }

    // Hide all views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    // Show target view
    const target = document.getElementById('view-' + viewId);
    if(target) {
        target.classList.add('active');
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // Trigger view-specific logic
    if (viewId === 'seats') {
        renderSeats();
        updateSummary();
    }
    if (viewId === 'checkout') {
        document.getElementById('checkout-total').innerText = (state.selectedSeats.length * state.selectedBus.price);
        renderPassengerForms();
    }
    if (viewId === 'dashboard') {
        renderDashboard();
    }
};

function renderPassengerForms() {
    const container = document.getElementById('passenger-forms-container');
    if (!container) return;
    container.innerHTML = '';
    
    state.selectedSeats.forEach((seatId, index) => {
        const div = document.createElement('div');
        div.className = 'passenger-form mb-3';
        div.innerHTML = `
            <p class="text-muted mb-2"><strong style="color:var(--text-primary)">Passenger ${index + 1} (Seat: ${seatId})</strong></p>
            <div class="input-grid">
                <div class="input-group mb-0">
                    <label>Full Name</label>
                    <input type="text" id="pass-name-${seatId}" required placeholder="Passenger Name">
                </div>
                <div class="input-group mb-0">
                    <label>Gender</label>
                    <select id="pass-gender-${seatId}" required style="background: rgba(0, 0, 0, 0.2); border: 1px solid var(--border-color); color: var(--text-primary); padding: 0.875rem 1rem; border-radius: 8px; font-family: 'Inter', sans-serif; font-size: 1rem; appearance: none; outline: none;">
                        <option value="" disabled selected style="color: #000;">Select</option>
                        <option value="M" style="color: #000;">Male</option>
                        <option value="F" style="color: #000;">Female</option>
                        <option value="O" style="color: #000;">Other</option>
                    </select>
                </div>
            </div>
        `;
        container.appendChild(div);
    });
}

window.togglePassword = function(inputId, icon) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.name = 'eye-off-outline';
    } else {
        input.type = 'password';
        icon.name = 'eye-outline';
    }
};

window.togglePaymentMethod = function(method) {
    document.getElementById('label-pay-card').classList.remove('active');
    document.getElementById('label-pay-upi').classList.remove('active');

    if (method === 'card') {
        document.getElementById('label-pay-card').classList.add('active');
        document.getElementById('payment-card').classList.remove('d-none');
        document.getElementById('payment-upi').classList.add('d-none');
        
        // Ensure card fields are required
        document.querySelectorAll('#payment-card input').forEach(inp => inp.required = true);
    } else {
        document.getElementById('label-pay-upi').classList.add('active');
        document.getElementById('payment-card').classList.add('d-none');
        document.getElementById('payment-upi').classList.remove('d-none');

        // Remove required from card fields so form can submit
        document.querySelectorAll('#payment-card input').forEach(inp => inp.required = false);
    }
};

// --- Auth View ---
window.switchAuthTab = function(type) {
    document.querySelectorAll('.auth-tabs .tab').forEach(t => t.classList.remove('active'));
    document.getElementById('form-login').classList.add('d-none');
    document.getElementById('form-signup').classList.add('d-none');
    document.getElementById('form-forgot').classList.add('d-none');
    document.getElementById('form-reset').classList.add('d-none');

    if (type === 'login') {
        document.querySelector('.auth-tabs .tab:nth-child(1)').classList.add('active');
        document.getElementById('form-login').classList.remove('d-none');
    } else if (type === 'signup') {
        document.querySelector('.auth-tabs .tab:nth-child(2)').classList.add('active');
        document.getElementById('form-signup').classList.remove('d-none');
    } else if (type === 'forgot') {
        document.getElementById('form-forgot').classList.remove('d-none');
    } else if (type === 'reset') {
        document.getElementById('form-reset').classList.remove('d-none');
    }
};

window.handleSignup = function() {
    const name = document.getElementById('signup-name').value.trim();
    const email = document.getElementById('signup-email').value.trim();
    const pass = document.getElementById('signup-pass').value;

    if (!name || !email || !pass) return showToast("Please fill all fields.");
    
    // Check if user already exists
    if (state.users.find(u => u.email === email)) {
        alert("This Email ID is already registered. Please log in.");
        return;
    }

    const newUser = { name, email, pass, bookings: [] };
    state.users.push(newUser);
    state.user = newUser; // Auto login
    saveUsers(); // Persist data

    // Clear fields
    document.getElementById('signup-name').value = '';
    document.getElementById('signup-email').value = '';
    document.getElementById('signup-pass').value = '';

    window.navigateTo('search');
};

window.handleLogin = function() {
    const email = document.getElementById('login-email').value.trim();
    const pass = document.getElementById('login-pass').value;

    if (!email || !pass) return showToast("Please fill all fields.");

    const user = state.users.find(u => u.email === email);
    if (!user || user.pass !== pass) {
        return showToast("Invalid Email ID or Password!");
    }

    state.user = user;
    
    // Clear fields
    document.getElementById('login-email').value = '';
    document.getElementById('login-pass').value = '';

    window.navigateTo('search');
};

window.handleForgot = function() {
    const email = document.getElementById('forgot-email').value.trim();
    if (!email) return showToast("Please enter your email.");
    
    const user = state.users.find(u => u.email === email);
    if (!user) {
        return showToast("No account found with this email ID.");
    }

    // Simulate sending reset code
    state.resetEmail = email;
    state.resetCode = Math.floor(1000 + Math.random() * 9000).toString();
    showToast(`Reset code sent to ${email} (Code: ${state.resetCode})`, 'success');

    document.getElementById('forgot-email').value = '';
    window.switchAuthTab('reset');
};

window.handleReset = function() {
    const code = document.getElementById('reset-code').value.trim();
    const newPass = document.getElementById('reset-pass').value;

    if (!code || !newPass) return showToast("Please fill all fields.");

    if (code !== state.resetCode) {
        return showToast("Invalid reset code.");
    }

    const user = state.users.find(u => u.email === state.resetEmail);
    if (user) {
        user.pass = newPass;
        saveUsers(); // Persist data
        showToast("Password reset successfully. Please login.", 'success');
    }

    // Clean up
    state.resetEmail = null;
    state.resetCode = null;
    document.getElementById('reset-code').value = '';
    document.getElementById('reset-pass').value = '';
    
    window.switchAuthTab('login');
};

// --- Search Logic ---
window.handleSearch = function() {
    const src = document.getElementById('search-source').value.trim();
    const dst = document.getElementById('search-destination').value.trim();
    const date = document.getElementById('search-date').value;

    if (!src || !dst || !date) return showToast('Please fill all search fields');

    state.search = { source: src, destination: dst, date: date };
    
    // Update headers
    document.getElementById('buses-route-title').innerText = `${src} to ${dst}`;
    document.getElementById('buses-date-title').innerText = new Date(date).toDateString();

    // Mock Backend: Generate Buses
    generateMockBuses(src, dst, date);
    renderBusList();

    window.navigateTo('buses');
};

function generateMockBuses(src, dst, date) {
    const cacheKey = `${src.toLowerCase()}-${dst.toLowerCase()}-${date}`;
    if (state.routesCache[cacheKey]) {
        state.buses = state.routesCache[cacheKey];
        return;
    }

    const companies = ['Nexus Premium', 'Skyline Express', 'Voyage Intercity', 'RapidLine', 'Kaveri Travels', 'SRS Travels', 'VRL Travels', 'Orange Tours', 'National Travels', 'IntrCity SmartBus', 'Zingbus'];
    const times = [
        { d: '08:00 AM', a: '02:30 PM', dur: '6h 30m' },
        { d: '10:15 AM', a: '04:00 PM', dur: '5h 45m' },
        { d: '01:30 PM', a: '08:45 PM', dur: '7h 15m' },
        { d: '09:00 PM', a: '06:00 AM', dur: '9h 00m' },
        { d: '06:00 AM', a: '01:00 PM', dur: '7h 00m' },
        { d: '11:00 AM', a: '04:30 PM', dur: '5h 30m' },
        { d: '10:00 PM', a: '07:00 AM', dur: '9h 00m' },
        { d: '11:30 PM', a: '08:30 AM', dur: '9h 00m' },
        { d: '05:00 PM', a: '11:45 PM', dur: '6h 45m' },
        { d: '07:30 AM', a: '01:15 PM', dur: '5h 45m' },
        { d: '08:30 PM', a: '05:30 AM', dur: '9h 00m' },
        { d: '04:00 PM', a: '10:30 PM', dur: '6h 30m' },
        { d: '09:30 AM', a: '03:15 PM', dur: '5h 45m' },
        { d: '10:30 PM', a: '06:30 AM', dur: '8h 00m' }
    ];

    state.buses = times.map((t, index) => {
        const busTypes = ['AC Sleeper (2+1)', 'Non-AC Sleeper (2+1)', 'AC Seater (2+2)', 'Volvo Multi-Axle Semi-Sleeper (2+2)', 'AC Sleeper (1+1)', 'Scania AC Multi Axle Sleeper (2+1)'];
        return {
            id: 'bus-' + cacheKey + '-' + index,
            company: companies[index % companies.length],
            type: busTypes[index % busTypes.length],
            departure: t.d,
            arrival: t.a,
            duration: t.dur,
            price: Math.floor(Math.random() * 800) + 700 // INR pricing between 700 and 1500
        };
    });

    state.routesCache[cacheKey] = state.buses;
}

function renderBusList() {
    const container = document.getElementById('bus-list-container');
    container.innerHTML = '';

    if (state.buses.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">No buses found for this route.</p>';
        return;
    }

    state.buses.forEach(bus => {
        const card = document.createElement('div');
        card.className = 'bus-card';
        card.innerHTML = `
            <div>
                <div class="bus-company">${bus.company}</div>
                <div class="bus-type">${bus.type}</div>
            </div>
            <div class="bus-times">
                <div class="time-col">
                    <strong>${bus.departure}</strong>
                    <span>${state.search.source}</span>
                </div>
                <div class="duration">${bus.duration}</div>
                <div class="time-col">
                    <strong>${bus.arrival}</strong>
                    <span>${state.search.destination}</span>
                </div>
            </div>
            <div class="bus-price">₹${bus.price}</div>
            <button class="btn-primary" onclick="selectBus('${bus.id}')">Select Seats</button>
        `;
        container.appendChild(card);
    });
}

window.selectBus = function(id) {
    state.selectedBus = state.buses.find(b => b.id === id);
    state.selectedSeats = []; // Reset on new bus

    if (!state.selectedBus.seatsGenerated) {
        let cols = [1, 2, 'aisle', 3, 4];
        if (state.selectedBus.type.includes('2+1')) {
            cols = [1, 2, 'aisle', 3];
        } else if (state.selectedBus.type.includes('1+1')) {
            cols = [1, 'aisle', 2];
        }
        
        const rows = ['A','B','C','D','E','F','G','H','I','J'];
        let seatsData = {};
    
        rows.forEach(row => {
            cols.forEach(col => {
                if (col === 'aisle') return;
                const sid = `${row}${col}`;
                const isHandicap = (row === 'A');
                const isBooked = !isHandicap && Math.random() < 0.25;
                let bookedGender = null;
                if (isBooked) bookedGender = Math.random() < 0.5 ? 'M' : 'F';
                
                seatsData[sid] = { id: sid, row, col, isHandicap, isBooked, bookedGender, restrictedTo: null };
            });
        });
        
        state.selectedBus.seatsCols = cols;
        state.selectedBus.seatsRows = rows;
        state.selectedBus.seatsData = seatsData;
        state.selectedBus.seatsGenerated = true;
    }

    window.navigateTo('seats');
};

// --- Seats Logic ---
function renderSeats() {
    document.getElementById('summary-bus-name').innerText = state.selectedBus.company;
    document.getElementById('summary-route').innerText = `${state.search.source} -> ${state.search.destination}`;
    
    const container = document.getElementById('seats-grid');
    container.innerHTML = '';

    const isSleeper = state.selectedBus.type.toLowerCase().includes('sleeper');
    const cols = state.selectedBus.seatsCols;
    const rows = state.selectedBus.seatsRows;
    const seatsData = state.selectedBus.seatsData;
    
    container.style.gridTemplateColumns = `repeat(${cols.length}, 40px)`;

    for (let id in seatsData) {
        seatsData[id].restrictedTo = null;
    }

    rows.forEach(row => {
        const applyRestriction = (c1, c2) => {
            const s1 = seatsData[`${row}${c1}`];
            const s2 = seatsData[`${row}${c2}`];
            if (s1 && s2) {
                if (s1.isBooked && !s2.isBooked) s2.restrictedTo = s1.bookedGender;
                if (s2.isBooked && !s1.isBooked) s1.restrictedTo = s2.bookedGender;
            }
        };
        if(cols.includes(1) && cols.includes(2)) applyRestriction(1, 2);
        if(cols.includes(3) && cols.includes(4)) applyRestriction(3, 4);
    });

    state.currentSeatsData = seatsData;

    rows.forEach(row => {
        cols.forEach(col => {
            if (col === 'aisle') {
                const space = document.createElement('div');
                space.className = `seat-space ${isSleeper ? 'sleeper' : ''}`;
                container.appendChild(space);
                return;
            }

            const data = seatsData[`${row}${col}`];
            const seatElement = document.createElement('div');
            
            let classes = ['seat'];
            if (isSleeper) classes.push('sleeper');
            
            if (data.isBooked) {
                classes.push('booked');
                if (data.bookedGender === 'M') classes.push('booked-m');
                if (data.bookedGender === 'F') classes.push('booked-f');
            } else if (data.restrictedTo === 'M') {
                classes.push('restricted-m');
            } else if (data.restrictedTo === 'F') {
                classes.push('restricted-f');
            } else {
                classes.push('available');
            }

            if (data.isHandicap) {
                classes.push('handicap');
            }
            
            if (state.selectedSeats.includes(data.id)) {
                classes.push('selected');
            }

            seatElement.className = classes.join(' ');
            seatElement.innerText = data.id;
            seatElement.dataset.id = data.id;

            if (!data.isBooked) {
                seatElement.onclick = () => toggleSeatSelection(data.id, seatElement);
            }

            container.appendChild(seatElement);
        });
    });
}

function toggleSeatSelection(id, el) {
    const idx = state.selectedSeats.indexOf(id);
    if (idx > -1) {
        // Deselect
        state.selectedSeats.splice(idx, 1);
        el.classList.remove('selected');
    } else {
        // Max 6 seats
        if (state.selectedSeats.length >= 6) return showToast('Maximum 6 seats allowed per booking.');
        state.selectedSeats.push(id);
        el.classList.add('selected');
    }
    updateSummary();
}

function updateSummary() {
    const seatsDisplay = document.getElementById('summary-seats-list');
    const totalDisplay = document.getElementById('summary-total-price');
    const btnProceed = document.getElementById('btn-proceed-passenger');

    if (state.selectedSeats.length === 0) {
        seatsDisplay.innerText = 'None';
        totalDisplay.innerText = '0';
        btnProceed.disabled = true;
    } else {
        seatsDisplay.innerText = state.selectedSeats.join(', ');
        totalDisplay.innerText = (state.selectedSeats.length * state.selectedBus.price);
        btnProceed.disabled = false;
    }
}

// --- Checkout & Booking ---
window.confirmBooking = function() {
    const btn = document.querySelector('.flash-btn');
    
    // Validation
    const phone = document.getElementById('pass-phone').value.trim();
    const email = document.getElementById('pass-email').value.trim();

    if (!phone || !email) return showToast("Fill all contact details.");

    const passengers = [];
    let isValid = true;
    let restrictionError = null;

    state.selectedSeats.forEach(seatId => {
        const nameInput = document.getElementById(`pass-name-${seatId}`);
        const genderInput = document.getElementById(`pass-gender-${seatId}`);
        
        if (!nameInput || !genderInput || !nameInput.value.trim() || !genderInput.value) {
            isValid = false;
        } else {
            const gender = genderInput.value;
            // Validate seat restrictions
            const seatInfo = state.currentSeatsData[seatId];
            if (seatInfo.restrictedTo && seatInfo.restrictedTo !== gender) {
                restrictionError = `Cannot book Seat ${seatId}. It is reserved for ${seatInfo.restrictedTo === 'F' ? 'female' : 'male'} passengers only.`;
            }
            passengers.push({ seatId, name: nameInput.value.trim(), gender });
        }
    });

    if (!isValid) return showToast("Fill all passenger details including gender.");
    if (restrictionError) return showToast(restrictionError);

    const primaryPassenger = passengers[0];
    state.passenger = { name: primaryPassenger.name, phone, email, gender: primaryPassenger.gender, allPassengers: passengers };

    // Simulate Payment Processing
    btn.innerHTML = '<ion-icon name="sync-outline" class="spin"></ion-icon> Processing...';
    btn.disabled = true;

    setTimeout(() => {
        btn.classList.add('flash-success');
        btn.innerHTML = '<ion-icon name="checkmark-outline"></ion-icon> Payment Successful!';

        window.addNotification(`Booking Confirmed! Details sent to ${state.passenger.email}.`, 'success');

        // Reset ticket header for fresh booking
        document.querySelector('.ticket-header h2').innerText = 'Booking Confirmed!';
        document.querySelector('.ticket-header p').innerText = 'Your e-ticket has been sent to your Gmail.';
        document.querySelector('.success-icon').classList.remove('d-none');

        // Block the booked seats visually for future visits
        for (let pass of passengers) {
            const id = pass.seatId;
            if (state.selectedBus && state.selectedBus.seatsData[id]) {
                state.selectedBus.seatsData[id].isBooked = true;
                state.selectedBus.seatsData[id].bookedGender = pass.gender;
            }
        }
        
        let amount = (state.selectedSeats.length * state.selectedBus.price);
        let pnr = 'NEX' + Math.floor(Math.random() * 90000000 + 10000000); // 8 digit random
        
        const allNames = passengers.map(p => p.name).join(', ');

        state.currentTicket = { pnr, amount, passNames: allNames };

        if (state.user) {
            if (!state.user.bookings) state.user.bookings = [];
            state.user.bookings.unshift({
                pnr: pnr,
                date: new Date(state.search.date).toDateString(),
                src: state.search.source.substring(0, 3).toUpperCase(),
                dst: state.search.destination.substring(0, 3).toUpperCase(),
                busName: state.selectedBus.company,
                seats: state.selectedSeats.join(', '),
                amount: amount,
                passName: allNames,
                passPhone: state.passenger.phone
            });
            
            // Sync current user object inside the state.users list and save
            const uIndex = state.users.findIndex(u => u.email === state.user.email);
            if(uIndex !== -1) {
                state.users[uIndex] = state.user;
                saveUsers();
            }
        }
        
        setTimeout(() => {
            generateFinalTicket();
            
            // Reset selected seats so they are not carried over to the next search/booking
            state.selectedSeats = [];
            
            // Cleanup UI for next time
            btn.classList.remove('flash-success');
            btn.innerHTML = `Proceed & Book Ticket`;
            btn.disabled = false;
            
            window.navigateTo('ticket');
        }, 1000);
    }, 1500);
};

function generateFinalTicket() {
    // Generate PNR
    const pnr = state.currentTicket ? state.currentTicket.pnr : 'NEX' + Math.floor(Math.random() * 90000000 + 10000000); // 8 digit random

    document.getElementById('ticket-pnr').innerText = pnr;
    document.getElementById('ticket-date').innerText = new Date(state.search.date).toDateString();
    document.getElementById('ticket-src').innerText = state.search.source.substring(0, 3).toUpperCase();
    document.getElementById('ticket-dst').innerText = state.search.destination.substring(0, 3).toUpperCase();
    
    document.getElementById('ticket-name').innerText = state.currentTicket && state.currentTicket.passNames ? state.currentTicket.passNames : state.passenger.name;
    document.getElementById('ticket-phone').innerText = state.passenger.phone;
    
    document.getElementById('ticket-bus-name').innerText = state.selectedBus.company;
    document.getElementById('ticket-seats').innerText = state.selectedSeats.join(', ');
    
    const amount = state.currentTicket ? state.currentTicket.amount : (state.selectedSeats.length * state.selectedBus.price);
    document.getElementById('ticket-amount').innerText = `₹${amount}`;
}

function renderDashboard() {
    const container = document.getElementById('dashboard-bookings');
    container.innerHTML = '';

    if (!state.user || !state.user.bookings || state.user.bookings.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">No tickets booked yet.</p>';
        return;
    }

    state.user.bookings.forEach(booking => {
        const card = document.createElement('div');
        card.className = 'bus-card';
        card.innerHTML = `
            <div>
                <div class="bus-company">${booking.busName}</div>
                <div class="bus-type">PNR: ${booking.pnr} <span class="mx-2">•</span> Seats: <span class="color-accent">${booking.seats}</span></div>
            </div>
            <div class="bus-times">
                <div class="time-col">
                    <strong>${booking.src}</strong>
                </div>
                <div class="duration">${booking.date}</div>
                <div class="time-col">
                    <strong>${booking.dst}</strong>
                </div>
            </div>
            <div class="bus-price">₹${booking.amount}</div>
            <button class="btn-primary" onclick="window.viewTicket('${booking.pnr}')">Show Ticket</button>
        `;
        container.appendChild(card);
    });
}

window.viewTicket = function(pnr) {
    const booking = state.user.bookings.find(b => b.pnr === pnr);
    if (!booking) return;

    document.getElementById('ticket-pnr').innerText = booking.pnr;
    document.getElementById('ticket-date').innerText = booking.date;
    document.getElementById('ticket-src').innerText = booking.src;
    document.getElementById('ticket-dst').innerText = booking.dst;
    
    document.getElementById('ticket-name').innerText = booking.passName || state.user.name;
    document.getElementById('ticket-phone').innerText = booking.passPhone || 'N/A';
    
    document.getElementById('ticket-bus-name').innerText = booking.busName;
    document.getElementById('ticket-seats').innerText = booking.seats;
    document.getElementById('ticket-amount').innerText = `₹${booking.amount}`;

    document.querySelector('.ticket-header h2').innerText = 'Your E-Ticket';
    document.querySelector('.ticket-header p').innerText = 'Present this to the conductor during boarding.';
    document.querySelector('.success-icon').classList.add('d-none');

    window.navigateTo('ticket');
};

// Spin animation for button
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin { 100% { transform: rotate(360deg); } }
.spin { animation: spin 1s linear infinite; }
`;
document.head.appendChild(style);
