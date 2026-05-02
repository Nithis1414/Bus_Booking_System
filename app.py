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
import datetime


POPULAR_POINTS = {
    'Ariyalur': [('Bus Stand', 0), ('Railway Station', 15), ('Sendurai Road', 30)],
    'Chengalpattu': [('New Bus Stand', 0), ('Railway Station', 10), ('GST Road', 20)],
    'Chennai': [('Koyambedu (CMBT)', 0), ('Egmore', 20), ('Guindy', 40), ('Tambaram', 75), ('Perungalathur', 90)],
    'Coimbatore': [('Gandhipuram', 0), ('Omni Bus Stand', 15), ('Hope College', 30), ('Singanallur', 45), ('Ukkadam', 60)],
    'Cuddalore': [('Bus Stand', 0), ('OT', 15), ('Manjakuppam', 25)],
    'Dharmapuri': [('Bus Stand', 0), ('Four Roads', 15), ('Collectorate', 25)],
    'Dindigul': [('Bus Stand', 0), ('Palani Road', 15), ('Railway Station', 25)],
    'Erode': [('Central Bus Stand', 0), ('Sathyamangalam Road', 20), ('Railway Station', 35)],
    'Kallakurichi': [('Bus Stand', 0), ('Kachirapalayam Road', 20)],
    'Kancheepuram': [('Bus Stand', 0), ('Collectorate', 15), ('Temple View', 30)],
    'Kanyakumari': [('Nagercoil Bus Stand', 0), ('Kanyakumari Stand', 45), ('Vivekananda Rock View', 60)],
    'Karur': [('Bus Stand', 0), ('Gandhigramam', 15), ('Pugalur Road', 30)],
    'Krishnagiri': [('Bus Stand', 0), ('Rayakottai Road', 15), ('Roundana', 25)],
    'Madurai': [('Mattuthavani', 0), ('Arapalayam', 20), ('Periyar', 35), ('Kalavasal', 50)],
    'Mayiladuthurai': [('Bus Stand', 0), ('Koranad', 15), ('Railway Station', 25)],
    'Nagapattinam': [('Bus Stand', 0), ('Public Office', 15), ('Velankanni Road', 45)],
    'Namakkal': [('Bus Stand', 0), ('Salem Road', 15), ('Paramathi Road', 30)],
    'Nilgiris': [('Ooty Bus Stand', 0), ('Charring Cross', 10), ('Coonoor Bus Stand', 60)],
    'Perambalur': [('Bus Stand', 0), ('New Colony', 20)],
    'Pudukkottai': [('Bus Stand', 0), ('Old Bus Stand', 15), ('Alangudi Road', 30)],
    'Ramanathapuram': [('Bus Stand', 0), ('Railway Station', 15), ('Kenikarai', 25)],
    'Ranipet': [('Bus Stand', 0), ('Arcot Road', 15), ('Wallajah Road', 30)],
    'Salem': [('New Bus Stand', 0), ('AVR Circle', 15), ('Kondalampatti', 30), ('Old Bus Stand', 45)],
    'Sivaganga': [('Bus Stand', 0), ('Railway Station', 15)],
    'Tenkasi': [('Bus Stand', 0), ('Railway Station', 15), ('Courtallam Road', 30)],
    'Thanjavur': [('New Bus Stand', 0), ('Old Bus Stand', 20), ('Palli Agraharam', 40)],
    'Theni': [('Bus Stand', 0), ('Theni Junction', 15), ('Cumbum Road', 40)],
    'Thoothukudi': [('New Bus Stand', 0), ('Old Bus Stand', 20), ('VVD Signal', 40)],
    'Tiruchirappalli': [('Central Bus Stand', 0), ('Chathiram', 20), ('Srirangam', 40), ('No.1 Tollgate', 60)],
    'Tirunelveli': [('New Bus Stand (VNR)', 0), ('Palayamkottai', 20), ('Junction', 40)],
    'Tirupathur': [('Bus Stand', 0), ('Collector Office', 20)],
    'Tiruppur': [('New Bus Stand', 0), ('Old Bus Stand', 20), ('Avinashi Road', 40)],
    'Tiruvallur': [('Bus Stand', 0), ('Railway Station', 20)],
    'Tiruvannamalai': [('Bus Stand', 0), ('Temple Entry', 15), ('Girivalam Path', 45)],
    'Tiruvarur': [('Bus Stand', 0), ('Railway Station', 20)],
    'Vellore': [('New Bus Stand', 0), ('Green Circle', 15), ('Katpadi', 40)],
    'Viluppuram': [('New Bus Stand', 0), ('Four Roads', 15), ('Collectorate', 30)],
    'Virudhunagar': [('Bus Stand', 0), ('Railway Station', 20)],
    'Bengaluru': [('Majestic', 0), ('Kalasipalya', 15), ('Madiwala', 45), ('Silk Board', 60), ('Electronic City', 90)],
    'Hyderabad': [('MGBS', 0), ('Ameerpet', 30), ('Jubilee Bus Station', 60), ('Gachibowli', 90), ('Miyapur', 120)]
}

