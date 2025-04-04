from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_mail import Mail, Message
import os
import json
import math
from datetime import datetime
import asyncio
from aiosmtplib import SMTP
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from dotenv import load_dotenv
from groq import AsyncGroq

app = Flask(__name__)
app.secret_key = os.urandom(24)  # for session management

# Load environment variables
load_dotenv()

# Configure Flask-Mail for async operation
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465  # Using SSL port instead of 587
app.config['MAIL_USE_SSL'] = True  # Use SSL instead of TLS
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ADDRESS')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('EMAIL_ADDRESS')

mail = Mail(app)

# Initialize Groq client with API key from environment variable
groq_api_key = os.getenv('GROQ_API_KEY')
if not groq_api_key:
    raise ValueError("GROQ_API_KEY environment variable is not set")
groq_client = AsyncGroq(api_key=groq_api_key)

# Login decorator that supports async routes
def login_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if 'user_email' not in session:
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
        return await f(*args, **kwargs)
    return decorated_function

# In-memory storage (replace with database in production)
DONORS = {}
RECIPIENTS = {
    "vrindashram@example.com": {
        "name": "Vrindashram Old Age Home",
        "type": "Old Age Home",
        "latitude": 12.9027,
        "longitude": 77.5600,
        "preferences": ["cooked food", "sweets", "fruits"],
        "dietary_restrictions": ["no spicy food"],
        "capacity": 100,
        "current_needs": "high",
        "available_times": ["07:00-10:00", "12:00-14:00", "18:00-20:00"],
        "contact_person": "Mrs. Lakshmi",
        "phone": "9876543210",
        "address": "Basavanagudi, Bangalore"
    },
    "sevaashram@example.com": {
        "name": "Seva Ashram",
        "type": "Community Kitchen",
        "latitude": 12.8965,
        "longitude": 77.5645,
        "preferences": ["raw food", "grains", "vegetables"],
        "dietary_restrictions": [],
        "capacity": 500,
        "current_needs": "medium",
        "available_times": ["06:00-20:00"],
        "contact_person": "Mr. Ramesh",
        "phone": "9876543211",
        "address": "Jayanagar, Bangalore"
    },
    "hopehome@example.com": {
        "name": "Hope Children's Home",
        "type": "Children's Home",
        "latitude": 12.9150,
        "longitude": 77.5685,
        "preferences": ["fruits", "milk products", "snacks"],
        "dietary_restrictions": ["no nuts"],
        "capacity": 75,
        "current_needs": "high",
        "available_times": ["08:00-18:00"],
        "contact_person": "Ms. Sarah",
        "phone": "9876543212",
        "address": "Richmond Town, Bangalore"
    },
    "youthshelter@example.com": {
        "name": "Youth Shelter Home",
        "type": "Shelter",
        "latitude": 12.8850,
        "longitude": 77.5740,
        "preferences": ["cooked food", "high-protein", "fruits"],
        "dietary_restrictions": [],
        "capacity": 150,
        "current_needs": "medium",
        "available_times": ["07:00-21:00"],
        "contact_person": "Mr. Karthik",
        "phone": "9876543213",
        "address": "BTM Layout, Bangalore"
    },
    "annapurna@example.com": {
        "name": "Annapurna Food Bank",
        "type": "Food Bank",
        "latitude": 12.9080,
        "longitude": 77.5730,
        "preferences": ["raw food", "grains", "vegetables", "non-perishable"],
        "dietary_restrictions": [],
        "capacity": 1000,
        "current_needs": "low",
        "available_times": ["09:00-17:00"],
        "contact_person": "Mrs. Priya",
        "phone": "9876543214",
        "address": "Shanti Nagar, Bangalore"
    }
}

