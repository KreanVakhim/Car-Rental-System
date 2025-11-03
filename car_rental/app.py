from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory
)
from datetime import datetime, date, timedelta
import os
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
from jinja2 import Environment

app = Flask(__name__)
app.secret_key = 'car_rental_kh_2025_secret'

# Extend Jinja2 environment with a custom date filter
def date_filter(value, format='%B %d, %Y'):
    if value is None:
        return ""
    return value.strftime(format)

app.jinja_env.filters['date'] = date_filter

# ------------------- UPLOAD CONFIG -------------------
UPLOAD_FOLDER = 'static/car_images'
DAMAGE_FOLDER = 'static/damage_images'
PROFILE_FOLDER = 'static/img'
PAYMENT_IMAGES_FOLDER = 'static/payment_images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DAMAGE_FOLDER'] = DAMAGE_FOLDER
app.config['PROFILE_FOLDER'] = PROFILE_FOLDER
app.config['PAYMENT_IMAGES_FOLDER'] = PAYMENT_IMAGES_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DAMAGE_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)
os.makedirs(PAYMENT_IMAGES_FOLDER, exist_ok=True)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

@app.route('/car_images/<filename>')
def uploaded_file(filename):
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    print(f"Attempting to serve: {filename} from {full_path}")
    if not os.path.exists(full_path):
        print(f"File not found at: {full_path}")
        # Fallback to default car image
        default_path = os.path.join(app.config['UPLOAD_FOLDER'], 'default_car.png')
        if os.path.exists(default_path):
            return send_from_directory(app.config['UPLOAD_FOLDER'], 'default_car.png')
        return "Image not found", 404
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/damage_images/<filename>')
def damage_image(filename):
    return send_from_directory(DAMAGE_FOLDER, filename)

@app.route('/img/<filename>')
def profile_pic(filename):
    return send_from_directory(PROFILE_FOLDER, filename)

@app.route('/payment_images/<filename>')
def payment_image(filename):
    return send_from_directory(PAYMENT_IMAGES_FOLDER, filename)

# ------------------- MySQL -------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'demo_classa'
}

def get_db():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print(f"DB error: {e}")
        return None

def query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetchone: return cursor.fetchone()
        if fetchall: return cursor.fetchall()
    except Error as e:
        print(f"Query error: {e}")
        if commit: conn.rollback()
    finally:
        cursor.close()
        conn.close()

