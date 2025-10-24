from flask import Flask, render_template, request, session, flash, redirect, url_for, make_response
from flask_mysqldb import MySQL
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
import MySQLdb.cursors
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_random_secret_key_1234567890')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'car_rental')
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mysql = MySQL(app)
mail = Mail(app)
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Index route
@app.route('/')
def index():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM cars WHERE status = 'Available' LIMIT 3")
        featured_cars = cursor.fetchall()
        cursor.close()
        exchange_rate = 4100  # USD to KHR
        return render_template('index.html', featured_cars=featured_cars, exchange_rate=exchange_rate, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return render_template('index.html', featured_cars=[], exchange_rate=4100, language=session.get('language', 'en'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            cursor.close()
            if user and check_password_hash(user['password'], password):
                session['loggedin'] = True
                session['id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['language'] = user['language']
                flash('{% if session.language == "km" %}ចូលគណនីជោគជ័យ{% else %}Logged in successfully{% endif %}', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('{% if session.language == "km" %}ឈ្មោះអ្នកប្រើ ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ{% else %}Invalid username or password{% endif %}', 'error')
        except Exception as e:
            flash(f'Error accessing database: {str(e)}', 'error')
    return render_template('login.html', language=session.get('language', 'en'))

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        language = request.form.get('language', 'en')
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE username = %s OR email = %s', (username, email))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('{% if session.language == "km" %}ឈ្មោះអ្នកប្រើ ឬអ៊ីមែលមានរួចហើយ{% else %}Username or email already exists{% endif %}', 'error')
            else:
                hashed_password = generate_password_hash(password)
                cursor.execute('INSERT INTO users (username, email, password, language) VALUES (%s, %s, %s, %s)', 
                              (username, email, hashed_password, language))
                mysql.connection.commit()
                flash('{% if session.language == "km" %}ចុះឈ្មោះជោគជ័យ{% else %}Registration successful{% endif %}', 'success')
                return redirect(url_for('login'))
            cursor.close()
        except Exception as e:
            flash(f'Error accessing database: {str(e)}', 'error')
    return render_template('register.html', language=session.get('language', 'en'))

# Forgot Password route
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        try:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.close()
            if user:
                token = serializer.dumps(email, salt='password-reset')
                reset_url = url_for('reset_password', token=token, _external=True)
                msg = Message('Password Reset Request', sender=app.config['MAIL_USERNAME'], recipients=[email])
                msg.body = f'Reset your password here: {reset_url}\nThis link expires in 1 hour.'
                mail.send(msg)
                flash('{% if session.language == "km" %}តំណភ្ជាប់កំណត់ពាក្យសម្ងាត់ឡើងវិញបានផ្ញើទៅអ៊ីមែល{% else %}Password reset link sent to your email{% endif %}', 'success')
            else:
                flash('{% if session.language == "km" %}អ៊ីមែលមិនមានក្នុងប្រព័ន្ធ{% else %}Email not found{% endif %}', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    return render_template('forgot_password.html', language=session.get('language', 'en'))

# Reset Password route
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except Exception:
        flash('{% if session.language == "km" %}តំណភ្ជាប់ផុតកំណត់ ឬមិនត្រឹមត្រូវ{% else %}Invalid or expired reset link{% endif %}', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form['password']
        try:
            hashed_password = generate_password_hash(password)
            cursor = mysql.connection.cursor()
            cursor.execute('UPDATE users SET password = %s WHERE email = %s', (hashed_password, email))
            mysql.connection.commit()
            cursor.close()
            flash('{% if session.language == "km" %}បានកំណត់ពាក្យសម្ងាត់ឡើងវិញជោគជ័យ{% else %}Password reset successfully{% endif %}', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error accessing database: {str(e)}', 'error')
    return render_template('reset_password.html', token=token, language=session.get('language', 'en'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        flash('{% if session.language == "km" %}សូមចូលគណនីជាមុន{% else %}Please log in first{% endif %}', 'error')
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if session['role'] == 'admin':
            cursor.execute('SELECT COUNT(*) AS user_count FROM users')
            user_count = cursor.fetchone()['user_count']
            cursor.execute('SELECT COUNT(*) AS car_count FROM cars')
            car_count = cursor.fetchone()['car_count']
            cursor.execute('SELECT COUNT(*) AS booking_count FROM bookings WHERE status = %s', ('Pending',))
            pending_bookings = cursor.fetchone()['booking_count']
            cursor.close()
            return render_template('dashboard.html', user_count=user_count, car_count=car_count, 
                                 pending_bookings=pending_bookings, role=session['role'], 
                                 language=session.get('language', 'en'))
        elif session['role'] == 'staff':
            cursor.execute('SELECT b.*, c.model, u.username FROM bookings b JOIN cars c ON b.car_id = c.id JOIN users u ON b.user_id = u.id WHERE b.status = %s', ('Pending',))
            pending_bookings = cursor.fetchall()
            cursor.close()
            return render_template('dashboard.html', pending_bookings=pending_bookings, role=session['role'], 
                                 language=session.get('language', 'en'))
        else:
            cursor.execute('SELECT b.*, c.model FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s', (session['id'],))
            user_bookings = cursor.fetchall()
            cursor.close()
            return render_template('dashboard.html', user_bookings=user_bookings, role=session['role'], 
                                 language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('index'))

# Profile route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'loggedin' not in session:
        flash('{% if session.language == "km" %}សូមចូលគណនីជាមុន{% else %}Please log in first{% endif %}', 'error')
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT id, username, email, role, loyalty_points, language FROM users WHERE id = %s', (session['id'],))
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            flash('{% if session.language == "km" %}រកមិនឃើញអ្នកប្រើ{% else %}User not found{% endif %}', 'error')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            language = request.form.get('language', 'en')
            if language in ['en', 'km']:
                cursor.execute('UPDATE users SET language = %s WHERE id = %s', (language, session['id']))
                mysql.connection.commit()
                session['language'] = language
                flash('{% if session.language == "km" %}បានធ្វើបច្ចុប្បន្នភាសាដោយជោគជ័យ{% else %}Language updated successfully{% endif %}', 'success')
            else:
                flash('{% if session.language == "km" %}ភាសាមិនត្រឹមត្រូវ{% else %}Invalid language{% endif %}', 'error')
            
            cursor.close()
            return redirect(url_for('profile'))
        
        cursor.close()
        return render_template('profile.html', user=user, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Cars route
@app.route('/cars')
def cars():
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM cars WHERE status = 'Available'")
        cars = cursor.fetchall()
        cursor.close()
        exchange_rate = 4100
        return render_template('cars.html', cars=cars, exchange_rate=exchange_rate, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return render_template('cars.html', cars=[], exchange_rate=4100, language=session.get('language', 'en'))

# Car Details route
@app.route('/car/<int:car_id>')
def car_details(car_id):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM cars WHERE id = %s', (car_id,))
        car = cursor.fetchone()
        cursor.close()
        if car:
            exchange_rate = 4100
            return render_template('car_details.html', car=car, exchange_rate=exchange_rate, language=session.get('language', 'en'))
        else:
            flash('{% if session.language == "km" %}រកមិនឃើញរថយន្ត{% else %}Car not found{% endif %}', 'error')
            return redirect(url_for('cars'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('cars'))

# Booking route
@app.route('/booking/<int:car_id>', methods=['GET', 'POST'])
def booking(car_id):
    if 'loggedin' not in session:
        flash('{% if session.language == "km" %}សូមចូលគណនីជាមុន{% else %}Please log in first{% endif %}', 'error')
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM cars WHERE id = %s AND status = %s', (car_id, 'Available'))
        car = cursor.fetchone()
        if not car:
            cursor.close()
            flash('{% if session.language == "km" %}រថយន្តមិនអាចជួលបាន{% else %}Car is not available{% endif %}', 'error')
            return redirect(url_for('cars'))
        
        if request.method == 'POST':
            start_date = request.form['start_date']
            end_date = request.form['end_date']
            pickup_location = request.form['pickup_location']
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            days = (end - start).days
            if days <= 0:
                flash('{% if session.language == "km" %}កាលបរិច្ឆេទមិនត្រឹមត្រូវ{% else %}Invalid date range{% endif %}', 'error')
            else:
                total_amount = days * car['price_per_day']
                cursor.execute('INSERT INTO bookings (user_id, car_id, start_date, end_date, pickup_location, total_amount) VALUES (%s, %s, %s, %s, %s, %s)', 
                              (session['id'], car_id, start_date, end_date, pickup_location, total_amount))
                cursor.execute('UPDATE cars SET status = %s WHERE id = %s', ('Booked', car_id))
                mysql.connection.commit()
                cursor.close()
                flash('{% if session.language == "km" %}កក់រថយន្តជោគជ័យ{% else %}Booking successful{% endif %}', 'success')
                return redirect(url_for('booking_history'))
        cursor.close()
        exchange_rate = 4100
        return render_template('booking.html', car=car, exchange_rate=exchange_rate, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('cars'))

# Booking History route
@app.route('/booking_history')
def booking_history():
    if 'loggedin' not in session:
        flash('{% if session.language == "km" %}សូមចូលគណនីជាមុន{% else %}Please log in first{% endif %}', 'error')
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT b.*, c.model FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s', (session['id'],))
        bookings = cursor.fetchall()
        cursor.close()
        exchange_rate = 4100
        return render_template('booking_history.html', bookings=bookings, exchange_rate=exchange_rate, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Payment route
@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'loggedin' not in session:
        flash('{% if session.language == "km" %}សូមចូលគណនីជាមុន{% else %}Please log in first{% endif %}', 'error')
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT b.*, c.model FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.id = %s AND b.user_id = %s', (booking_id, session['id']))
        booking = cursor.fetchone()
        if not booking:
            cursor.close()
            flash('{% if session.language == "km" %}រកមិនឃើញការកក់{% else %}Booking not found{% endif %}', 'error')
            return redirect(url_for('booking_history'))
        
        if request.method == 'POST':
            method = request.form['payment_method']
            cursor.execute('INSERT INTO payments (booking_id, amount, method, status) VALUES (%s, %s, %s, %s)', 
                          (booking_id, booking['total_amount'], method, 'Completed'))
            cursor.execute('UPDATE bookings SET status = %s WHERE id = %s', ('Confirmed', booking_id))
            mysql.connection.commit()
            
            cursor.execute('SELECT email FROM users WHERE id = %s', (session['id'],))
            user = cursor.fetchone()
            msg = Message('Payment Receipt', sender=app.config['MAIL_USERNAME'], recipients=[user['email']])
            msg.body = f'Payment for booking ID {booking_id} of {booking["model"]} completed successfully. Amount: ${booking["total_amount"]}.'
            mail.send(msg)
            
            cursor.close()
            flash('{% if session.language == "km" %}ការទូទាត់ជោគជ័យ{% else %}Payment successful{% endif %}', 'success')
            return redirect(url_for('payment_receipt', booking_id=booking_id))
        
        cursor.close()
        exchange_rate = 4100
        return render_template('payment.html', booking=booking, exchange_rate=exchange_rate, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('booking_history'))

# Payment Receipt route
@app.route('/payment_receipt/<int:booking_id>')
def payment_receipt(booking_id):
    if 'loggedin' not in session:
        flash('{% if session.language == "km" %}សូមចូលគណនីជាមុន{% else %}Please log in first{% endif %}', 'error')
        return redirect(url_for('login'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT b.*, c.model, p.method, p.created_at FROM bookings b JOIN cars c ON b.car_id = c.id JOIN payments p ON b.id = p.booking_id WHERE b.id = %s AND b.user_id = %s', 
                      (booking_id, session['id']))
        receipt = cursor.fetchone()
        cursor.close()
        if receipt:
            exchange_rate = 4100
            return render_template('payment_receipt.html', receipt=receipt, exchange_rate=exchange_rate, language=session.get('language', 'en'))
        else:
            flash('{% if session.language == "km" %}រកមិនឃើញបង្កាន់ដៃ{% else %}Receipt not found{% endif %}', 'error')
            return redirect(url_for('booking_history'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('booking_history'))

# Manage Cars route (Admin only)
@app.route('/manage_cars', methods=['GET', 'POST'])
def manage_cars():
    if 'loggedin' not in session or session['role'] != 'admin':
        flash('{% if session.language == "km" %}តម្រូវឲ្យជាអ្នកគ្រប់គ្រង{% else %}Admin access required{% endif %}', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            model = request.form['model']
            price_per_day = float(request.form['price_per_day'])
            status = request.form['status']
            image_path = request.form.get('image_path', 'images/placeholder_car.jpg')
            cursor.execute('INSERT INTO cars (model, price_per_day, status, image_path) VALUES (%s, %s, %s, %s)', 
                          (model, price_per_day, status, image_path))
            mysql.connection.commit()
            flash('{% if session.language == "km" %}បានបន្ថែមរថយន្តជោគជ័យ{% else %}Car added successfully{% endif %}', 'success')
        
        cursor.execute('SELECT * FROM cars')
        cars = cursor.fetchall()
        cursor.close()
        return render_template('manage_cars.html', cars=cars, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Manage Users route (Admin only)
@app.route('/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'loggedin' not in session or session['role'] != 'admin':
        flash('{% if session.language == "km" %}តម្រូវឲ្យជាអ្នកគ្រប់គ្រង{% else %}Admin access required{% endif %}', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            user_id = request.form['user_id']
            role = request.form['role']
            cursor.execute('UPDATE users SET role = %s WHERE id = %s', (role, user_id))
            mysql.connection.commit()
            flash('{% if session.language == "km" %}បានធ្វើបច្ចុប្បន្នភាពអ្នកប្រើជោគជ័យ{% else %}User updated successfully{% endif %}', 'success')
        
        cursor.execute('SELECT id, username, email, role, loyalty_points FROM users')
        users = cursor.fetchall()
        cursor.close()
        return render_template('manage_users.html', users=users, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Manage Handovers route (Staff only)
@app.route('/manage_handovers', methods=['GET', 'POST'])
def manage_handovers():
    if 'loggedin' not in session or session['role'] != 'staff':
        flash('{% if session.language == "km" %}តម្រូវឲ្យជាបុគ្គលិក{% else %}Staff access required{% endif %}', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        if request.method == 'POST':
            booking_id = request.form['booking_id']
            action = request.form['action']
            if action in ['Confirmed', 'Completed', 'Cancelled']:
                cursor.execute('UPDATE bookings SET status = %s WHERE id = %s', (action, booking_id))
                mysql.connection.commit()
                if action == 'Completed':
                    cursor.execute('UPDATE cars SET status = %s WHERE id = (SELECT car_id FROM bookings WHERE id = %s)', ('Available', booking_id))
                    mysql.connection.commit()
                flash('{% if session.language == "km" %}បានធ្វើបច្ចុប្បន្នភាពការកក់ជោគជ័យ{% else %}Booking updated successfully{% endif %}', 'success')
        
        cursor.execute('SELECT b.*, c.model, u.username FROM bookings b JOIN cars c ON b.car_id = c.id JOIN users u ON b.user_id = u.id WHERE b.status IN (%s, %s)', 
                      ('Pending', 'Confirmed'))
        bookings = cursor.fetchall()
        cursor.close()
        return render_template('manage_handovers.html', bookings=bookings, language=session.get('language', 'en'))
    except Exception as e:
        flash(f'Error accessing database: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# Logout route
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    session.pop('role', None)
    session.pop('language', None)
    flash('{% if session.language == "km" %}បានចាកចេញជោគជ័យ{% else %}Logged out successfully{% endif %}', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)