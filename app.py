from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail, Message
import mysql.connector
from xhtml2pdf import pisa
from io import BytesIO
import os

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super_secret_key_12345')  # Use env var in production!

# Email Configuration - use env vars in production
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'rushikeshkanekar@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '12345678')
mail = Mail(app)

# MySQL Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rushi@2001",
    database="flightdb"
)

def get_cursor():
    return db.cursor(dictionary=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password or not confirm_password:
            flash("All fields are required!", "danger")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template('register.html')

        cursor = get_cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        cursor.close()

        if existing_user:
            flash("Email already registered!", "danger")
            return render_template('register.html')

        hashed_password = generate_password_hash(password)

        cursor = get_cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        db.commit()
        cursor.close()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter email and password", "danger")
            return render_template('login.html')

        cursor = get_cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash("Logged in successfully!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        origin = request.form.get('origin', '').strip().lower()
        destination = request.form.get('destination', '').strip().lower()
        airline = request.form.get('airline', '').strip().lower()
        departure = request.form.get('departure', '').strip()
        price_min = request.form.get('price_min', '').strip()
        price_max = request.form.get('price_max', '').strip()
        time_of_day = request.form.get('time_of_day', '').strip().lower()
        sort_by = request.form.get('sort_by', '').strip().lower()

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

        try:
            price_min_val = float(price_min) if price_min else None
            price_max_val = float(price_max) if price_max else None
        except ValueError:
            price_min_val = None
            price_max_val = None

        if price_min_val is not None and price_max_val is not None:
            sql += " AND price BETWEEN %s AND %s"
            values.extend([price_min_val, price_max_val])
        elif price_min_val is not None:
            sql += " AND price >= %s"
            values.append(price_min_val)
        elif price_max_val is not None:
            sql += " AND price <= %s"
            values.append(price_max_val)

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

        cursor = get_cursor()
        cursor.execute(sql, values)
        flights = cursor.fetchall()
        cursor.close()

        return render_template('search.html', flights=flights)

    return render_template('search.html', flights=None)

@app.route('/book/<int:flight_id>', methods=['GET', 'POST'])
def book_flight(flight_id):
    if 'user_id' not in session:
        flash("Please login to book a flight.", "warning")
        return redirect(url_for('login'))

    cursor = get_cursor()
    cursor.execute("SELECT * FROM flights WHERE id = %s", (flight_id,))
    flight = cursor.fetchone()
    cursor.close()

    if not flight:
        return "Flight not found", 404

    if request.method == 'POST':
        user_id = session['user_id']
        email = request.form.get('email', '').strip()
        total_passengers = int(request.form.get('total_passengers', 1))

        cursor = get_cursor()
        cursor.execute(
            "INSERT INTO bookings (user_id, flight_id, total_passengers, email, payment_status) VALUES (%s, %s, %s, %s, %s)",
            (user_id, flight_id, total_passengers, email, 'Pending')
        )
        db.commit()
        booking_id = cursor.lastrowid

        for i in range(1, total_passengers + 1):
            p_name = request.form.get(f'name_{i}', '').strip()
            p_age = request.form.get(f'age_{i}', '0').strip()
            p_gender = request.form.get(f'gender_{i}', '').strip()

            if not p_name or not p_age.isdigit() or not p_gender:
                flash("Please provide valid passenger details.", "danger")
                cursor.close()
                return render_template('passenger.html', flight=flight)

            cursor.execute(
                "INSERT INTO passengers (booking_id, name, age, gender) VALUES (%s, %s, %s, %s)",
                (booking_id, p_name, int(p_age), p_gender)
            )
        db.commit()
        cursor.close()

        return redirect(url_for('payment', booking_id=booking_id))

    return render_template('passenger.html', flight=flight)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'user_id' not in session:
        flash("Please login to proceed with payment.", "warning")
        return redirect(url_for('login'))

    cursor = get_cursor()
    cursor.execute("""
        SELECT b.*, f.airline, f.origin, f.destination, f.departure, f.price
        FROM bookings b
        JOIN flights f ON b.flight_id = f.id
        WHERE b.id = %s
    """, (booking_id,))
    booking = cursor.fetchone()
    cursor.close()

    if not booking:
        return "Booking not found", 404

    if request.method == 'POST':
        card_number = request.form.get('card_number', '').strip()
        card_expiry = request.form.get('card_expiry', '').strip()
        card_cvv = request.form.get('card_cvv', '').strip()

        if not card_number or not card_expiry or not card_cvv:
            flash("Please fill all card details", "danger")
            return render_template('payment.html', booking=booking)

        # In real app: Integrate with payment gateway here
        # For demo, we just mark payment success
        cursor = get_cursor()
        cursor.execute("UPDATE bookings SET payment_status = %s WHERE id = %s", ('Success', booking_id))
        db.commit()
        cursor.close()

        # Send confirmation email
        try:
            msg = Message(
                "Flight Booking Confirmation",
                sender=app.config['MAIL_USERNAME'],
                recipients=[booking['email']]
            )
            msg.body = f"Dear {session['user_name']}, your booking for flight {booking['airline']} from {booking['origin']} to {booking['destination']} on {booking['departure']} has been confirmed."
            mail.send(msg)
        except Exception as e:
            print(f"Email send error: {e}")

        flash("Payment successful! Confirmation email sent.", "success")
        return redirect(url_for('home'))

    return render_template('payment.html', booking=booking)

@app.route('/admin')
def admin_dashboard():
    # Simple check for admin - you can improve this with roles
    if session.get('user_name') != 'admin':
        flash("Admin access only.", "danger")
        return redirect(url_for('home'))

    cursor = get_cursor()
    cursor.execute("""
        SELECT b.*, u.name AS user_name, f.airline, f.origin, f.destination, f.departure
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN flights f ON b.flight_id = f.id
        ORDER BY b.id DESC
    """)
    bookings = cursor.fetchall()
    cursor.close()

    return render_template('admin.html', bookings=bookings)

def convert_html_to_pdf(source_html):
    result = BytesIO()
    pisa_status = pisa.CreatePDF(source_html, dest=result)
    if pisa_status.err:
        return None
    return result.getvalue()

@app.route('/download_ticket/<int:booking_id>')
def download_ticket(booking_id):
    if 'user_id' not in session:
        flash("Please login to download ticket.", "warning")
        return redirect(url_for('login'))

    cursor = get_cursor()
    cursor.execute("""
        SELECT b.*, u.name as user_name, f.airline, f.origin, f.destination, f.departure, f.price
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN flights f ON b.flight_id = f.id
        WHERE b.id = %s
    """, (booking_id,))
    booking = cursor.fetchone()

    cursor.execute("SELECT * FROM passengers WHERE booking_id = %s", (booking_id,))
    passengers = cursor.fetchall()
    cursor.close()

    if not booking:
        return "Booking not found", 404

    html = render_template('ticket.html', booking=booking, passengers=passengers)
    pdf = convert_html_to_pdf(html)

    if pdf is None:
        return "Failed to generate PDF", 500

    return (pdf, 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'attachment; filename=eticket_{booking_id}.pdf'
    })

if __name__ == '__main__':
    app.run(debug=True)