DONATIONS = []
BIOGAS_PLANTS = [
    {
        "name": "Karnataka Renewable Energy Development Ltd. Biogas Plant",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "capacity": 2000,
        "contact_person": "Dr. Ramesh Kumar",
        "phone": "080-22207851",
        "email": "info@kredl.kar.in",
        "address": "No. 39, Shanthi Road, Bengaluru, Karnataka",
        "description": "Large-scale biogas plant operated by KREDL processing agricultural and food waste"
    },
    {
        "name": "Bengaluru East Waste Management",
        "latitude": 12.9850,
        "longitude": 77.7480,
        "capacity": 1500,
        "contact_person": "Mrs. Priya Sharma",
        "phone": "9876543240",
        "email": "east.biogas@bengaluru.com",
        "address": "Whitefield Main Road, Bengaluru, Karnataka",
        "description": "Modern biogas facility serving IT corridor and residential areas"
    },
    {
        "name": "Electronic City Bio Energy Hub",
        "latitude": 12.8458,
        "longitude": 77.6692,
        "capacity": 1800,
        "contact_person": "Mr. Arun Verma",
        "phone": "9876543241",
        "email": "ecity.biogas@bengaluru.com",
        "address": "Electronic City Phase 1, Bengaluru, Karnataka",
        "description": "High-tech biogas plant processing IT park and commercial waste"
    },
    {
        "name": "Yelahanka Green Energy Center",
        "latitude": 13.1005,
        "longitude": 77.5939,
        "capacity": 1200,
        "contact_person": "Dr. Kavitha Rao",
        "phone": "9876543242",
        "email": "yelahanka.biogas@bengaluru.com",
        "address": "Near Airport Road, Yelahanka, Bengaluru, Karnataka",
        "description": "Advanced biogas facility serving north Bangalore region"
    },
    {
        "name": "BTM Layout Waste Processing",
        "latitude": 12.9165,
        "longitude": 77.6101,
        "capacity": 900,
        "contact_person": "Mr. Suresh Kumar",
        "phone": "9876543243",
        "email": "btm.biogas@bengaluru.com",
        "address": "BTM 2nd Stage, Bengaluru, Karnataka",
        "description": "Community biogas plant serving residential areas"
    },
    {
        "name": "Koramangala Bio Energy Plant",
        "latitude": 12.9349,
        "longitude": 77.6205,
        "capacity": 1300,
        "contact_person": "Mrs. Anjali Menon",
        "phone": "9876543244",
        "email": "koramangala.biogas@bengaluru.com",
        "address": "80 Feet Road, Koramangala, Bengaluru, Karnataka",
        "description": "Processing food waste from restaurants and apartments"
    },
    {
        "name": "Indiranagar Green Hub",
        "latitude": 12.9784,
        "longitude": 77.6408,
        "capacity": 1000,
        "contact_person": "Mr. Rajesh Iyer",
        "phone": "9876543245",
        "email": "indiranagar.biogas@bengaluru.com",
        "address": "100 Feet Road, Indiranagar, Bengaluru, Karnataka",
        "description": "Modern facility processing commercial and residential waste"
    },
    {
        "name": "JP Nagar Biogas Center",
        "latitude": 12.9077,
        "longitude": 77.5851,
        "capacity": 850,
        "contact_person": "Dr. Meena Patil",
        "phone": "9876543246",
        "email": "jpnagar.biogas@bengaluru.com",
        "address": "24th Main, JP Nagar, Bengaluru, Karnataka",
        "description": "Community waste processing center for south Bangalore"
    },
    {
        "name": "Hebbal Waste to Energy",
        "latitude": 13.0355,
        "longitude": 77.5950,
        "capacity": 1100,
        "contact_person": "Mr. Vinod Kumar",
        "phone": "9876543247",
        "email": "hebbal.biogas@bengaluru.com",
        "address": "Hebbal Ring Road, Bengaluru, Karnataka",
        "description": "Large-scale facility serving north Bangalore communities"
    },
    {
        "name": "Jayanagar Bio Processing",
        "latitude": 12.9250,
        "longitude": 77.5938,
        "capacity": 950,
        "contact_person": "Mrs. Lakshmi Devi",
        "phone": "9876543248",
        "email": "jayanagar.biogas@bengaluru.com",
        "address": "30th Cross, Jayanagar, Bengaluru, Karnataka",
        "description": "Modern biogas plant serving south Bangalore residential areas"
    },
    {
        "name": "Mandya Bio Energy Plant",
        "latitude": 12.5218,
        "longitude": 76.8951,
        "capacity": 1500,
        "contact_person": "Smt. Lakshmi Devi",
        "phone": "9876543215",
        "email": "mandya.bioenergy@gmail.com",
        "address": "Sugar Town Road, Mandya, Karnataka",
        "description": "Biogas plant utilizing sugarcane waste from local sugar industries"
    },
    {
        "name": "Mysuru Rural Biogas Initiative",
        "latitude": 12.2958,
        "longitude": 76.6394,
        "capacity": 1000,
        "contact_person": "Mr. Krishna Murthy",
        "phone": "9876543216",
        "email": "mysuru.biogas@gmail.com",
        "address": "Outer Ring Road, Mysuru, Karnataka",
        "description": "Community biogas plant serving rural areas around Mysuru"
    },
    {
        "name": "Hubballi Agricultural Waste to Energy",
        "latitude": 15.3647,
        "longitude": 75.1240,
        "capacity": 1200,
        "contact_person": "Dr. Suresh Patil",
        "phone": "9876543217",
        "email": "hubballi.biogas@gmail.com",
        "address": "APMC Yard Road, Hubballi, Karnataka",
        "description": "Modern biogas facility processing agricultural waste from North Karnataka"
    },
    {
        "name": "Belagavi Green Energy Hub",
        "latitude": 15.8497,
        "longitude": 74.4977,
        "capacity": 800,
        "contact_person": "Mr. Vijay Kumar",
        "phone": "9876543218",
        "email": "belagavi.green@gmail.com",
        "address": "Industrial Area, Belagavi, Karnataka",
        "description": "Innovative biogas plant serving urban and rural areas"
    },
    {
        "name": "Tumakuru Agri-Waste Processing Plant",
        "latitude": 13.3379,
        "longitude": 77.1173,
        "capacity": 750,
        "contact_person": "Mrs. Anitha Rao",
        "phone": "9876543219",
        "email": "tumkur.biogas@gmail.com",
        "address": "Agriculture University Road, Tumakuru, Karnataka",
        "description": "Specialized in processing agricultural waste from local farmers"
    },
    {
        "name": "Shivamogga Bio Energy Center",
        "latitude": 13.9299,
        "longitude": 75.5681,
        "capacity": 900,
        "contact_person": "Mr. Prakash Shetty",
        "phone": "9876543220",
        "email": "shimoga.biogas@gmail.com",
        "address": "Industrial Estate, Shivamogga, Karnataka",
        "description": "Modern biogas facility serving the Malnad region"
    },
    {
        "name": "Davangere Food Waste to Energy",
        "latitude": 14.4644,
        "longitude": 75.9218,
        "capacity": 600,
        "contact_person": "Dr. Manjunath K",
        "phone": "9876543221",
        "email": "davangere.biogas@gmail.com",
        "address": "APMC Market Road, Davangere, Karnataka",
        "description": "Converting food waste from markets into renewable energy"
    },
    {
        "name": "Kalaburagi Rural Biogas Plant",
        "latitude": 17.3297,
        "longitude": 76.8343,
        "capacity": 700,
        "contact_person": "Mr. Basavaraj Patil",
        "phone": "9876543222",
        "email": "gulbarga.biogas@gmail.com",
        "address": "Sedam Road, Kalaburagi, Karnataka",
        "description": "Community biogas plant serving rural communities"
    },
    {
        "name": "Bidar Agricultural Waste Processing",
        "latitude": 17.9104,
        "longitude": 77.5199,
        "capacity": 550,
        "contact_person": "Mrs. Suma Kulkarni",
        "phone": "9876543223",
        "email": "bidar.biogas@gmail.com",
        "address": "Agriculture College Road, Bidar, Karnataka",
        "description": "Processing agricultural waste from North Karnataka region"
    },
    {
        "name": "Vijayapura Green Energy Plant",
        "latitude": 16.8302,
        "longitude": 75.7100,
        "capacity": 850,
        "contact_person": "Mr. Ibrahim Khan",
        "phone": "9876543224",
        "email": "vijayapura.biogas@gmail.com",
        "address": "Industrial Area, Vijayapura, Karnataka",
        "description": "Modern biogas facility serving urban and rural areas"
    },
    {
        "name": "Raichur Agri-Waste Center",
        "latitude": 16.2160,
        "longitude": 77.3566,
        "capacity": 650,
        "contact_person": "Dr. Shivakumar R",
        "phone": "9876543225",
        "email": "raichur.biogas@gmail.com",
        "address": "APMC Yard, Raichur, Karnataka",
        "description": "Processing agricultural waste from surrounding farmlands"
    },
    {
        "name": "Hassan Bio Energy Hub",
        "latitude": 13.0068,
        "longitude": 76.1003,
        "capacity": 800,
        "contact_person": "Mr. Venkatesh H",
        "phone": "9876543226",
        "email": "hassan.biogas@gmail.com",
        "address": "Industrial Layout, Hassan, Karnataka",
        "description": "Modern facility processing various organic waste types"
    },
    {
        "name": "Chitradurga Rural Energy Center",
        "latitude": 14.2251,
        "longitude": 76.3982,
        "capacity": 450,
        "contact_person": "Mrs. Savitha Kumar",
        "phone": "9876543227",
        "email": "chitradurga.biogas@gmail.com",
        "address": "Fort Road, Chitradurga, Karnataka",
        "description": "Community biogas plant serving local villages"
    },
    {
        "name": "Ballari Waste Processing Plant",
        "latitude": 15.1394,
        "longitude": 76.9214,
        "capacity": 950,
        "contact_person": "Mr. Santosh Reddy",
        "phone": "9876543228",
        "email": "bellary.biogas@gmail.com",
        "address": "Mining Area Road, Ballari, Karnataka",
        "description": "Large-scale biogas plant serving industrial areas"
    },
    {
        "name": "Koppal Green Energy Center",
        "latitude": 15.3547,
        "longitude": 76.1565,
        "capacity": 500,
        "contact_person": "Dr. Mahesh Patil",
        "phone": "9876543229",
        "email": "koppal.biogas@gmail.com",
        "address": "Industrial Hub, Koppal, Karnataka",
        "description": "Modern facility processing organic waste"
    },
    {
        "name": "Bagalkot Bio Energy Plant",
        "latitude": 16.1691,
        "longitude": 75.6615,
        "capacity": 700,
        "contact_person": "Mr. Ravindra Kulkarni",
        "phone": "9876543230",
        "email": "bagalkot.biogas@gmail.com",
        "address": "Sugar Factory Road, Bagalkot, Karnataka",
        "description": "Processing sugarcane waste and other organic materials"
    },
    {
        "name": "Gadag Agricultural Waste Center",
        "latitude": 15.4317,
        "longitude": 75.6350,
        "capacity": 400,
        "contact_person": "Mrs. Reshma Patil",
        "phone": "9876543231",
        "email": "gadag.biogas@gmail.com",
        "address": "APMC Road, Gadag, Karnataka",
        "description": "Specialized in agricultural waste processing"
    },
    {
        "name": "Haveri Rural Biogas Initiative",
        "latitude": 14.7935,
        "longitude": 75.4043,
        "capacity": 550,
        "contact_person": "Mr. Basavaraj S",
        "phone": "9876543232",
        "email": "haveri.biogas@gmail.com",
        "address": "Farmers Market Road, Haveri, Karnataka",
        "description": "Community biogas plant for rural development"
    },
    {
        "name": "Uttara Kannada Coastal Biogas",
        "latitude": 14.8183,
        "longitude": 74.1352,
        "capacity": 600,
        "contact_person": "Dr. Nagaraj Hegde",
        "phone": "9876543233",
        "email": "karwar.biogas@gmail.com",
        "address": "Coastal Road, Karwar, Karnataka",
        "description": "Processing coastal and agricultural waste"
    },
    {
        "name": "Dharwad Innovation Center",
        "latitude": 15.4589,
        "longitude": 75.0078,
        "capacity": 850,
        "contact_person": "Prof. Srinivas Murthy",
        "phone": "9876543234",
        "email": "dharwad.biogas@gmail.com",
        "address": "University Road, Dharwad, Karnataka",
        "description": "Research-focused biogas facility with latest technology"
    },
    {
        "name": "Chikkamagaluru Green Hub",
        "latitude": 13.3161,
        "longitude": 75.7720,
        "capacity": 500,
        "contact_person": "Mr. George Thomas",
        "phone": "9876543235",
        "email": "chikmagalur.biogas@gmail.com",
        "address": "Coffee Estate Road, Chikkamagaluru, Karnataka",
        "description": "Processing coffee waste and agricultural residue"
    },
    {
        "name": "Udupi Coastal Energy Center",
        "latitude": 13.3409,
        "longitude": 74.7421,
        "capacity": 700,
        "contact_person": "Dr. Mohan Pai",
        "phone": "9876543236",
        "email": "udupi.biogas@gmail.com",
        "address": "Beach Road, Udupi, Karnataka",
        "description": "Processing fish waste and coastal organic matter"
    },
    {
        "name": "Kodagu Forest Waste Plant",
        "latitude": 12.4244,
        "longitude": 75.7382,
        "capacity": 450,
        "contact_person": "Mrs. Lakshmi Bhat",
        "phone": "9876543237",
        "email": "kodagu.biogas@gmail.com",
        "address": "Forest Edge Road, Madikeri, Karnataka",
        "description": "Specialized in processing forest and agricultural waste"
    },
    {
        "name": "Chamarajanagar Bio Energy",
        "latitude": 11.9261,
        "longitude": 76.9401,
        "capacity": 400,
        "contact_person": "Mr. Ravi Kumar",
        "phone": "9876543238",
        "email": "chamarajanagar.biogas@gmail.com",
        "address": "Forest Road, Chamarajanagar, Karnataka",
        "description": "Community biogas plant near wildlife sanctuary"
    },
    {
        "name": "Bengaluru Rural Biogas Center",
        "latitude": 13.2846,
        "longitude": 77.7947,
        "capacity": 1100,
        "contact_person": "Dr. Siddharth Reddy",
        "phone": "9876543239",
        "email": "bengalururural.biogas@gmail.com",
        "address": "Devanahalli Road, Bengaluru Rural, Karnataka",
        "description": "Large-scale facility serving Bengaluru's rural areas"
    }
]

