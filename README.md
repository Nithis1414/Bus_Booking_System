# Nexus Bus Transit System

A premium regional bus booking application built with Flask, SQLAlchemy, and modern web technologies. This system provides a seamless booking experience across 38+ districts, featuring interactive maps and dynamic travel schedules.

## 🚀 Key Features

### 1. Interactive Travel Points
- **Custom Dropdowns**: Replaced standard selects with premium, interactive dropdown components.
- **Location-Specific Timings**: Every boarding and dropping point now calculates its own estimated time based on distance-based offsets.
- **Dynamic Selection**: Real-time UI updates with icons and checkmark indicators for selected locations.

### 2. Live Map Integration
- **OpenStreetMap (Leaflet.js)**: A dedicated Contact Us page featuring a live interactive map.
- **Transit Hubs**: Visual markers for all major transit hubs in Tamil Nadu and Bengaluru.
- **Premium Aesthetics**: Dark-themed map tiles with pulsing HQ indicators.

### 3. Smart Travel Logic
- **Haversine Distance**: Realistic route distance calculations.
- **Road Multipliers**: Adjusted speed (65 km/h) and road factors (1.3x) for accurate 7-8 hour travel times between major cities.
- **Regional Coverage**: Pre-seeded with over 13,000 routes across the South Indian regional network.

### 4. Professional E-Ticketing
- **General Instructions**: Comprehensive travel guidelines and terms included on every ticket.
- **Print Optimization**: Dedicated CSS for high-quality, professional black-and-white ticket printing.
- **PNR Generation**: Unique booking references for every passenger.

### 5. Secure Payments
- **Razorpay Integration**: Seamless checkout experience.
- **Robust Error Handling**: Graceful recovery and user-friendly messaging for network or SSL interruptions.

## 🛠️ Technology Stack
- **Backend**: Python, Flask, Flask-SQLAlchemy
- **Frontend**: HTML5, Vanilla CSS (Modern Design System), JavaScript (ES6+)
- **Icons**: Ionicons
- **Maps**: Leaflet.js / OpenStreetMap
- **Payments**: Razorpay API

## 📦 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Nithis1414/Bus_Booking_System.git
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**:
   Create a `.env` file from `.env.example` and add your `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `SECRET_KEY`.

4. **Initialize Database**:
   ```bash
   flask shell
   >>> from models import db
   >>> db.create_all()
   ```

5. **Run the application**:
   ```bash
   python app.py
   ```

---
*Developed with a focus on premium user experience and regional connectivity.*
