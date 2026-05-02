// Core state for seats view
const state = {
    selectedSeats: [],
    currentSeatsData: {}
};

// --- Notifications ---
window.toggleNotifications = function() {
    const panel = document.getElementById('notifications-panel');
    if (panel.classList.contains('d-none')) {
        panel.classList.remove('d-none');
    } else {
        panel.classList.add('d-none');
    }
};

window.showToast = function(message, type = 'error') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const iconName = type === 'error' ? 'warning-outline' : 'checkmark-circle-outline';
    toast.innerHTML = `<div class="toast-content"><ion-icon name="${iconName}"></ion-icon> <span>${message}</span></div><div class="toast-progress"></div>`;
    
    container.appendChild(toast);
    
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
};

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

// --- Seats Logic (used in seats.html) ---
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('seats-grid') && window.routeData) {
        renderSeats();
    }
});

function renderSeats() {
    const container = document.getElementById('seats-grid');
    if (!container) return;
    container.innerHTML = '';

    const isSleeper = window.routeData.type.toLowerCase().includes('sleeper');
    let cols = [1, 2, 'aisle', 3, 4];
    if (window.routeData.type.includes('2+1')) {
        cols = [1, 2, 'aisle', 3];
    } else if (window.routeData.type.includes('1+1')) {
        cols = [1, 'aisle', 2];
    }
    
    const rows = ['A','B','C','D','E','F','G','H','I','J'];
    let seatsData = {};
    
    // Generate map
    rows.forEach(row => {
        cols.forEach(col => {
            if (col === 'aisle') return;
            const sid = `${row}${col}`;
            const isHandicap = (row === 'A');
            const bookedGender = window.bookedSeats[sid] || null;
            const isBooked = !!bookedGender;
            
            seatsData[sid] = { id: sid, row, col, isHandicap, isBooked, bookedGender, restrictedTo: null };
        });
    });

    // Handle M/F Restrictions based on booked neighbor
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
    container.style.gridTemplateColumns = `repeat(${cols.length}, 40px)`;

    // Render HTML
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

            if (data.isHandicap) classes.push('handicap');
            if (state.selectedSeats.includes(data.id)) classes.push('selected');

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
        state.selectedSeats.splice(idx, 1);
        el.classList.remove('selected');
    } else {
        if (state.selectedSeats.length >= 6) return showToast('Maximum 6 seats allowed.');
        state.selectedSeats.push(id);
        el.classList.add('selected');
    }
    updateSummary();
}

function updateSummary() {
    const seatsDisplay = document.getElementById('summary-seats-list');
    const totalDisplay = document.getElementById('summary-total-price');
    const btnProceed = document.getElementById('btn-proceed-passenger');

    if (!seatsDisplay || !totalDisplay || !btnProceed) return;

    if (state.selectedSeats.length === 0) {
        seatsDisplay.innerText = 'None';
        totalDisplay.innerText = '0';
        btnProceed.disabled = true;
    } else {
        seatsDisplay.innerText = state.selectedSeats.join(', ');
        totalDisplay.innerText = (state.selectedSeats.length * window.routeData.price);
        btnProceed.disabled = false;
    }
}

// --- Checkout Transitions ---
window.proceedToCheckout = function() {
    document.getElementById('view-seats').classList.remove('active');
    document.getElementById('view-checkout').classList.add('active');
    
    document.getElementById('checkout-total').innerText = (state.selectedSeats.length * window.routeData.price);
    renderPassengerForms();
};

window.backToSeats = function() {
    document.getElementById('view-checkout').classList.remove('active');
    document.getElementById('view-seats').classList.add('active');
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

// --- Razorpay Payment Integration ---
window.payWithRazorpay = async function() {
    const phone = document.getElementById('pass-phone').value.trim();
    const email = document.getElementById('pass-email').value.trim();
    const pickupPoint = document.getElementById('pickup-point') ? document.getElementById('pickup-point').value : null;
    const dropPoint = document.getElementById('drop-point') ? document.getElementById('drop-point').value : null;
    
    if (!phone || !email) return showToast("Fill all contact details.");
    if (!pickupPoint || !dropPoint) return showToast("Select boarding and dropping points.");

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
            const seatInfo = state.currentSeatsData[seatId];
            if (seatInfo.restrictedTo && seatInfo.restrictedTo !== gender) {
                restrictionError = `Cannot book Seat ${seatId}. It is reserved for ${seatInfo.restrictedTo === 'F' ? 'female' : 'male'} passengers only.`;
            }
            passengers.push({ seatId, name: nameInput.value.trim(), gender });
        }
    });

    if (!isValid) return showToast("Fill all passenger details including gender.");
    if (restrictionError) return showToast(restrictionError);

    const btn = document.getElementById('pay-btn');
    btn.innerHTML = '<ion-icon name="sync-outline" class="spin"></ion-icon> Processing...';
    btn.disabled = true;

    try {
        // Step 1: Create Order on Backend
        const res = await fetch('/checkout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                route_id: window.routeData.id,
                seats: state.selectedSeats,
                passengers: passengers,
                contact_phone: phone,
                contact_email: email,
                pickup_point: pickupPoint,
                drop_point: dropPoint
            })
        });
        
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to create order');

        // Step 2: Open Razorpay UI
        const options = {
            "key": data.key,
            "amount": data.amount,
            "currency": "INR",
            "name": "Nexus Transit",
            "description": "Bus Ticket Booking",
            "order_id": data.order_id,
            "method": {
                "upi": true,
                "netbanking": true,
                "card": true,
                "wallet": true
            },
            "handler": async function (response) {
                // Step 3: Verify Signature on Backend
                const verifyRes = await fetch('/payment/verify', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        razorpay_payment_id: response.razorpay_payment_id,
                        razorpay_order_id: response.razorpay_order_id,
                        razorpay_signature: response.razorpay_signature
                    })
                });
                
                const verifyData = await verifyRes.json();
                if (verifyData.success) {
                    window.location.href = `/confirmation/${verifyData.pnr}`;
                } else {
                    showToast('Payment verification failed.');
                    btn.innerHTML = 'Pay & Book Ticket';
                    btn.disabled = false;
                }
            },
            "prefill": {
                "name": passengers[0].name,
                "email": email,
                "contact": phone
            },
            "theme": { "color": "#0ea5e9" }
        };
        
        const rzp = new Razorpay(options);
        rzp.on('payment.failed', function (response){
            showToast('Payment Failed. Reason: ' + response.error.description);
            btn.innerHTML = 'Pay & Book Ticket';
            btn.disabled = false;
        });
        rzp.open();
        
    } catch (err) {
        showToast(err.message);
        btn.innerHTML = 'Pay & Book Ticket';
        btn.disabled = false;
    }
};

// Spin animation for button
const style = document.createElement('style');
style.innerHTML = `
@keyframes spin { 100% { transform: rotate(360deg); } }
.spin { animation: spin 1s linear infinite; }
`;
document.head.appendChild(style);