def calculate_distance(lat1, lng1, lat2, lng2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def find_nearest_gobar_plant(lat, lng):
    """Find the nearest gobar plant"""
    distances = [(plant, calculate_distance(lat, lng, plant["latitude"], plant["longitude"])) for plant in BIOGAS_PLANTS]
    nearest = min(distances, key=lambda x: x[1])
    return {
        "plant": nearest[0],
        "distance": round(nearest[1], 2)
    }

async def send_notification_email(to_email, subject, body):
    """Send email notification using aiosmtplib"""
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = app.config['MAIL_DEFAULT_SENDER']
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        # Configure SMTP with SSL
        import ssl
        context = ssl.create_default_context()
        
        smtp = SMTP(
            hostname=app.config['MAIL_SERVER'],
            port=app.config['MAIL_PORT'],
            use_tls=True,  # Use direct SSL
            tls_context=context,
            timeout=30
        )

        print(f"Sending email to {to_email}...")  # Debug log
        
        try:
            await smtp.connect()
            await smtp.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            await smtp.send_message(message)
            print("Email sent successfully")  # Debug log
        finally:
            try:
                await smtp.quit()
            except:
                pass  # Ignore errors during quit

    except Exception as e:
        print(f"Error sending email: {str(e)}")
        import traceback
        print(traceback.format_exc())
        raise

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        users = DONORS if user_type == 'donor' else RECIPIENTS
        
        if email in users and users[email].get('password') == password:
            session['user_email'] = email
            session['user_type'] = user_type
            flash('Login successful!', 'success')
            if user_type == 'donor':
                return redirect(url_for('donor_dashboard'))
            else:
                return redirect(url_for('receiver_dashboard'))
        else:
            flash('Invalid credentials', 'error')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('home'))

