import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv
from models import db, User, Bus, Route, Booking, Passenger
import os
import razorpay
from razorpay.errors import SignatureVerificationError


load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise Exception("Razorpay keys are missing in .env")

razorpay_client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_secret_key_change_me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def generate_pnr():
    return 'NEX' + ''.join(random.choices(string.digits, k=8))

# ==================== ROUTES ====================

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Registration successful!', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        source = request.form.get('source', '').strip()
        destination = request.form.get('destination', '').strip()
        date = request.form.get('date')
        
        # Normalize Bangalore to Bengaluru
        if source.lower() == 'bangalore':
            source = 'Bengaluru'
        elif source:
            source = source.title()
            
        if destination.lower() == 'bangalore':
            destination = 'Bengaluru'
        elif destination:
            destination = destination.title()
            
        # Save search to session
        session['search'] = {'source': source, 'destination': destination, 'date': date}
        
        routes = Route.query.filter_by(source=source, destination=destination, date=date).all()
        return render_template('buses.html', routes=routes, search=session['search'])
    
    # If GET and session exists, show results
    if 'search' in session:
        routes = Route.query.filter_by(
            source=session['search']['source'], 
            destination=session['search']['destination'], 
            date=session['search']['date']
        ).all()
        return render_template('buses.html', routes=routes, search=session['search'])
        
    return redirect(url_for('index'))


@app.route('/bus/<int:route_id>/seats')
@login_required
def seats(route_id):
    route = Route.query.get_or_404(route_id)
    # Get already booked seats for this route
    bookings = Booking.query.filter_by(route_id=route.id, payment_status='Paid').all()
    booked_seats = {}
    for b in bookings:
        for p in b.passengers:
            booked_seats[p.seat_number] = p.gender
            
    return render_template('seats.html', route=route, booked_seats=booked_seats)

@app.route('/checkout', methods=['POST'])
def checkout():
    if request.method == 'POST':
        # Get data from frontend (AJAX)
        data = request.json
        route_id = data.get('route_id')
        seats = data.get('seats') # list of seat IDs
        passengers = data.get('passengers') # list of dicts: {seatId, name, gender}
        contact_phone = data.get('contact_phone')
        contact_email = data.get('contact_email')
        
        route = Route.query.get(route_id)
        if not route:
            return jsonify({'error': 'Route not found'}), 404
            
        amount = len(seats) * route.bus.price
        amount_in_paise = int(amount * 100)
        
        # Create Razorpay order
        order_data = {
            'amount': amount_in_paise,
            'currency': 'INR',
            'receipt': 'receipt_' + ''.join(random.choices(string.digits, k=6)),
            'payment_capture': 1
        }
        
        try:
            razorpay_order = razorpay_client.order.create(data=order_data)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
            
        # Create pending booking
        booking = Booking(
            pnr=generate_pnr(),
            user_id=current_user.id if current_user.is_authenticated else None,
            route_id=route.id,
            contact_phone=contact_phone,
            contact_email=contact_email,
            total_amount=amount,
            razorpay_order_id=razorpay_order['id'],
            payment_status='Pending'
        )
        db.session.add(booking)
        db.session.flush() # get booking.id
        
        for p in passengers:
            passenger = Passenger(
                booking_id=booking.id,
                name=p['name'],
                gender=p['gender'],
                seat_number=p['seatId']
            )
            db.session.add(passenger)
            
        db.session.commit()
        
        return jsonify({
            'order_id': razorpay_order['id'],
            'amount': amount_in_paise,
            'booking_id': booking.id,
            'pnr': booking.pnr,
            'key': RAZORPAY_KEY_ID
        })

@app.route('/payment/verify', methods=['POST'])
def payment_verify():
    data = request.json
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    
    booking = Booking.query.filter_by(razorpay_order_id=razorpay_order_id).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
        
    try:
        # Verify signature
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        
        booking.payment_status = 'Paid'
        booking.razorpay_payment_id = razorpay_payment_id
        db.session.commit()
        
        return jsonify({'success': True, 'pnr': booking.pnr})
    except SignatureVerificationError:
        booking.payment_status = 'Failed'
        db.session.commit()
        return jsonify({'error': 'Signature verification failed'}), 400
    except Exception as e:
        booking.payment_status = 'Failed'
        db.session.commit()
        return jsonify({'error': f'Payment verification error: {str(e)}'}), 400

