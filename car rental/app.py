from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # ផ្លាស់ប្តូរសម្រាប់ security

# ==================== MySQL Configuration ====================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'demo_classa'

mysql = MySQL(app)

# Sample Database Setup
def init_db():
    cur = mysql.connection.cursor()
    # Create tables if not exists – ជួសជុល: បន្ថែម UNIQUE KEY លើ username
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(50),
            email VARCHAR(100),
            role ENUM('admin', 'customer', 'staff')
        ) ENGINE=InnoDB
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model VARCHAR(100),
            price_per_day DECIMAL(10,2),
            status ENUM('available', 'rented'),
            image VARCHAR(200)
        ) ENGINE=InnoDB
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            car_id INT,
            start_date DATE,
            end_date DATE,
            status ENUM('confirmed', 'completed', 'cancelled'),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (car_id) REFERENCES cars(id)
        ) ENGINE=InnoDB
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT,
            amount DECIMAL(10,2),
            method ENUM('cash', 'card', 'online'),
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        ) ENGINE=InnoDB
    ''')
    
    # ជួសជុល: បន្ថែម column image បើមិនមាន
    try:
        cur.execute("ALTER TABLE cars ADD COLUMN IF NOT EXISTS image VARCHAR(200)")
    except:
        pass  # បើមានរួច មិនធ្វើអ្វី
    
    # Insert sample data (ប្រើ INSERT IGNORE ដើម្បីជៀសវាង duplicate)
    cur.execute("INSERT IGNORE INTO users (username, password, email, role) VALUES ('admin', 'admin123', 'admin@example.com', 'admin'), ('customer1', 'pass123', 'customer@example.com', 'customer')")
    cur.execute("INSERT IGNORE INTO cars (model, price_per_day, status, image) VALUES ('Toyota Camry', 50.00, 'available', 'car1.jpg'), ('Honda Civic', 40.00, 'available', 'car2.jpg')")
    mysql.connection.commit()
    cur.close()

# ជួសជុល: ហៅ init_db() ក្នុង app context
with app.app_context():
    init_db()

# Email Function
def send_email(to_email, subject, body):
    from_email = "your_email@gmail.com"  # កែទៅ email របស់បង់
    password = "your_app_password"  # ប្រើ App Password សម្រាប់ Gmail
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Email error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[3]  # ជួសជុល: បន្ថែម email ក្នុង session
            session['role'] = user[4]
            if user[4] == 'admin':
                return redirect(url_for('dashboard'))
            return redirect(url_for('welcome'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = 'customer'  # Default
        cur = mysql.connection.cursor()
        # ជួសជុល: ពិនិត្យ username មុនពេល insert
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        if cur.fetchone():
            flash('Username already exists! Please choose another one.')
            cur.close()
            return render_template('index.html')
        cur.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)", (username, password, email, role))
        mysql.connection.commit()
        cur.close()
        flash('Registered successfully!')
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/cars')
def cars():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cars WHERE status='available'")
    car_list = cur.fetchall()
    cur.close()
    return render_template('cars.html', cars=car_list)

@app.route('/booking/<int:car_id>', methods=['GET', 'POST'])
def booking(car_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cars WHERE id=%s", (car_id,))
    car = cur.fetchone()
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        user_id = session['user_id']
        cur.execute("INSERT INTO bookings (user_id, car_id, start_date, end_date, status) VALUES (%s, %s, %s, %s, 'confirmed')",
                    (user_id, car_id, start_date, end_date))
        booking_id = cur.lastrowid
        mysql.connection.commit()
        # Update car status
        cur.execute("UPDATE cars SET status='rented' WHERE id=%s", (car_id,))
        mysql.connection.commit()
        # Send email
        user_email = session.get('email', 'customer@example.com')
        send_email(user_email, 'Booking Confirmed', f'<h2>Your booking for {car[1]} is confirmed!</h2><p>From {start_date} to {end_date}</p>')
        flash('Booking confirmed!')
        cur.close()
        return redirect(url_for('payment', booking_id=booking_id))
    cur.close()
    return render_template('booking.html', car=car)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if request.method == 'POST':
        amount = request.form['amount']
        method = request.form['method']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO payments (booking_id, amount, method) VALUES (%s, %s, %s)", (booking_id, amount, method))
        mysql.connection.commit()
        # Fetch booking details for receipt
        cur.execute("SELECT b.id, b.start_date, b.end_date, c.model FROM bookings b JOIN cars c ON b.car_id=c.id WHERE b.id=%s", (booking_id,))
        booking = cur.fetchone()
        cur.close()
        return render_template('payment_receipt.html', booking=booking, amount=amount, method=method)
    return render_template('payment.html', booking_id=booking_id)

@app.route('/dashboard')
def dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM cars")
    total_cars = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM bookings WHERE status='confirmed'")
    total_bookings = cur.fetchone()[0]
    cur.close()
    return render_template('dashboard.html', total_cars=total_cars, total_bookings=total_bookings)

@app.route('/welcome')
def welcome():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('welcome.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)