@app.route('/register/<user_type>', methods=['GET', 'POST'])
async def register(user_type):
    if request.method == 'POST':
        data = request.form.to_dict()
        data['password'] = request.form.get('password')  # Add password field
        
        if user_type == 'donor':
            DONORS[data['email']] = data
            session['user_email'] = data['email']
            session['user_type'] = 'donor'
            flash('Registration successful!', 'success')
            return redirect(url_for('donor_dashboard'))
        else:
            RECIPIENTS[data['email']] = data
            session['user_email'] = data['email']
            session['user_type'] = 'recipient'
            flash('Registration successful!', 'success')
            return redirect(url_for('receiver_dashboard'))
    
    return render_template('register.html', user_type=user_type)

@app.route('/register')
def register_landing():
    return render_template('register_landing.html')

@app.route('/biogas/register', methods=['GET', 'POST'])
@login_required
async def register_biogas():
    if request.method == 'POST':
        plant_data = request.form.to_dict()
        BIOGAS_PLANTS.append(plant_data)
        flash('Biogas plant registered successfully!', 'success')
        return redirect(url_for('map'))
    return render_template('biogas_register.html')

@app.route('/map')
def map():
    return render_template('map.html', plants=BIOGAS_PLANTS)

@app.route('/donor/dashboard')
@login_required
async def donor_dashboard():
    email = session.get('user_email')
    if session.get('user_type') != 'donor':
        flash('Access denied. Please login as a donor.', 'error')
        return redirect(url_for('login'))
    
    activities = []
    for donation in DONATIONS:
        if donation.get('donor_email') == email:
            activities.append({
                'date': donation['date'],
                'type': 'donation',
                'details': f"{donation['quantity']}kg of {donation['food_type']}",
                'status': donation['status']
            })
    
    return render_template('donor_dashboard.html', 
                         donor=DONORS[email],
                         activities=activities)