def calculate_point_time(base_time_str, offset_minutes):
    try:
        t = datetime.datetime.strptime(base_time_str, "%I:%M %p")
        new_t = t + datetime.timedelta(minutes=offset_minutes)
        return new_t.strftime("%I:%M %p")
    except:
        return base_time_str


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
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=remember)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('User already exists. Please login instead.', 'error')
            return redirect(url_for('register'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(name=name, email=email, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        # Also store in a human-readable log for reference
        with open('registrations.txt', 'a') as f:
            f.write(f"Name: {name}, Email: {email}, Registered At: {datetime.datetime.now()}\n")
        
        login_user(new_user, remember=True)
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
            
    # Calculate specific times for each point
    source_points = POPULAR_POINTS.get(route.source, [('Main Bus Stand', 0)])
    dest_points = POPULAR_POINTS.get(route.destination, [('Main Bus Stand', 0)])
    
    pickup_points = [
        {'name': p[0], 'time': calculate_point_time(route.departure_time, p[1])}
        for p in source_points
    ]
    drop_points = [
        {'name': p[0], 'time': calculate_point_time(route.arrival_time, p[1])}
        for p in dest_points
    ]
            
    return render_template('seats.html', route=route, booked_seats=booked_seats, 
                           pickup_points=pickup_points, drop_points=drop_points)

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
        pickup_point = data.get('pickup_point')
        drop_point = data.get('drop_point')
        
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
            print(f"Razorpay Connection Error: {str(e)}")
            return jsonify({
                'success': False, 
                'error': 'Payment Gateway Connection Failed. Please check your internet connection and try again.'
            }), 500
            
        # Create pending booking
        booking = Booking(
            pnr=generate_pnr(),
            user_id=current_user.id if current_user.is_authenticated else None,
            route_id=route.id,
            contact_phone=contact_phone,
            contact_email=contact_email,
            pickup_point=pickup_point,
            drop_point=drop_point,
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

@app.route('/contact')
def contact():
    return render_template('contact.html')

# Helper to populate DB
@app.route('/seed')
def seed_db():
    db.drop_all()
    db.create_all()
    
    import datetime
    def add_time(time_str, hours_to_add, minutes_to_add):
        t = datetime.datetime.strptime(time_str, "%I:%M %p")
        new_t = t + datetime.timedelta(hours=hours_to_add, minutes=minutes_to_add)
        return new_t.strftime("%I:%M %p")

    # Coordinates (Approximate Lat, Lon) for all 38 districts + Bengaluru & Hyderabad
    coords = {
        'Ariyalur': (11.14, 79.08), 'Chengalpattu': (12.68, 79.98), 'Chennai': (13.08, 80.27),
        'Coimbatore': (11.01, 76.95), 'Cuddalore': (11.75, 79.77), 'Dharmapuri': (12.13, 78.16),
        'Dindigul': (10.37, 77.98), 'Erode': (11.34, 77.71), 'Kallakurichi': (11.74, 78.96),
        'Kancheepuram': (12.83, 79.70), 'Kanyakumari': (8.09, 77.54), 'Karur': (10.96, 78.08),
        'Krishnagiri': (12.52, 78.21), 'Madurai': (9.92, 78.12), 'Mayiladuthurai': (11.10, 79.65),
        'Nagapattinam': (10.76, 79.84), 'Namakkal': (11.22, 78.16), 'Nilgiris': (11.41, 76.70),
        'Perambalur': (11.23, 78.88), 'Pudukkottai': (10.38, 78.82), 'Ramanathapuram': (9.36, 78.83),
        'Ranipet': (12.92, 79.33), 'Salem': (11.66, 78.14), 'Sivaganga': (9.84, 78.48),
        'Tenkasi': (8.95, 77.30), 'Thanjavur': (10.78, 79.13), 'Theni': (10.01, 77.47),
        'Thoothukudi': (8.80, 78.13), 'Tiruchirappalli': (10.79, 78.70), 'Tirunelveli': (8.71, 77.75),
        'Tirupathur': (12.49, 78.56), 'Tiruppur': (11.10, 77.34), 'Tiruvallur': (13.14, 79.91),
        'Tiruvannamalai': (12.22, 79.07), 'Tiruvarur': (10.77, 79.64), 'Vellore': (12.91, 79.13),
        'Viluppuram': (11.94, 79.49), 'Virudhunagar': (9.58, 77.95),
        'Bengaluru': (12.97, 77.59), 'Hyderabad': (17.38, 78.48)
    }

    def get_distance(city1, city2):
        import math
        c1 = coords.get(city1, (11.0, 78.0))
        c2 = coords.get(city2, (11.0, 78.0))
        dist = math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2) * 111
        return max(50, dist)

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
        'Saraswathi Travels', 'A1 Travels', 'Kallada Travels', 'SRS Travels', 'VRL Travels', 'Orange Tours',
        'Jabbar Travels', 'KPN Travels', 'Parveen Travels', 'Rathimeena Travels', 'Sharma Transports',
        'Neeta Tours', 'Konduskar Travels', 'Paulo Travels', 'Sangita Travels', 'Saini Travels',
        'Amarnath Travels', 'National Travels', 'IntrCity SmartBus', 'Zingbus', 'NueGo',
        'YoloBus', 'GreenLine Travels', 'Sugama Tourist', 'Bharathi Travels', 'Vivekananda Travels',
        'SPS Travels', 'JBT Travels', 'Muthu Travels', 'SRM Transports', 'Tranz King Travels',
        'YBM Travels', 'Kallada G4', 'ABT Xpress', 'Universal Travels', 'Praveen Travels',
        'Kalaivani Travels', 'Tippu Sultan Travels', 'Khushi Tourist', 'Humsafar Travels', 'Shree Travels',
        'Mahasagar Travels', 'Eagle Travels', 'Shatabdi Travels', 'Royal Travels', 'Classic Travels',
        'Vignesh Travels', 'Murugan Travels', 'Kannan Travels', 'Selvam Travels', 'Siva Travels',
        'Cauvery Travels', 'Vaigai Express', 'Pothigai Travels', 'Siruvani Express', 'Kumari Travels',
        'Kovai Superfast', 'Madurai Meenakshi Travels', 'Nellai Express', 'Salem Steel Express',
        'Rockfort Travels', 'Delta Express', 'Kongu Travels', 'Pandian Express', 'Cheran Travels'
    ]

    bus_types = [
        ('AC Sleeper (2+1)', 2.5), ('AC Seater (2+2)', 1.8), ('Non-AC Sleeper (2+1)', 1.5), 
        ('Volvo Multi-Axle (2+2)', 3.0), ('Semi-AC Seater (2+2)', 1.2), ('Premium AC Sleeper', 3.5)
    ]
    
    date_options = [
        (datetime.date.today() + datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        for i in range(0, 8)
    ]

    tn_districts = list(coords.keys())
    tn_districts.remove('Bengaluru')
    tn_districts.remove('Hyderabad')
    
    major_cities = ['Bengaluru', 'Hyderabad']

    morning_times = ['05:00 AM', '06:30 AM', '08:00 AM', '09:30 AM', '11:00 AM']
    afternoon_times = ['01:30 PM', '03:00 PM', '04:30 PM']
    night_times = ['08:00 PM', '09:15 PM', '10:30 PM', '11:45 PM']

    routes = []

    def create_route(src, dst, date_str, dep_time):
        straight_dist = get_distance(src, dst)
        # Use a multiplier of 1.3 for road distance and 65 km/h for realistic TN bus speeds
        road_distance = straight_dist * 1.3
        
        bus_name = random.choice(travel_companies)
        b_type, rate = random.choice(bus_types)
        
        price = int(300 + (road_distance * rate))
        
        # Calculate duration based on road distance and 65 km/h average speed
        duration_hours = road_distance / 65
        h = int(duration_hours)
        m = int((duration_hours - h) * 60)
        dur_str = f"{h}h {m}m"
        
        # Calculate accurate arrival time
        arr_time = add_time(dep_time, h, m)
        
        bus = Bus(company=bus_name, type=b_type, price=price)
        db.session.add(bus)
        db.session.flush()
        
        return Route(
            source=src, destination=dst, date=date_str,
            departure_time=dep_time, arrival_time=arr_time, duration=dur_str, bus_id=bus.id
        )

    # Generate routes
    for city in major_cities:
        for district in tn_districts:
            for date_str in date_options:
                # 3 Morning + 1 Afternoon + 2 Night = 6 buses
                all_times = random.sample(morning_times, 3) + [random.choice(afternoon_times)] + random.sample(night_times, 4)
                for t in all_times:
                    routes.append(create_route(district, city, date_str, t))
                    # Bi-directional
                    routes.append(create_route(city, district, date_str, t))

    # Add key intra-TN routes
    main_tn = ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem']
    for src in main_tn:
        for dst in tn_districts:
            if src == dst: continue
            for date_str in date_options[:2]:
                # 2 Morning + 1 Afternoon + 2 Night = 5 buses
                all_times = random.sample(morning_times, 2) + [random.choice(afternoon_times)] + random.sample(night_times, 2)
                for t in all_times:
                    routes.append(create_route(src, dst, date_str, t))
                    routes.append(create_route(dst, src, date_str, t))

    batch_size = 1000
    for i in range(0, len(routes), batch_size):
        db.session.add_all(routes[i:i+batch_size])
        db.session.commit()

    return f"Database seeded with {len(routes)} routes! Every route now has at least 5-6 buses with accurate times and synchronized durations."

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8000, host='127.0.0.1')