# ------------------- DB INIT -------------------
def init_db():
    conn = get_db()
    if not conn: return
    cur = conn.cursor(dictionary=True)

    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            password VARCHAR(100) NOT NULL,
            role ENUM('customer','staff','admin') DEFAULT 'customer',
            profile_pic VARCHAR(255) DEFAULT 'default.png',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            year INT NOT NULL,
            price_day DECIMAL(10,2) NOT NULL,
            seats INT NOT NULL,
            image VARCHAR(255) DEFAULT 'default_car.png',
            available BOOLEAN DEFAULT TRUE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            car_id INT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            discount DECIMAL(10,2) DEFAULT 0,
            promo_code VARCHAR(20),
            status ENUM('pending','confirmed','active','completed','cancelled') DEFAULT 'pending',
            payment_proof VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (car_id) REFERENCES cars(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS promotions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            discount_pct INT NOT NULL,
            valid_from DATE NOT NULL,
            valid_to DATE NOT NULL
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS damage_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            car_id INT NOT NULL,
            staff_id INT NOT NULL,
            description TEXT NOT NULL,
            image VARCHAR(255),
            status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
            reported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_id) REFERENCES cars(id),
            FOREIGN KEY (staff_id) REFERENCES users(id)
        )
    ''')

    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()['c'] == 0:
        # Insert users with predefined profile pictures
        cur.executemany(
            "INSERT INTO users (name,email,phone,password,role,profile_pic) VALUES (%s,%s,%s,%s,%s,%s)",
            [
                ('Admin KH', 'admin@carrental.com', '012345678', 'admin123', 'admin', 'user1.png'),
                ('Staff One', 'staff@carrental.com', '098765432', 'staff123', 'staff', 'staff1.png'),
                ('Staff Two', 'staff2@carrental.com', '098765433', 'staff123', 'staff', 'staff2.png'),
                ('Sokha', 'sokha@test.com', '011223344', 'cust123', 'customer', 'user2.png')
            ]
        )
        # Insert cars with predefined images
        cur.executemany(
            "INSERT INTO cars (brand, model, year, price_day, seats, image) VALUES (%s,%s,%s,%s,%s,%s)",
            [
                ('Toyota', 'Camry', 2023, 50.00, 5, 'car1.png'),
                ('Honda', 'Civic', 2022, 45.00, 5, 'car2.png')
            ]
        )
        today = date.today()
        cur.executemany(
            "INSERT IGNORE INTO promotions (code,discount_pct,valid_from,valid_to) VALUES (%s,%s,%s,%s)",
            [('WELCOME20', 20, today, today + timedelta(days=30))]
        )
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ------------------- JINJA HELPERS -------------------
@app.context_processor
def inject_helpers():
    pic = session.get('profile_pic')
    if not pic or not os.path.exists(os.path.join(PROFILE_FOLDER, pic)):
        pic = 'default.png'
    return dict(
        today=date.today(),
        current_year=date.today().year,
        user_pic=url_for('profile_pic', filename=pic)
    )

# ------------------- ROUTES -------------------
@app.route('/')
def index():
    cars = query("SELECT * FROM cars WHERE available=TRUE LIMIT 3", fetchall=True) or []
    return render_template('index.html', cars=cars)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = query("SELECT * FROM users WHERE email=%s", (request.form['email'],), fetchone=True)
        if user and user['password'] == request.form['password']:
            session.update({
                'user_id': user['id'],
                'role': user['role'],
                'user_name': user['name'],
                'profile_pic': user.get('profile_pic') or 'default.png'
            })
            flash('Login successful!', 'success')
            return redirect('/')
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if query("SELECT id FROM users WHERE email=%s", (request.form['email'],), fetchone=True):
            flash('Email already taken', 'danger')
        else:
            query("INSERT INTO users (name,email,phone,password,role,profile_pic) VALUES (%s,%s,%s,%s,'customer',%s)",
                  (request.form['name'], request.form['email'], request.form['phone'], request.form['password'], 'user1.png'), commit=True)
            flash('Registered! Please login.', 'success')
            return redirect('/login')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect('/')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please login to view profile', 'warning')
        return redirect('/login')
    
    user = query("SELECT * FROM users WHERE id=%s", (session['user_id'],), fetchone=True)
    current_pic = user.get('profile_pic') or 'default.png'
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        
        filename = current_pic
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            file = request.files['profile_pic']
            if allowed_file(file.filename):
                if filename != 'default.png':
                    old_path = os.path.join(PROFILE_FOLDER, filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"user_{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                file.save(os.path.join(PROFILE_FOLDER, filename))
            else:
                flash('Invalid file type. Use PNG, JPG, JPEG, GIF.', 'danger')
                filename = current_pic

        existing = query("SELECT id FROM users WHERE email=%s AND id!=%s", (email, session['user_id']), fetchone=True)
        if existing:
            flash('Email already in use', 'danger')
        else:
            query("UPDATE users SET name=%s, email=%s, phone=%s, profile_pic=%s WHERE id=%s",
                  (name, email, phone, filename, session['user_id']), commit=True)
            session.update({'user_name': name, 'profile_pic': filename})
            flash('Profile updated successfully!', 'success')
            return redirect('/profile')
    
    return render_template('profile.html', user=user)

@app.route('/cars')
def cars_list():
    cars = query("SELECT * FROM cars WHERE available=TRUE", fetchall=True) or []
    return render_template('cars.html', cars=cars)

@app.route('/car/<int:cid>')
def car_detail(cid):
    car = query("SELECT * FROM cars WHERE id=%s", (cid,), fetchone=True)
    if not car: return redirect('/cars')
    return render_template('car_detail.html', car=car)

@app.route('/book/<int:cid>', methods=['GET', 'POST'])
def book_car(cid):
    if session.get('role') != 'customer':
        flash('Login as customer', 'warning')
        return redirect('/login')
    car = query("SELECT * FROM cars WHERE id=%s AND available=TRUE", (cid,), fetchone=True)
    if not car: return redirect('/cars')

    if request.method == 'POST':
        start = request.form['start_date']
        end = request.form['end_date']
        try:
            s = datetime.strptime(start, '%Y-%m-%d').date()
            e = datetime.strptime(end, '%Y-%m-%d').date()
        except:
            flash('Invalid date format', 'danger')
            return redirect(url_for('book_car', cid=cid))
        if s < date.today() or e <= s:
            flash('Invalid date range', 'danger')
            return redirect(url_for('book_car', cid=cid))

        overlap = query("SELECT id FROM bookings WHERE car_id=%s AND status IN ('pending','confirmed','active') AND NOT (end_date <= %s OR start_date >= %s)", (cid, start, end), fetchone=True)
        if overlap:
            flash('Car already booked', 'danger')
            return redirect(url_for('book_car', cid=cid))

        days = (e - s).days
        total = car['price_day'] * days
        code = request.form.get('promo_code', '').strip().upper()
        discount = 0
        promo_msg = ""

        if code:
            promo = query("SELECT * FROM promotions WHERE code=%s AND %s BETWEEN valid_from AND valid_to", (code, date.today()), fetchone=True)
            if promo:
                discount = total * promo['discount_pct'] / 100
                total -= discount
                promo_msg = f"Promo {code} applied!"

        bid = query("INSERT INTO bookings (user_id,car_id,start_date,end_date,total,discount,promo_code,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')",
                    (session['user_id'], cid, start, end, round(total,2), round(discount,2), code if discount else None), commit=True)
        query("UPDATE cars SET available=FALSE WHERE id=%s", (cid,), commit=True)
        flash(f'Booking created – ${total:.2f}. {promo_msg}', 'success')
        return redirect(url_for('payment', booking_id=bid))

    promos = query("SELECT * FROM promotions WHERE valid_to>=%s", (date.today(),), fetchall=True) or []
    return render_template('book.html', car=car, min_date=date.today().strftime('%Y-%m-%d'), promotions=promos)

@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session: return redirect('/login')
    raw = query("SELECT b.*, c.brand, c.model, c.image FROM bookings b JOIN cars c ON b.car_id=c.id WHERE b.user_id=%s ORDER BY b.created_at DESC", (session['user_id'],), fetchall=True) or []
    for b in raw:
        start = b['start_date']
        end = b['end_date']
        if isinstance(start, str): start = datetime.strptime(start, '%Y-%m-%d').date()
        if isinstance(end, str): end = datetime.strptime(end, '%Y-%m-%d').date()
        b['rental_days'] = (end - start).days
    return render_template('my_bookings.html', bookings=raw)

@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    if 'user_id' not in session:
        flash('Please login to cancel a booking', 'warning')
        return redirect('/login')
    
    booking = query("SELECT * FROM bookings WHERE id=%s AND user_id=%s", (booking_id, session['user_id']), fetchone=True)
    if not booking:
        flash('Booking not found or not authorized', 'danger')
        return redirect('/my_bookings')

    current_date = date.today()
    start_date = datetime.strptime(booking['start_date'], '%Y-%m-%d').date()
    time_to_start = (start_date - current_date).days

    # Cancellation rules
    if booking['status'] in ['pending', 'confirmed']:
        # Allow cancellation up to 24 hours before start date
        if time_to_start > 1:
            query("UPDATE bookings SET status='cancelled' WHERE id=%s", (booking_id,), commit=True)
            query("UPDATE cars SET available=TRUE WHERE id=%s", (booking['car_id'],), commit=True)
            flash('Booking cancelled successfully!', 'success')
        else:
            flash('Cannot cancel: Booking starts within 24 hours', 'danger')
    elif booking['status'] == 'active':
        flash('Cannot cancel: Booking is currently active', 'danger')
    elif booking['status'] in ['completed', 'cancelled']:
        flash('Booking is already completed or cancelled', 'danger')
    else:
        flash('Cannot cancel: Invalid booking status', 'danger')

    return redirect('/my_bookings')

@app.route('/payment/<int:booking_id>')
def payment(booking_id):
    if 'user_id' not in session: return redirect('/login')
    b = query("SELECT b.*, c.brand, c.model, c.image FROM bookings b JOIN cars c ON b.car_id=c.id WHERE b.id=%s AND b.user_id=%s", (booking_id, session['user_id']), fetchone=True)
    if not b: return redirect('/my_bookings')
    return render_template('payment.html', booking=b, is_qr=False)

@app.route('/QR_code_payment/<int:booking_id>')
def qr_payment(booking_id):
    if 'user_id' not in session: return redirect('/login')
    b = query("SELECT b.*, c.brand, c.model, c.image FROM bookings b JOIN cars c ON b.car_id=c.id WHERE b.id=%s AND b.user_id=%s", (booking_id, session['user_id']), fetchone=True)
    if not b: return redirect('/my_bookings')
    return render_template('QR_code_payment.html', booking=b)

@app.route('/confirm_payment/<int:booking_id>')
def confirm_payment(booking_id):
    if 'user_id' not in session: return redirect('/login')
    query("UPDATE bookings SET status='confirmed' WHERE id=%s AND user_id=%s", (booking_id, session['user_id']), commit=True)
    flash('Payment confirmed!', 'success')
    return redirect('/my_bookings')

@app.route('/upload_payment_proof/<int:booking_id>', methods=['POST'])
def upload_payment_proof(booking_id):
    if 'user_id' not in session:
        flash('Please login to upload payment proof', 'warning')
        return redirect('/login')
    
    booking = query("SELECT * FROM bookings WHERE id=%s AND user_id=%s", (booking_id, session['user_id']), fetchone=True)
    if not booking:
        flash('Booking not found', 'danger')
        return redirect('/my_bookings')

    if 'payment_proof' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('qr_payment', booking_id=booking_id))

    file = request.files['payment_proof']
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"proof_{booking_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
        file.save(os.path.join(app.config['PAYMENT_IMAGES_FOLDER'], filename))
        
        # Update booking with payment proof reference
        query("UPDATE bookings SET payment_proof=%s WHERE id=%s", (filename, booking_id), commit=True)
        flash('Payment proof uploaded successfully! Awaiting verification.', 'success')
    else:
        flash('Invalid file type. Use PNG, JPG, or JPEG.', 'danger')
        return redirect(url_for('qr_payment', booking_id=booking_id))

    return redirect(url_for('my_bookings'))

@app.route('/invoice/<int:booking_id>')
def invoice(booking_id):
    if 'user_id' not in session: return redirect('/login')
    b = query("SELECT b.*, c.brand, c.model, c.year, u.name, u.email, u.phone FROM bookings b JOIN cars c ON b.car_id=c.id JOIN users u ON b.user_id=u.id WHERE b.id=%s AND b.user_id=%s", (booking_id, session['user_id']), fetchone=True)
    if not b: return redirect('/my_bookings')
    return render_template('invoice.html', booking=b)

@app.route('/promotions')
def promotions():
    promos = query("SELECT * FROM promotions WHERE valid_to >= %s ORDER BY valid_to DESC", (date.today(),), fetchall=True) or []
    return render_template('promotions.html', promotions=promos)

# ------------------- ADMIN -------------------
@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin': 
        flash('Access denied', 'danger')
        return redirect('/')
    
    users_count = query("SELECT COUNT(*) as c FROM users", fetchone=True)['c']
    cars_count = query("SELECT COUNT(*) as c FROM cars", fetchone=True)['c']
    bookings_count = query("SELECT COUNT(*) as c FROM bookings", fetchone=True)['c']
    revenue = query("SELECT COALESCE(SUM(total), 0) as r FROM bookings WHERE status='completed'", fetchone=True)['r']
    recent_bookings = query("""
        SELECT b.*, c.brand, c.model, u.name 
        FROM bookings b 
        JOIN cars c ON b.car_id=c.id 
        JOIN users u ON b.user_id=u.id 
        ORDER BY b.created_at DESC LIMIT 5
    """, fetchall=True) or []
    
    return render_template('admin/admin_dashboard.html',
                          users_count=users_count,
                          cars_count=cars_count,
                          bookings_count=bookings_count,
                          revenue=revenue,
                          recent_bookings=recent_bookings)

@app.route('/admin/manage_cars')
def manage_cars():
    if session.get('role') != 'admin': return redirect('/')
    cars = query("SELECT * FROM cars", fetchall=True) or []
    return render_template('admin/manage_cars.html', cars=cars)

@app.route('/admin/add_car', methods=['GET', 'POST'])
def add_car():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect('/')
    
    if request.method == 'POST':
        brand = request.form['brand'].strip()
        model = request.form['model'].strip()
        year = request.form['year']
        price_day = request.form['price_day']
        seats = request.form['seats']

        # Validation
        if not all([brand, model, year, price_day, seats]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('add_car'))

        try:
            year = int(year)
            price_day = float(price_day)
            seats = int(seats)
        except ValueError:
            flash('Year, price, and seats must be valid numbers.', 'danger')
            return redirect(url_for('add_car'))

        if year > date.today().year or year < 1900:
            flash('Year must be between 1900 and the current year (2025).', 'danger')
            return redirect(url_for('add_car'))

        if price_day <= 0:
            flash('Price per day must be greater than zero.', 'danger')
            return redirect(url_for('add_car'))

        if seats <= 0:
            flash('Number of seats must be greater than zero.', 'danger')
            return redirect(url_for('add_car'))

        # Use predefined car image names sequentially
        cur_car_count = query("SELECT COUNT(*) as c FROM cars", fetchone=True)['c']
        filename = f'car{cur_car_count + 1}.png' if cur_car_count < 2 else 'default_car.png'  # Limit to car1, car2 for now
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                if file.content_length and file.content_length > 2 * 1024 * 1024:  # 2MB limit
                    flash('Image size must be less than 2MB.', 'danger')
                    return redirect(url_for('add_car'))
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = os.path.normcase(secure_filename(f"car_{brand}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"))
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                print(f"Image saved at: {os.path.join(app.config['UPLOAD_FOLDER'], filename)}")
            elif file and not allowed_file(file.filename):
                flash('Invalid file type. Use PNG, JPG, JPEG, GIF.', 'danger')
                return redirect(url_for('add_car'))

        query("INSERT INTO cars (brand, model, year, price_day, seats, image) VALUES (%s, %s, %s, %s, %s, %s)",
              (brand, model, year, price_day, seats, filename), commit=True)
        flash('Car added successfully!', 'success')
        return redirect(url_for('manage_cars'))

    return render_template('admin/add_car.html', current_year=date.today().year)

@app.route('/admin/edit_car/<int:cid>', methods=['GET', 'POST'])
def edit_car(cid):
    if session.get('role') != 'admin': return redirect('/')
    car = query("SELECT * FROM cars WHERE id=%s", (cid,), fetchone=True)
    if not car: return redirect('/admin/manage_cars')

    if request.method == 'POST':
        filename = car['image']
        if 'image' in request.files and request.files['image'].filename:
            img = request.files['image']
            if allowed_file(img.filename):
                if filename and filename != 'default_car.png':
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                ext = img.filename.rsplit('.', 1)[1].lower()
                filename = os.path.normcase(secure_filename(f"car_{request.form['brand']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"))
                img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        query("UPDATE cars SET brand=%s, model=%s, year=%s, price_day=%s, seats=%s, image=%s WHERE id=%s",
              (request.form['brand'], request.form['model'], request.form['year'], request.form['price_day'], request.form['seats'], filename, cid), commit=True)
        flash('Car updated!', 'success')
        return redirect('/admin/manage_cars')

    return render_template('admin/edit_car.html', car=car, current_year=date.today().year)

@app.route('/admin/delete_car/<int:cid>')
def delete_car(cid):
    if session.get('role') != 'admin': return redirect('/')
    car = query("SELECT image FROM cars WHERE id=%s", (cid,), fetchone=True)
    if car and car['image'] and car['image'] != 'default_car.png':
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], car['image'])
        if os.path.exists(img_path):
            os.remove(img_path)
    query("DELETE FROM cars WHERE id=%s", (cid,), commit=True)
    flash('Car deleted!', 'success')
    return redirect('/admin/manage_cars')

@app.route('/admin/manage_promotions')
def manage_promotions():
    if session.get('role') != 'admin': return redirect('/')
    promos = query("SELECT * FROM promotions ORDER BY valid_to DESC", fetchall=True) or []
    return render_template('admin/manage_promotions.html', promotions=promos)

@app.route('/admin/add_promo', methods=['GET', 'POST'])
def add_promo():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        code = request.form['code'].upper()
        if query("SELECT id FROM promotions WHERE code=%s", (code,), fetchone=True):
            flash('Code exists', 'danger')
        else:
            query("INSERT INTO promotions (code,discount_pct,valid_from,valid_to) VALUES (%s,%s,%s,%s)",
                  (code, request.form['discount_pct'], request.form['valid_from'], request.form['valid_to']), commit=True)
            flash('Promotion added!', 'success')
            return redirect('/admin/manage_promotions')
    return render_template('admin/add_promo.html')

@app.route('/admin/manage_users')
def manage_users():
    if session.get('role') != 'admin': return redirect('/')
    users = query("SELECT * FROM users", fetchall=True) or []
    return render_template('admin/manage_users.html', users=users)

@app.route('/admin/add_user', methods=['GET', 'POST'])
def add_user():
    if session.get('role') != 'admin': return redirect('/')
    if request.method == 'POST':
        query("INSERT INTO users (name,email,phone,password,role,profile_pic) VALUES (%s,%s,%s,%s,%s,%s)",
              (request.form['name'], request.form['email'], request.form['phone'], request.form['password'], request.form['role'], 'user1.png'), commit=True)
        flash('User added', 'success')
        return redirect('/admin/manage_users')
    return render_template('admin/add_user.html')

@app.route('/admin/add_staff', methods=['GET', 'POST'])
def add_staff():
    if session.get('role') != 'admin':
        flash('Access denied', 'danger')
        return redirect('/')
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        
        if query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True):
            flash('Email already in use', 'danger')
        else:
            query("INSERT INTO users (name, email, phone, password, role, profile_pic) VALUES (%s, %s, %s, %s, 'staff', %s)",
                  (name, email, phone, password, 'staff1.png'), commit=True)
            flash('Staff added successfully!', 'success')
            return redirect('/admin/manage_users')
    
    return render_template('admin/add_staff.html')

@app.route('/admin/edit_user/<int:uid>', methods=['GET', 'POST'])
def edit_user(uid):
    if session.get('role') != 'admin': return redirect('/')
    user = query("SELECT * FROM users WHERE id=%s", (uid,), fetchone=True)
    if not user: return redirect('/admin/manage_users')

    if request.method == 'POST':
        query("UPDATE users SET name=%s, email=%s, phone=%s, role=%s, profile_pic=%s WHERE id=%s",
              (request.form['name'], request.form['email'], request.form['phone'], request.form['role'], request.form['profile_pic'] or 'default.png', uid), commit=True)
        flash('User updated', 'success')
        return redirect('/admin/manage_users')
    return render_template('admin/edit_user.html', user=user)

@app.route('/admin/confirm_delete_user/<int:uid>')
def confirm_delete_user(uid):
    if session.get('role') != 'admin': return redirect('/')
    user = query("SELECT * FROM users WHERE id=%s", (uid,), fetchone=True)
    if not user: return redirect('/admin/manage_users')
    return render_template('admin/confirm_delete_user.html', user=user)

@app.route('/admin/delete_user/<int:uid>')
def delete_user(uid):
    if session.get('role') != 'admin': return redirect('/')
    query("DELETE FROM users WHERE id=%s", (uid,), commit=True)
    flash('User deleted', 'success')
    return redirect('/admin/manage_users')

@app.route('/admin/manage_bookings')
def manage_bookings():
    if session.get('role') != 'admin':
        flash('Admin only!', 'danger')
        return redirect('/')
    
    bookings = query("""
        SELECT b.*, c.brand, c.model, u.name AS customer_name
        FROM bookings b 
        JOIN cars c ON b.car_id = c.id 
        JOIN users u ON b.user_id = u.id 
        ORDER BY b.created_at DESC
    """, fetchall=True) or []
    
    return render_template('admin/manage_bookings.html', bookings=bookings)

@app.route('/admin/update_booking_status/<int:bid>/<string:status>', methods=['POST'])
def update_booking_status(bid, status):
    if session.get('role') != 'admin':
        flash('Admin only!', 'danger')
        return redirect('/')
    
    valid_statuses = ['pending', 'confirmed', 'active', 'completed', 'cancelled']
    if status not in valid_statuses:
        flash('Invalid status', 'danger')
        return redirect('/admin/manage_bookings')
    
    # Get current booking
    booking = query("SELECT * FROM bookings WHERE id=%s", (bid,), fetchone=True)
    if not booking:
        flash('Booking not found', 'danger')
        return redirect('/admin/manage_bookings')
    
    # Update status
    query("UPDATE bookings SET status=%s WHERE id=%s", (status, bid), commit=True)
    
    # Handle car availability
    car_id = booking['car_id']
    if status in ['completed', 'cancelled']:
        query("UPDATE cars SET available=TRUE WHERE id=%s", (car_id,), commit=True)
    elif status in ['pending', 'confirmed', 'active']:
        query("UPDATE cars SET available=FALSE WHERE id=%s", (car_id,), commit=True)
    
    flash(f'Booking {bid} status updated to {status}!', 'success')
    return redirect('/admin/manage_bookings')

@app.route('/admin/damage_reports')
def damage_reports():
    if session.get('role') != 'admin':
        flash('Admin only!', 'danger')
        return redirect('/')
    
    reports = query("""
        SELECT dr.*, c.brand, c.model, u.name AS staff_name
        FROM damage_reports dr
        JOIN cars c ON dr.car_id = c.id
        JOIN users u ON dr.staff_id = u.id
        ORDER BY dr.reported_at DESC
    """, fetchall=True) or []
    
    return render_template('admin/damage_reports.html', reports=reports)

@app.route('/admin/review_damage/<int:report_id>/<string:action>', methods=['POST'])
def review_damage(report_id, action):
    if session.get('role') != 'admin':
        flash('Admin only!', 'danger')
        return redirect('/')
    
    report = query("SELECT * FROM damage_reports WHERE id=%s", (report_id,), fetchone=True)
    if not report:
        flash('Damage report not found', 'danger')
        return redirect('/admin/damage_reports')
    
    if action not in ['approve', 'reject']:
        flash('Invalid action', 'danger')
        return redirect('/admin/damage_reports')
    
    new_status = 'approved' if action == 'approve' else 'rejected'
    query("UPDATE damage_reports SET status=%s WHERE id=%s", (new_status, report_id), commit=True)
    flash(f'Damage report {report_id} {new_status} successfully!', 'success')
    return redirect('/admin/damage_reports')

# ------------------- STAFF -------------------
@app.route('/staff')
def staff_dashboard():
    if session.get('role') != 'staff': return redirect('/')
    
    # Dashboard stats
    pending_checkins = query("SELECT COUNT(*) as c FROM bookings WHERE status='confirmed'", fetchone=True)['c'] or 0
    active_rentals = query("SELECT b.*, c.brand, c.model FROM bookings b JOIN cars c ON b.car_id=c.id WHERE b.status='active'", fetchall=True) or []
    damage_count = query("SELECT COUNT(*) as c FROM damage_reports WHERE staff_id=%s", (session['user_id'],), fetchone=True)['c'] or 0
    today_returns = query("SELECT b.*, c.brand, c.model FROM bookings b JOIN cars c ON b.car_id=c.id WHERE b.status='completed' AND b.end_date=%s", (date.today(),), fetchall=True) or []
    recent_checkins = query("""
        SELECT b.id, b.start_date, u.name AS customer_name
        FROM bookings b JOIN users u ON b.user_id = u.id
        WHERE b.status='confirmed' ORDER BY b.start_date DESC LIMIT 5
    """, fetchall=True) or []
    damaged_cars = query("""
        SELECT c.id, c.brand, c.model
        FROM cars c JOIN damage_reports dr ON c.id = dr.car_id
        WHERE dr.status='pending' GROUP BY c.id, c.brand, c.model
    """, fetchall=True) or []

    return render_template('staff/staff_dashboard.html',
                          pending_checkins=pending_checkins,
                          active_rentals=active_rentals,
                          damage_count=damage_count,
                          today_returns=today_returns,
                          recent_checkins=recent_checkins,
                          damaged_cars=damaged_cars)

@app.route('/staff/report_damage/<int:cid>', methods=['GET', 'POST'])
def report_damage(cid):
    if session.get('role') != 'staff':
        flash('Access denied! Staff only.', 'danger')
        return redirect('/')
    
    car = query("SELECT * FROM cars WHERE id=%s", (cid,), fetchone=True)
    if not car:
        flash('Car not found.', 'danger')
        return redirect('/staff')

    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        if not description:
            flash('Description is required.', 'danger')
            return redirect(url_for('report_damage', cid=cid))

        filename = None
        if 'image' in request.files and request.files['image'].filename:
            img = request.files['image']
            if allowed_file(img.filename):
                ext = img.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"damage_{car['brand']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                img.save(os.path.join(DAMAGE_FOLDER, filename))
            else:
                flash('Invalid file type. Use PNG, JPG, JPEG, or GIF.', 'danger')
                return redirect(url_for('report_damage', cid=cid))

        query("INSERT INTO damage_reports (car_id, staff_id, description, image, status) VALUES (%s, %s, %s, %s, 'pending')",
              (cid, session['user_id'], description, filename), commit=True)
        flash('Damage reported successfully!', 'success')
        return redirect('/staff')

    return render_template('staff/report_damage.html', car=car)

@app.route('/staff/check_in/<int:booking_id>')
def check_in(booking_id):
    if session.get('role') != 'staff': return redirect('/')
    booking = query("SELECT * FROM bookings WHERE id=%s", (booking_id,), fetchone=True)
    if booking and booking['status'] == 'confirmed':
        query("UPDATE bookings SET status='active' WHERE id=%s", (booking_id,), commit=True)
        flash('Car checked in', 'success')
    else:
        flash('Cannot check in (invalid status)', 'danger')
    return redirect('/staff/rental_history')

@app.route('/staff/check_out/<int:booking_id>')
def check_out(booking_id):
    if session.get('role') != 'staff': return redirect('/')
    booking = query("SELECT * FROM bookings WHERE id=%s", (booking_id,), fetchone=True)
    if booking and booking['status'] == 'active':
        query("UPDATE bookings SET status='completed' WHERE id=%s", (booking_id,), commit=True)
        query("UPDATE cars SET available=TRUE WHERE id=%s", (booking['car_id'],), commit=True)
        flash('Car checked out', 'success')
    else:
        flash('Cannot check out (invalid status)', 'danger')
    return redirect('/staff/rental_history')

@app.route('/staff/rental_history')
def rental_history():
    if session.get('role') != 'staff': return redirect('/')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    # Filter parameters
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    car_model = request.args.get('car', '').strip()

    query_base = """
        SELECT b.*, c.brand, c.model, u.name as customer_name 
        FROM bookings b 
        JOIN cars c ON b.car_id = c.id 
        JOIN users u ON b.user_id = u.id 
        WHERE 1=1
    """
    params = []
    if start_date:
        query_base += " AND b.start_date >= %s"
        params.append(start_date)
    if end_date:
        query_base += " AND b.end_date <= %s"
        params.append(end_date)
    if car_model:
        query_base += " AND c.model LIKE %s"
        params.append(f'%{car_model}%')
    query_base += " ORDER BY b.created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    bookings = query(query_base, params, fetchall=True) or []
    total = query("SELECT COUNT(*) as count FROM bookings", fetchone=True)['count']
    total_pages = (total + per_page - 1) // per_page

    return render_template('staff/rental_history.html', bookings=bookings, page=page, total=total, per_page=per_page, total_pages=total_pages)

@app.route('/staff/my_damage_reports')
def my_damage_reports():
    if session.get('role') != 'staff':
        flash('Staff only!', 'danger')
        return redirect('/')
    reports = query("""
        SELECT dr.*, c.brand, c.model
        FROM damage_reports dr
        JOIN cars c ON dr.car_id = c.id
        WHERE dr.staff_id = %s
        ORDER BY dr.reported_at DESC
    """, (session['user_id'],), fetchall=True) or []
    return render_template('staff/my_damage_reports.html', reports=reports)

# ------------------- STATIC PAGES -------------------
@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/sitemap')
def sitemap():
    return render_template('sitemap.html')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)