@app.route('/submit_donation', methods=['POST'])
async def submit_donation():
    """Handle donation submission and find best recipient"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        print("Received donation data:", data)  # Debug log

        # Validate required fields
        required_fields = ['donor_email', 'food_type', 'quantity', 'pickup_time', 'pickup_latitude', 'pickup_longitude']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
            if not data[field]:  # Check for empty values
                return jsonify({'success': False, 'error': f'Empty value for required field: {field}'}), 400

        # Convert numeric fields
        try:
            data['quantity'] = float(data['quantity'])
            data['pickup_latitude'] = float(data['pickup_latitude'])
            data['pickup_longitude'] = float(data['pickup_longitude'])
        except (ValueError, TypeError) as e:
            return jsonify({'success': False, 'error': f'Invalid numeric value: {str(e)}'}), 400

        print("Finding best recipient...")  # Debug log
        result = await find_best_recipient(data)
        
        if not result:
            return jsonify({'success': False, 'error': 'Failed to find suitable recipient'}), 404

        print("Match found:", result)  # Debug log
        
        # Get recipient details
        recipient = RECIPIENTS.get(result['best_match'])
        if not recipient:
            return jsonify({'success': False, 'error': f'Recipient not found: {result["best_match"]}'}), 404

        # Send email notification to recipient
        try:
            email_subject = "New Food Donation Available"
            email_body = f"""
            A new food donation is available that matches your preferences:
            
            Food Type: {data['food_type']}
            Quantity: {data['quantity']} kg
            Description: {data.get('description', 'No description provided')}
            Pickup Time: {data['pickup_time']}
            Pickup Location: {data.get('address', 'No address provided')}
            
            Donor Email: {data['donor_email']}
            
            Please respond promptly to accept this donation.
            
            Best regards,
            Food Donation Platform Team
            """
            
            # Send to the provided email address
            await send_notification_email("rockybai8234@gmail.com", email_subject, email_body)
            print(f"Notification email sent to rockybai8234@gmail.com")  # Debug log
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            # Continue even if email fails

        # Return success response with match details
        response = {
            'success': True,
            'recipient_name': recipient['name'],
            'match_reason': result['reasoning'],
            'match_score': result['match_score'],
            'distance': next((r['distance'] for r in result.get('recipients', []) if r['email'] == result['best_match']), None)
        }
        print("Returning response:", response)  # Debug log
        return jsonify(response)

    except Exception as e:
        print(f"Error in submit_donation: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/submit_biogas_waste', methods=['POST'])
@login_required
async def submit_biogas_waste():
    if session.get('user_type') != 'donor':
        return jsonify({'success': False, 'error': 'Access denied'})
        
    email = session.get('user_email')
    data = request.form.to_dict()
    
    # Find nearest biogas plant
    nearest = find_nearest_gobar_plant(
        float(data['waste_latitude']), 
        float(data['waste_longitude'])
    )
    
    subject = "Biogas Plant Waste Processing Details"
    body = f"""
Dear {DONORS[email]['name']},

Your waste processing request has been received. Please deliver the waste to:

Plant Name: {nearest['plant']['name']}
Address: {nearest['plant']['address']}
Contact: {nearest['plant']['contact_person']} ({nearest['plant']['phone']})
Distance: {nearest['distance']:.2f} km

Waste Details:
- Type: {data['waste_type']}
- Quantity: {data['waste_quantity']} kg

