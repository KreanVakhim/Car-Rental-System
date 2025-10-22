from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'your_super_secret_key_here'  # ផ្លាស់ប្តូរទៅជា secret key ពិតប្រាកដ

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'demo_classa'
mysql = MySQL(app)

# Email Configuration (សម្រាប់ send welcome email - ប្រើ Gmail ឧទាហរណ៍)
EMAIL_ADDRESS = 'your_email@gmail.com'
EMAIL_PASSWORD = 'your_app_password'  # ប្រើ App Password របស់ Gmail

# បង្កើតតារាងទិន្នន័យ (DROP មុន CREATE ដើម្បីជៀសវាង error)
def init_db():
    cur = mysql.connection.cursor()
    
    # DROP tables ដើម្បី reset (សម្រាប់ dev - លុបពាក្យនេះបើចង់ keep data)
    cur.execute('DROP TABLE IF EXISTS invoices')
    cur.execute('DROP TABLE IF EXISTS payments')
    cur.execute('DROP TABLE IF EXISTS bookings')
    cur.execute('DROP TABLE IF EXISTS cars')
    cur.execute('DROP TABLE IF EXISTS users')
    
    # CREATE tables
    cur.execute('''
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100) UNIQUE,
            password VARCHAR(255),
            user_type ENUM('admin', 'customer', 'staff') DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE cars (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand VARCHAR(50),
            model VARCHAR(50),
            price DECIMAL(10,2),
            image VARCHAR(255),
            available BOOLEAN DEFAULT TRUE,
            description TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            car_id INT,
            start_date DATE,
            end_date DATE,
            status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (car_id) REFERENCES cars(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT,
            amount DECIMAL(10,2),
            method VARCHAR(50),
            transaction_id VARCHAR(100),
            status ENUM('pending', 'paid') DEFAULT 'pending',
            paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(id)
        )
    ''')
    cur.execute('''
        CREATE TABLE invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            payment_id INT,
            total_amount DECIMAL(10,2),
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payment_id) REFERENCES payments(id)
        )
    ''')
    
    # បន្ថែម sample data
    cur.execute("INSERT INTO users (name, email, password, user_type) VALUES ('Admin', 'admin@example.com', 'admin123', 'admin')")
    cur.execute("INSERT INTO users (name, email, password, user_type) VALUES ('Staff', 'staff@example.com', 'staff123', 'staff')")
    cur.execute("INSERT INTO cars (brand, model, price, image, available, description) VALUES "
                "('Toyota', 'Camry', 50.00, '/static/images/toyota_camry.jpg', TRUE, 'Sedan car'), "
                "('Honda', 'Civic', 45.00, '/static/images/honda_civic.jpg', TRUE, 'Compact car')")
    mysql.connection.commit()
    cur.close()

# គ្រឿងមធ្យោបាយសម្រាប់ send email
def send_email(to_email, subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, to_email, text)
        server.quit()
        return True
    except:
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['logged_in'] = True
            session['user_id'] = user['id']  # ធានា id ជា int
            session['user_type'] = user['user_type']
            session['name'] = user['name']
            flash('ចូលប្រព័ន្ធជោគជ័យ!')
            return redirect(url_for('cars'))
        else:
            flash('អ៊ីម៉ែល ឬ ពាក្យសម្ងាត់មិនត្រឹមត្រូវ!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']
        cur = mysql.connection.cursor()
        try:
            cur.execute('INSERT INTO users (name, email, password, user_type) VALUES (%s, %s, %s, %s)', (name, email, password, user_type))
            user_id = cur.lastrowid  # យក id ថ្មី
            mysql.connection.commit()
            
            # Auto-login ក្រោយ register (ដើម្បីងាយស្រួល)
            session['logged_in'] = True
            session['user_id'] = user_id
            session['user_type'] = user_type
            session['name'] = name
            flash('ចុះឈ្មោះ និងចូលប្រព័ន្ធជោគជ័យ!')
            
            # Send welcome email
            body = f'<h1>ស្វាគមន៍ {name}!</h1><p>អ្នកបានចុះឈ្មោះជោគជ័យ។ ចូលប្រើនៅ <a href="http://localhost:5000/login">ទីនេះ</a>។</p>'
            send_email(email, 'ស្វាគមន៍មកកាន់ Car Rental System', body)
            
            return redirect(url_for('cars'))  # Redirect ទៅ cars ជំនួស login
        except Exception as e:
            flash(f'កំហុសក្នុងការចុះឈ្មោះ: {str(e)}')
        finally:
            cur.close()
    return render_template('register.html')

@app.route('/cars')
def cars():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('SELECT * FROM cars WHERE available = TRUE')
    cars_list = cur.fetchall()
    cur.close()
    return render_template('cars.html', cars=cars_list)