@app.route('/confirmation/<pnr>')
def confirmation(pnr):
    booking = Booking.query.filter_by(pnr=pnr).first_or_404()
    if booking.payment_status != 'Paid':
        flash('Payment is pending or failed for this ticket.', 'warning')
    return render_template('confirmation.html', booking=booking)

@app.route('/dashboard')
@login_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.created_at.desc()).all()
    return render_template('dashboard.html', bookings=bookings)

# Helper to populate DB
@app.route('/seed')
def seed_db():
    db.drop_all()
    db.create_all()
    
    # Create a larger set of buses / travel companies
    travel_companies = [
        'Anand Travels', 'Apex Superfast', 'Arjun Express', 'Arcadia Tours', 'Ashoka Sleeper',
        'Bharat Premium', 'Brindavan Coaches', 'Celestial Travels', 'City Link', 'Cloud Nine Bus',
        'Crown Coach', 'Dakshin Express', 'Delhi Madurai Lines', 'DreamLine Travels',
        'East West Express', 'Elden Bus Services', 'Empire Travels', 'EuroCoach', 'Galaxy Travels',
        'Gemini Bus Lines', 'Global Horizon', 'Grand Oak Travels', 'Imperial Coach', 'Infinity Travels',
        'Jai Hind Express', 'Jayalakshmi Travels', 'Jeevan Express', 'Kalyani Travels', 'Kaveri Golden',
        'Kingfisher Coaches', 'Lotus Travels', 'Maharaja Express', 'Majestic Bus Lines', 'MetroLink Travels',
        'New Era Travels', 'Nexus Express', 'Nithyas Travel', 'Noble Coach', 'Oceanic Travels',
        'Pacific Express', 'Phoenix Travels', 'Pioneer Coach', 'Prestige Travels', 'PrimeLine Express',
        'Rajdoot Travels', 'Rivera Coaches', 'Royal Star', 'Sahana Travels', 'Sapphire Express',
        'Saraswathi Travels',
        'A1 Travels', 'Kallada Travels', 'SRS Travels', 'VRL Travels', 'Orange Tours',
        'Jabbar Travels', 'KPN Travels', 'Parveen Travels', 'Rathimeena Travels', 'Sharma Transports',
        'Neeta Tours', 'Konduskar Travels', 'Paulo Travels', 'Sangita Travels', 'Saini Travels',
        'Amarnath Travels', 'National Travels', 'IntrCity SmartBus', 'Zingbus', 'NueGo',
        'YoloBus', 'GreenLine Travels', 'Sugama Tourist', 'Bharathi Travels', 'Vivekananda Travels',
        'SPS Travels', 'JBT Travels', 'Muthu Travels', 'SRM Transports', 'Tranz King Travels',
        'YBM Travels', 'Kallada G4', 'ABT Xpress', 'Universal Travels', 'Praveen Travels',
        'Kalaivani Travels', 'Tippu Sultan Travels', 'Khushi Tourist', 'Humsafar Travels', 'Shree Travels',
        'Mahasagar Travels', 'Eagle Travels', 'Shatabdi Travels', 'Royal Travels', 'Classic Travels',
        'Vignesh Travels', 'Murugan Travels', 'Kannan Travels', 'Selvam Travels', 'Siva Travels'
    ]

    bus_types = ['AC Sleeper (2+1)', 'AC Seater (2+2)', 'Non-AC Sleeper (2+1)', 'Volvo Multi-Axle (2+2)', 'Semi-AC Seater (2+2)']
    buses = []
    for name in travel_companies:
        for _ in range(5):
            buses.append(Bus(
                company=name,
                type=random.choice(bus_types),
                price=random.randint(700, 1800)
            ))

    db.session.add_all(buses)
    db.session.commit()

    import datetime
    date_options = [
        (datetime.date.today() + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(1, 16)
    ]

    # Districts organized by state
    states = {
        'Tamil Nadu': [
            'Ariyalur', 'Chengalpattu', 'Chennai', 'Coimbatore', 'Cuddalore', 'Dharmapuri',
            'Dindigul', 'Erode', 'Kallakurichi', 'Kancheepuram', 'Kanyakumari', 'Karur', 'Krishnagiri',
            'Madurai', 'Mayiladuthurai', 'Nagapattinam', 'Namakkal', 'Nilgiris', 'Perambalur',
            'Pudukkottai', 'Ramanathapuram', 'Ranipet', 'Salem', 'Sivaganga', 'Tenkasi',
            'Thanjavur', 'Theni', 'Thoothukudi', 'Tiruchirappalli', 'Tirunelveli', 'Tirupathur',
            'Tiruppur', 'Tiruvallur', 'Tiruvannamalai', 'Tiruvarur', 'Vellore', 'Viluppuram',
            'Virudhunagar'
        ],
        'Karnataka': ['Bengaluru'],
        'Telangana': ['Hyderabad']
    }

    times = [
        ('06:00 AM', '11:00 AM', '5h 00m'), ('08:30 AM', '02:00 PM', '5h 30m'),
        ('10:00 AM', '04:15 PM', '6h 15m'), ('02:00 PM', '08:30 PM', '6h 30m'),
        ('05:30 PM', '11:45 PM', '6h 15m'), ('09:00 PM', '05:00 AM', '8h 00m'),
        ('10:30 PM', '06:00 AM', '7h 30m'), ('11:45 PM', '07:30 AM', '7h 45m')
    ]

    routes = []

    # Generate route coverage for every distinct Tamil Nadu district pair on several dates
    tn_districts = states['Tamil Nadu']
    for src in tn_districts:
        for dst in tn_districts:
            if src == dst:
                continue
            for date_str in date_options[:2]:
                ops = random.randint(5, 7)
                sampled_buses = random.sample(buses, ops)
                for bus in sampled_buses:
                    dep, arr, dur = random.choice(times)
                    routes.append(Route(
                        source=src, destination=dst, date=date_str,
                        departure_time=dep, arrival_time=arr, duration=dur, bus_id=bus.id
                    ))

    # Add Bangalore and Hyderabad routes against all Tamil Nadu districts
    for city in ['Bengaluru', 'Hyderabad']:
        for district in tn_districts:
            for date_str in date_options[:2]:
                # city to district
                ops1 = random.randint(5, 7)
                sampled_buses1 = random.sample(buses, ops1)
                for bus in sampled_buses1:
                    dep, arr, dur = random.choice(times)
                    routes.append(Route(
                        source=city, destination=district, date=date_str,
                        departure_time=dep, arrival_time=arr, duration=dur, bus_id=bus.id
                    ))
                # district to city
                ops2 = random.randint(5, 7)
                sampled_buses2 = random.sample(buses, ops2)
                for bus in sampled_buses2:
                    dep, arr, dur = random.choice(times)
                    routes.append(Route(
                        source=district, destination=city, date=date_str,
                        departure_time=dep, arrival_time=arr, duration=dur, bus_id=bus.id
                    ))

    # Add additional random routes
    for _ in range(300):
        state_name, districts = random.choice(list(states.items()))
        if len(districts) >= 2:
            src, dst = random.sample(districts, 2)
        else:
            src = districts[0]
            other_states = [items for items in states.items() if items[0] != state_name and items[1]]
            other_state_name, other_districts = random.choice(other_states)
            dst = random.choice(other_districts)

        date_str = random.choice(date_options)
        dep, arr, dur = random.choice(times)
        bus = random.choice(buses)
        routes.append(Route(
            source=src, destination=dst, date=date_str,
            departure_time=dep, arrival_time=arr, duration=dur, bus_id=bus.id
        ))

    # Batch insert to handle larger datasets
    batch_size = 5000
    for i in range(0, len(routes), batch_size):
        db.session.add_all(routes[i:i+batch_size])
        db.session.commit()

    return f"Database seeded! Generated {len(routes)} sample routes for Tamil Nadu, Bengaluru, and Hyderabad on multiple dates."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8000, host='127.0.0.1')