Best regards,
FoodShare Team
"""
    await send_notification_email(email, subject, body)
    
    flash(f'Request submitted! Please check your email for the nearest biogas plant details.', 'success')
    return redirect(url_for('donor_dashboard'))

@app.route('/receiver/dashboard')
@login_required
async def receiver_dashboard():
    email = session.get('user_email')
    if session.get('user_type') != 'recipient':
        flash('Access denied. Please login as a recipient.', 'error')
        return redirect(url_for('login'))
    
    recipient = RECIPIENTS[email]
    schedule = recipient.get('schedule', {
        'days': ['Monday', 'Wednesday', 'Friday'],
        'start_time': '09:00',
        'end_time': '17:00'
    })
    
    recent_donations = [d for d in DONATIONS if d.get('recipient_email') == email][-5:]
    
    return render_template('receiver_dashboard.html', 
                         schedule=schedule,
                         org=recipient,
                         recent_donations=recent_donations,
                         is_online=recipient.get('is_online', False))

@app.route('/update_info', methods=['POST'])
@login_required
async def update_info():
    if session.get('user_type') != 'recipient':
        return jsonify({'success': False, 'error': 'Access denied'})
        
    email = session.get('user_email')
    data = request.form.to_dict()
    recipient = RECIPIENTS[email]
    recipient.update({
        'name': data['name'],
        'contact_person': data['contact_person'],
        'phone': data['phone'],
        'email': data['email'],
        'address': data['address']
    })
    
    subject = "Organization Information Updated"
    body = f"""
Dear {recipient['name']},

Your organization information has been updated successfully.

Best regards,
FoodShare Team
"""
    await send_notification_email(email, subject, body)
    
    flash('Organization information updated successfully!', 'success')
    return redirect(url_for('receiver_dashboard'))

@app.route('/update_schedule', methods=['POST'])
@login_required
async def update_schedule():
    if session.get('user_type') != 'recipient':
        return jsonify({'success': False, 'error': 'Access denied'})
        
    email = session.get('user_email')
    schedule = {
        'days': request.form.getlist('collection_days'),
        'start_time': request.form.get('start_time'),
        'end_time': request.form.get('end_time')
    }
    
    RECIPIENTS[email]['schedule'] = schedule
    
    subject = "Collection Schedule Updated"
    body = f"""
Dear {RECIPIENTS[email]['name']},

Your collection schedule has been updated:
Days: {', '.join(schedule['days'])}
Time: {schedule['start_time']} - {schedule['end_time']}

Donors in your area will be notified of your availability.

Best regards,
FoodShare Team
"""
    await send_notification_email(email, subject, body)
    
    flash('Collection schedule updated successfully!', 'success')
    return redirect(url_for('receiver_dashboard'))

@app.route('/toggle_status', methods=['POST'])
@login_required
async def toggle_status():
    if session.get('user_type') != 'recipient':
        return jsonify({'success': False, 'error': 'Access denied'})
        
    email = session.get('user_email')
    RECIPIENTS[email]['is_online'] = not RECIPIENTS[email].get('is_online', False)
    subject = "Status Updated"
    body = f"""
Dear {RECIPIENTS[email]['name']},

Your status has been updated to {'online' if RECIPIENTS[email]['is_online'] else 'offline'}.

Best regards,
FoodShare Team
"""
    await send_notification_email(email, subject, body)
    
    return jsonify({'success': True})

@app.route('/chat', methods=['POST'])
async def chat():
    """Handle chatbot interactions"""
    try:
        user_message = request.json.get('message', '')
        
        # Create chat completion with Groq
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant for a food donation platform. Help users with questions about donations, food safety, and connecting donors with recipients."
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            model="qwen-2.5-32b",
            temperature=0.3,
            max_tokens=1000
        )
        
        return jsonify({
            "response": chat_completion.choices[0].message.content
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/donate', methods=['GET', 'POST'])
async def donate():
    if request.method == 'POST':
        data = request.form.to_dict()
        data['location'] = {
            'lat': float(data.get('latitude')),
            'lng': float(data.get('longitude'))
        }
        
        # Check food quality
        food_quality_ok = analyze_food_quality(data['food_type'], float(data['shelf_life']))
        
        if not food_quality_ok:
            # Find nearest biogas plant
            nearest = find_nearest_gobar_plant(data['location']['lat'], data['location']['lng'])
            
            flash('Food quality check failed. Redirecting to nearest biogas plant.', 'warning')
            return redirect(url_for('map', highlight_plant=nearest['plant']['name']))
        
        # Find best recipient
        recipient_email = find_best_recipient(data)
        if not recipient_email:
            flash('No suitable recipients found in your area. Please try again later or consider our biogas plant options.', 'warning')
            return redirect(url_for('map'))
            
        if recipient_email in RECIPIENTS:
            # Add donation to the list
            donation_data = {
                'id': len(DONATIONS) + 1,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'donor_name': DONORS.get(data.get('donor_email', ''), {}).get('name', 'Anonymous'),
                'donor_phone': data.get('donor_phone', 'N/A'),
                'recipient_name': RECIPIENTS[recipient_email]['name'],
                'items': data['food_type'],
                'quantity': data.get('quantity', 'N/A'),
                'status': 'pending'
            }
            DONATIONS.append(donation_data)
            
            # Send notification to recipient
            subject = "New Food Donation Available"
            body = f"""
Dear {RECIPIENTS[recipient_email]['name']},