@app.route('/booking/<int:car_id>', methods=['GET', 'POST'])
def booking(car_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # Validate session user_id
    user_id = session.get('user_id')
    if not user_id or not isinstance(user_id, int):
        flash('Session មិនត្រឹមត្រូវ។ សូមចូលប្រព័ន្ធឡើងវិញ។')
        session.clear()
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
    car = cur.fetchone()
    if not car:
        flash('រថយន្តមិនមាន!')
        cur.close()
        return redirect(url_for('cars'))
    
    # Verify user exists (extra safety)
    cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
    if not cur.fetchone():
        flash('គណនីមិនត្រូវបានរកឃើញ។ សូមចូលប្រព័ន្ធឡើងវិញ។')
        cur.close()
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        # ពិនិត្យ end_date > start_date
        if end_date <= start_date:
            flash('ថ្ងៃបញ្ចប់ត្រូវតែធំជាងថ្ងៃចាប់ផ្តើម!')
            cur.close()
            return render_template('booking.html', car=car)
        
        # ពិនិត្យ availability (overlap)
        cur.execute('SELECT * FROM bookings WHERE car_id = %s AND status != "cancelled" AND (start_date <= %s AND end_date >= %s)', 
                    (car_id, end_date, start_date))
        overlap = cur.fetchone()
        if overlap:
            flash('រថយន្តមិនអាចកក់បានក្នុងថ្ងៃនេះ! សូមជ្រើសថ្ងៃផ្សេង។')
            cur.close()
            return render_template('booking.html', car=car)
        
        # បង្កើត booking
        try:
            cur.execute('INSERT INTO bookings (user_id, car_id, start_date, end_date, status) VALUES (%s, %s, %s, %s, "confirmed")', 
                        (user_id, car_id, start_date, end_date))
            booking_id = cur.lastrowid
            mysql.connection.commit()
            
            # ធ្វើឲ្យ car unavailable
            cur.execute('UPDATE cars SET available = FALSE WHERE id = %s', (car_id,))
            mysql.connection.commit()
        except Exception as e:
            flash(f'កំហុសក្នុងការកក់: {str(e)}')
            cur.close()
            return render_template('booking.html', car=car)
        
        cur.close()
        
        # Send email
        body = f'<h1>ការកក់បានបញ្ជាក់!</h1><p>រថយន្ត: {car["brand"]} {car["model"]}<br>ថ្ងៃចាប់ផ្តើម: {start_date}<br>ថ្ងៃបញ្ចប់: {end_date}</p>'
        send_email(session['name'], 'ការកក់រថយន្ត', body)
        
        flash('កក់ជោគជ័យ! បន្តទៅបង់ប្រាក់។')
        return redirect(url_for('payment', booking_id=booking_id))
    
    cur.close()
    return render_template('booking.html', car=car)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('SELECT b.*, c.price, DATEDIFF(b.end_date, b.start_date) as days FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.id = %s AND b.user_id = %s', 
                (booking_id, session['user_id']))
    booking = cur.fetchone()
    if not booking:
        flash('ការកក់មិនមាន!')
        cur.close()
        return redirect(url_for('cars'))
    
    total = booking['price'] * booking['days']
    
    if request.method == 'POST':
        method = request.form['method']
        transaction_id = request.form['transaction_id']
        # បង់ប្រាក់ (simulate)
        cur.execute('INSERT INTO payments (booking_id, amount, method, transaction_id, status) VALUES (%s, %s, %s, %s, "paid")', 
                    (booking_id, total, method, transaction_id))
        payment_id = cur.lastrowid
        cur.execute('INSERT INTO invoices (payment_id, total_amount) VALUES (%s, %s)', (payment_id, total))
        cur.execute('UPDATE bookings SET status = "confirmed" WHERE id = %s', (booking_id,))
        mysql.connection.commit()
        cur.close()
        
        flash('បង់ប្រាក់ជោគជ័យ!')
        return redirect(url_for('payment_receipt', payment_id=payment_id))
    
    cur.close()
    return render_template('payment.html', booking=booking, total=total)

@app.route('/payment_receipt/<int:payment_id>')
def payment_receipt(payment_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('''
        SELECT p.*, i.total_amount, b.start_date, c.brand, c.model 
        FROM payments p 
        JOIN invoices i ON p.id = i.payment_id 
        JOIN bookings b ON p.booking_id = b.id 
        JOIN cars c ON b.car_id = c.id 
        WHERE p.id = %s
    ''', (payment_id,))
    receipt = cur.fetchone()
    cur.close()
    if not receipt:
        flash('វិក្កយបត្រមិនមាន!')
        return redirect(url_for('dashboard'))
    return render_template('payment_receipt.html', receipt=receipt)

@app.route('/after_booking')
def after_booking():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('after_booking.html', start_date='ថ្ងៃកំណត់')  # អាច pass ពី session ឬ query

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if session['user_type'] not in ['admin', 'staff']:
        flash('អ្នកមិនមានសិទ្ធិចូល!')
        return redirect(url_for('cars'))
    
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute('''
        SELECT b.id, u.name as customer_name, CONCAT(c.brand, ' ', c.model) as car_model, b.status 
        FROM bookings b 
        JOIN users u ON b.user_id = u.id 
        JOIN cars c ON b.car_id = c.id 
        ORDER BY b.created_at DESC
    ''')
    bookings = cur.fetchall()
    cur.close()
    return render_template('dashboard.html', bookings=bookings)

@app.route('/logout')
def logout():
    session.clear()
    flash('ចាកចេញជោគជ័យ!')
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        init_db()  # បង្កើតតារាងនៅពេល run app
    app.run(debug=True)
