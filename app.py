from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from flask_mail import Mail, Message
import mysql.connector

app = Flask(__name__)
app.secret_key = 'super_secret_key_12345'  # Change this in production

# ✅ Email Config (TESTING ONLY — use app password for production)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'rushikeshkanekar@gmail.com'
app.config['MAIL_PASSWORD'] = '12345678'
mail = Mail(app)

# ✅ MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rushi@2001",
    database="flightdb"
)
cursor = db.cursor(dictionary=True)

# ✅ Home Route
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# ✅ Search Route
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        origin = request.form.get('origin', '').lower()
        destination = request.form.get('destination', '').lower()
        airline = request.form.get('airline', '').lower()
        departure = request.form.get('departure', '')
        price_min = request.form.get('price_min', '')
        price_max = request.form.get('price_max', '')
        time_of_day = request.form.get('time_of_day', '')
        sort_by = request.form.get('sort_by', '')

        sql = "SELECT * FROM flights WHERE 1=1"
        values = []

        if origin:
            sql += " AND LOWER(origin) LIKE %s"
            values.append(f"%{origin}%")
        if destination:
            sql += " AND LOWER(destination) LIKE %s"
            values.append(f"%{destination}%")
        if airline:
            sql += " AND LOWER(airline) LIKE %s"
            values.append(f"%{airline}%")
        if departure:
            sql += " AND DATE(departure) = %s"
            values.append(departure)
        if price_min and price_max:
            sql += " AND price BETWEEN %s AND %s"
            values.append(price_min)
            values.append(price_max)
        if time_of_day:
            if time_of_day == "morning":
                sql += " AND TIME(departure) BETWEEN '05:00:00' AND '11:59:59'"
            elif time_of_day == "afternoon":
                sql += " AND TIME(departure) BETWEEN '12:00:00' AND '16:59:59'"
            elif time_of_day == "evening":
                sql += " AND TIME(departure) BETWEEN '17:00:00' AND '20:59:59'"
            elif time_of_day == "night":
                sql += " AND (TIME(departure) >= '21:00:00' OR TIME(departure) <= '04:59:59')"

        if sort_by == "price_asc":
            sql += " ORDER BY price ASC"
        elif sort_by == "price_desc":
            sql += " ORDER BY price DESC"
        elif sort_by == "departure_asc":
            sql += " ORDER BY departure ASC"
        elif sort_by == "departure_desc":
            sql += " ORDER BY departure DESC"

        cursor.execute(sql, values)
        flights = cursor.fetchall()
        return render_template('search.html', flights=flights)

    return render_template('search.html', flights=None)

# ✅ Booking Route (form + database + email)
@app.route('/book/<int:flight_id>', methods=['GET', 'POST'])
def book_flight(flight_id):
    cursor.execute("SELECT * FROM flights WHERE id = %s", (flight_id,))
    flight = cursor.fetchone()

    if not flight:
        return "Flight not found", 404

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')

        # Insert booking
        cursor.execute(
            "INSERT INTO bookings (flight_id, name, email) VALUES (%s, %s, %s)",
            (flight_id, name, email)
        )
        db.commit()

        # Send email
        try:
            msg = Message("Flight Booking Confirmation",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"""Hi {name},

Your flight has been successfully booked!

✈️ Flight: {flight['airline']}  
🌍 From: {flight['origin']}  
🏁 To: {flight['destination']}  
🕑 Departure: {flight['departure']}

Thank you for booking with us!
"""
            mail.send(msg)
        except Exception as e:
            print("Email error:", e)

        return render_template('booking_success.html', flight=flight, name=name)

    return render_template('checkout_form.html', flight=flight)

# ✅ Admin Login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM admin WHERE username = %s", (username,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin['password'], password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid username or password")

    return render_template('admin_login.html')

# ✅ Admin Dashboard with Bookings
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    cursor.execute("""
        SELECT b.*, f.origin, f.destination, f.airline, f.departure
        FROM bookings b
        JOIN flights f ON b.flight_id = f.id
        ORDER BY b.id DESC
    """)
    bookings = cursor.fetchall()
    return render_template('admin_dashboard.html', bookings=bookings)

# ✅ Admin Logout
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# ✅ Run App
if __name__ == '__main__':
    app.run(debug=True)