A new food donation is available:

Food Type: {data['food_type']}
Quantity: {data['quantity']} servings
Available Until: {data['availability_time']}
Location: {data['address']}

Please respond quickly to claim this donation.

Best regards,
Food Donation Platform Team
"""
            await send_notification_email(recipient_email, subject, body)
            flash('Donation successful! The recipient has been notified.', 'success')
        else:
            flash('No suitable recipient found at this time.', 'warning')
        
        return redirect(url_for('home'))
    
    return render_template('donate.html')

@app.route('/api/analyze-food', methods=['POST'])
def analyze_food():
    data = request.json
    # Here we would integrate with Groq API for food analysis
    # For now, return a mock response
    return jsonify({
        "suitable_for_consumption": True,
        "quality_score": 85,
        "shelf_life_hours": 24
    })

def analyze_food_quality(food_type, shelf_life):
    """Analyze food quality using AI (mock implementation)"""
    # In a real implementation, this would use the Groq API
    if shelf_life <= 2:  # If shelf life is 2 hours or less
        return False
    return True

def find_best_recipient(donation):
    """Find the best recipient using location and schedule matching"""
    if not RECIPIENTS:
        return None
        
    donor_lat = donation['location']['lat']
    donor_lng = donation['location']['lng']
    donation_time = datetime.strptime(donation['pickup_time'], '%Y-%m-%dT%H:%M')
    
    # Calculate distances and find recipients within 10km radius
    nearby_recipients = []
    for email, recipient in RECIPIENTS.items():
        try:
            # Check if recipient is online and available
            if not recipient.get('is_online', False):
                continue
                
            # Check if recipient's schedule matches
            schedule = recipient.get('schedule', {})
            if schedule:
                if donation_time.strftime('%A') not in schedule.get('days', []):
                    continue
                if (schedule.get('start_time', '00:00') > donation_time.strftime('%H:%M') or
                    schedule.get('end_time', '23:59') < donation_time.strftime('%H:%M')):
                    continue
            
            # Check distance
            recipient_lat = float(recipient.get('latitude', 0))
            recipient_lng = float(recipient.get('longitude', 0))
            distance = calculate_distance(donor_lat, donor_lng, recipient_lat, recipient_lng)
            
            if distance <= 10:  # Within 10km radius
                recipient['email'] = email
                recipient['distance'] = distance
                nearby_recipients.append(recipient)
        except (ValueError, TypeError):
            continue
    
    if not nearby_recipients:
        return None
        
    # Sort by distance and capacity
    sorted_recipients = sorted(nearby_recipients, 
                             key=lambda x: (x['distance'], -int(x.get('capacity', 0))))
    
    return sorted_recipients[0]['email'] if sorted_recipients else None

@app.route('/submit_biogas_request', methods=['POST'])
async def submit_biogas_request():
    """Submit request to nearest biogas plant"""
    try:
        email = request.form.get('email')
        waste_type = request.form.get('waste_type')
        quantity = request.form.get('quantity')
        pickup_date = request.form.get('pickup_date')
        
        # Find nearest biogas plant
        nearest = find_nearest_biogas_plant(request.form)
        
        subject = "Biogas Plant Request Confirmation"
        body = f"""
Dear User,

Thank you for your biogas waste request. Here are the details of the nearest biogas plant:

Plant Name: {nearest['name']}
Distance: {nearest['distance']} km
Address: {nearest['address']}
Contact: {nearest['phone']}

Your Request Details:
Waste Type: {waste_type}
Quantity: {quantity} kg
Pickup Date: {pickup_date}

Best regards,
FoodShare Team
"""
        await send_notification_email(email, subject, body)
        
        flash(f'Request submitted! Please check your email for the nearest biogas plant details.', 'success')
        return redirect(url_for('donor_dashboard'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('donor_dashboard'))

@app.route('/update_collection_schedule', methods=['POST'])
async def update_collection_schedule():
    """Update collection schedule for a receiver"""
    try:
        email = request.form.get('email')
        schedule = request.form.get('schedule')
        
        subject = "Collection Schedule Updated"
        body = f"""
Dear Partner,

Your collection schedule has been updated successfully.

New Schedule: {schedule}

Best regards,
FoodShare Team
"""
        await send_notification_email(email, subject, body)
        
        flash('Collection schedule updated successfully!', 'success')
        return redirect(url_for('receiver_dashboard'))
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('receiver_dashboard'))

@app.route('/process_donation', methods=['POST'])
async def process_donation():
    """Process a food donation"""
    try:
        if not request.is_json:
            return jsonify({'success': False, 'error': 'Content-Type must be application/json'}), 415

        data = request.get_json()
        
        # Find best recipient
        result = await find_best_recipient(data)
        
        if result and result.get('best_match'):
            recipient_email = result['best_match']
            recipient = RECIPIENTS[recipient_email]
            
            subject = "New Food Donation Available"
            body = f"""
Dear {recipient['name']},

A new food donation is available that matches your preferences:

Food Type: {data['food_type']}
Quantity: {data['quantity']} kg
Description: {data.get('description', 'No description provided')}
Pickup Time: {data['pickup_time']}

Please respond promptly to accept this donation.

Best regards,
Food Donation Platform Team
"""
            await send_notification_email(recipient_email, subject, body)
            flash('Donation successful! The recipient has been notified.', 'success')
        else:
            flash('No suitable recipient found at this time.', 'warning')
        
        return redirect(url_for('donor_dashboard'))
        
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('donor_dashboard'))

async def find_best_recipient(donation_data):
    """Find the best recipient using AI analysis with Groq"""
    try:
        # Calculate distances to all recipients
        recipients_with_distance = []
        
        # Get donor coordinates directly from the data
        donor_lat = float(donation_data['pickup_latitude'])
        donor_lng = float(donation_data['pickup_longitude'])

        print(f"Calculating distances from donor location: {donor_lat}, {donor_lng}")  # Debug log

        for recipient_email, recipient in RECIPIENTS.items():
            try:
                # Calculate distance using Haversine formula
                lat2 = float(recipient['latitude'])
                lon2 = float(recipient['longitude'])
                
                R = 6371  # Earth's radius in km
                dlat = math.radians(lat2 - donor_lat)
                dlon = math.radians(lon2 - donor_lng)
                a = math.sin(dlat/2)**2 + math.cos(math.radians(donor_lat)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
                distance = R * c
                
                # Create a copy of recipient data with distance
                recipient_data = {
                    'name': recipient['name'],
                    'email': recipient_email,
                    'type': recipient['type'],
                    'preferences': recipient['preferences'],
                    'dietary_restrictions': recipient['dietary_restrictions'],
                    'distance': round(distance, 2),  # Distance in km
                    'capacity': recipient['capacity'],
                    'current_needs': recipient['current_needs'],
                    'available_times': recipient['available_times']
                }
                recipients_with_distance.append(recipient_data)
                print(f"Added recipient {recipient['name']} at distance {distance:.2f} km")  # Debug log
            except Exception as e:
                print(f"Error processing recipient {recipient_email}: {str(e)}")
                continue

        # Sort recipients by distance
        recipients_with_distance.sort(key=lambda x: x['distance'])
        print(f"Sorted {len(recipients_with_distance)} recipients by distance")  # Debug log
        
        # Prepare context for AI analysis
        donation_time = datetime.strptime(donation_data['pickup_time'], '%Y-%m-%dT%H:%M')
        donation_hour = donation_time.strftime('%H:%M')
        
        prompt = f"""Analyze this food donation and find the best recipient based on the following criteria:

DONATION DETAILS:
- Food Type: {donation_data['food_type']}
- Quantity: {donation_data['quantity']} kg
- Description: {donation_data.get('description', 'No description provided')}
- Pickup Time: {donation_hour}
- Donor Location: {donor_lat}, {donor_lng}

AVAILABLE RECIPIENTS (sorted by distance):
{json.dumps(recipients_with_distance, indent=2)}

MATCHING RULES:
1. Food Type Compatibility (40% weight):
   - Match food type with recipient preferences
   - Consider dietary restrictions
   - Special rules:
     * Sweets/desserts → prioritize Vrindashram Old Age Home
     * Raw food/bulk → prioritize Seva Ashram or Annapurna Food Bank
     * High-protein → prioritize Youth Shelter Home
     * Child-friendly → prioritize Hope Children's Home

2. Distance (30% weight):
   - Prefer recipients within 5km
   - Calculate penalty for distances > 5km
   - Consider traffic in Bangalore

3. Timing (20% weight):
   - Check if pickup time is within recipient's available hours
   - Consider Bangalore traffic patterns
   - Morning donations (6-10 AM) prioritize breakfast serving locations
   - Evening donations (4-8 PM) prioritize dinner serving locations

4. Current Needs (10% weight):
   - Prioritize recipients with "high" current needs
   - Consider recipient capacity vs donation quantity

Return a JSON response in this exact format:
{{
    "best_match": "recipient_email@example.com",
    "match_score": 85,
    "reasoning": "Detailed explanation of why this recipient is best",
    "alternative_matches": ["backup1@example.com", "backup2@example.com"]
}}

Make sure to explain the match score breakdown in the reasoning."""

        print("Sending request to Groq...")  # Debug log
        completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert food donation matching system that specializes in Bangalore's geography, traffic patterns, and food distribution logistics. Always return responses in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="qwen-2.5-32b",
            temperature=0.3,
            max_tokens=1000
        )
        
        try:
            result = json.loads(completion.choices[0].message.content)
            print(f"Received AI response: {json.dumps(result, indent=2)}")  # Debug log
            
            if not isinstance(result, dict) or 'best_match' not in result:
                raise ValueError("Invalid response format from AI")
            
            # Validate the best match exists
            if result['best_match'] not in RECIPIENTS:
                raise ValueError(f"Selected recipient {result['best_match']} not found in database")
            
            print(f"Selected recipient: {RECIPIENTS[result['best_match']]['name']}")  # Debug log
            return result
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON response from Groq: {str(e)}")
            print(f"Raw response: {completion.choices[0].message.content}")
            return None
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            return None

    except Exception as e:
        print(f"Error in AI analysis: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

if __name__ == '__main__':
    app.run(debug=True)
