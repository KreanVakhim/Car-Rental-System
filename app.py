from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, send_from_directory
)
from datetime import datetime, date, timedelta
import os
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'car_rental_kh_2025_secret'

# ------------------- JINJA FILTERS -------------------
def date_filter(value, fmt='%d/%m/%Y'):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d').date()
        except:
            return value
    return value.strftime(fmt)

app.jinja_env.filters['date'] = date_filter

# ------------------- UPLOAD CONFIG -------------------
UPLOAD_FOLDER = 'static/car_images'
DAMAGE_FOLDER = 'static/damage_images'
PROFILE_FOLDER = 'static/img'
PAYMENT_IMAGES_FOLDER = 'static/payment_images'

for folder in [UPLOAD_FOLDER, DAMAGE_FOLDER, PROFILE_FOLDER, PAYMENT_IMAGES_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app.config.update({
    'UPLOAD_FOLDER': UPLOAD_FOLDER,
    'DAMAGE_FOLDER': DAMAGE_FOLDER,
    'PROFILE_FOLDER': PROFILE_FOLDER,
    'PAYMENT_IMAGES_FOLDER': PAYMENT_IMAGES_FOLDER
})

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# ------------------- FILE SERVING -------------------
@app.route('/car_images/<filename>')
def uploaded_file(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], 'default_car.png')
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/damage_images/<filename>')
def damage_image(filename):
    return send_from_directory(app.config['DAMAGE_FOLDER'], filename)

@app.route('/img/<filename>')
def profile_pic(filename):
    return send_from_directory(app.config['PROFILE_FOLDER'], filename)

# ------------------- MySQL -------------------
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'demo_classa'
}

def get_db():
    try:
        conn = mysql.connector.connect(**db_config)
        conn.autocommit = False
        return conn
    except Error as e:
        print(f"DB error: {e}")
        return None

def query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    if not conn:
        return None
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        result = None
        if fetchone:
            result = cur.fetchone()
        elif fetchall:
            result = cur.fetchall()

        if result:
            desc = cur.description
            rows = [result] if fetchone else result
            for row in rows:
                for i, col in enumerate(desc):
                    val = row[col[0]]
                    if val is not None and col[1] in (108, 12, 7):  # DATE/DATETIME
                        row[col[0]] = val.date() if hasattr(val, 'date') else str(val)[:10]
            result = rows[0] if fetchone else rows

        if commit:
            conn.commit()
            return cur.lastrowid
        return result
    except Error as e:
        print(f"Query error: {e}")
        if commit:
            conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

# ------------------- AUTO UPDATE AVAILABILITY -------------------
def update_car_availability():
    today = date.today()
    query("UPDATE bookings SET status='completed' WHERE status='active' AND end_date < %s", (today,), commit=True)
    query("""
        UPDATE cars c SET available=TRUE WHERE c.available=FALSE
        AND NOT EXISTS (
            SELECT 1 FROM bookings b
            WHERE b.car_id=c.id AND b.status IN ('pending','confirmed','active') AND b.end_date >= %s
        )
    """, (today,), commit=True)

# ------------------- DB INIT -------------------
def init_db():
    conn = get_db()
    if not conn:
        return
    cur = conn.cursor()
    tables = [
        '''CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            password VARCHAR(100) NOT NULL,
            role ENUM('customer','staff','admin') DEFAULT 'customer',
            profile_pic VARCHAR(255) DEFAULT 'default.png',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )''',
        '''CREATE TABLE IF NOT EXISTS cars (
            id INT AUTO_INCREMENT PRIMARY KEY,
            brand VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            year INT NOT NULL,
            price_day DECIMAL(10,2) NOT NULL,
            seats INT NOT NULL,
            image VARCHAR(255) DEFAULT 'default_car.png',
            available BOOLEAN DEFAULT TRUE
        )''',
        '''CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            car_id INT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            discount DECIMAL(10,2) DEFAULT 0,
            promo_code VARCHAR(20),
            status ENUM('pending','confirmed','active','completed','cancelled') DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (car_id) REFERENCES cars(id)
        )''',
        '''CREATE TABLE IF NOT EXISTS promotions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            code VARCHAR(20) UNIQUE NOT NULL,
            discount_pct INT NOT NULL,
            valid_from DATE NOT NULL,
            valid_to DATE NOT NULL
        )''',
        '''CREATE TABLE IF NOT EXISTS damage_reports (
            id INT AUTO_INCREMENT PRIMARY KEY,
            car_id INT NOT NULL,
            staff_id INT NOT NULL,
            description TEXT NOT NULL,
            image VARCHAR(255),
            status ENUM('pending','approved','rejected') DEFAULT 'pending',
            reported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (car_id) REFERENCES cars(id),
            FOREIGN KEY (staff_id) REFERENCES users(id)
        )'''
    ]
    for t in tables:
        cur.execute(t)

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        today = date.today()
        cur.executemany(
            "INSERT INTO users (name,email,phone,password,role,profile_pic) VALUES (%s,%s,%s,%s,%s,%s)",
            [
                ('Admin KH', 'admin@carrental.com', '012345678', 'admin123', 'admin', 'user1.png'),
                ('Staff One', 'staff@carrental.com', '098765432', 'staff123', 'staff', 'staff1.png'),
                ('Sokha', 'sokha@test.com', '011223344', 'cust123', 'customer', 'user2.png')
            ]
        )
        cur.executemany(
            "INSERT INTO cars (brand,model,year,price_day,seats,image) VALUES (%s,%s,%s,%s,%s,%s)",
            [
                ('Toyota', 'Camry', 2023, 50.00, 5, 'car1.png'),
                ('Honda', 'Civic', 2022, 45.00, 5, 'car2.png')
            ]
        )
        cur.execute(
            "INSERT IGNORE INTO promotions (code,discount_pct,valid_from,valid_to) VALUES (%s,%s,%s,%s)",
            ('WELCOME20', 20, today, today + timedelta(days=30))
        )
    conn.commit()
    cur.close()
    conn.close()

init_db()

# ------------------- HELPERS -------------------
@app.context_processor
def inject_helpers():
    pic = session.get('profile_pic', 'default.png')
    path = os.path.join(app.config['PROFILE_FOLDER'], pic)
    if not os.path.exists(path):
        pic = 'default.png'
    return {
        'today': date.today(),
        'current_year': date.today().year,
        'user_pic': url_for('profile_pic', filename=pic)
    }

# ------------------- ROUTES -------------------
@app.route('/')
def index():
    update_car_availability()
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
                'profile_pic': user.get('profile_pic', 'default.png')
            })
            flash('Login successful!', 'success')
            return redirect('/')
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        phone = request.form['phone'].strip()
        password = request.form['password'].strip()

        if query("SELECT id FROM users WHERE email=%s", (email,), fetchone=True):
            flash('Email already registered', 'danger')
            return render_template('register.html')

        query(
            "INSERT INTO users (name, email, phone, password, role) VALUES (%s, %s, %s, %s, 'customer')",
            (name, email, phone, password), commit=True
        )
        flash('Registration successful! Please login.', 'success')
        return redirect('/login')

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'success')
    return redirect('/')

@app.route('/cars')
def cars_list():
    update_car_availability()
    cars = query("SELECT * FROM cars WHERE available=TRUE", fetchall=True) or []
    return render_template('cars.html', cars=cars)

@app.route('/car/<int:cid>')
def car_detail(cid):
    update_car_availability()
    car = query("SELECT * FROM cars WHERE id=%s AND available=TRUE", (cid,), fetchone=True)
    return render_template('car_detail.html', car=car) if car else redirect('/cars')

@app.route('/book/<int:cid>', methods=['GET', 'POST'])
def book_car(cid):
    if session.get('role') != 'customer':
        flash('Login as customer', 'warning')
        return redirect('/login')
    
    update_car_availability()
    car = query("SELECT * FROM cars WHERE id=%s AND available=TRUE", (cid,), fetchone=True)
    if not car:
        flash('This car is not available', 'danger')
        return redirect('/cars')
    
    promos = query(
        "SELECT * FROM promotions WHERE valid_from <= %s AND valid_to >= %s",
        (date.today(), date.today()), fetchall=True
    ) or []

    if request.method == 'POST':
        s = request.form['start_date']
        e = request.form['end_date']
        start_date = datetime.strptime(s, '%Y-%m-%d').date()
        end_date = datetime.strptime(e, '%Y-%m-%d').date()
        if end_date < start_date:
            flash('End date cannot be before start date', 'danger')
            return render_template('book.html', car=car, min_date=date.today().strftime('%Y-%m-%d'), promotions=promos)

        days = (end_date - start_date).days + 1
        total = car['price_day'] * days

        promo_code = request.form.get('promo_code', '').strip()
        discount = 0
        if promo_code:
            promo = query(
                "SELECT * FROM promotions WHERE code=%s AND valid_from <= %s AND valid_to >= %s",
                (promo_code, date.today(), date.today()), fetchone=True
            )
            if promo:
                discount = total * (promo['discount_pct'] / 100)
                total -= discount

        bid = query(
            "INSERT INTO bookings (user_id,car_id,start_date,end_date,total,discount,promo_code,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'pending')",
            (session['user_id'], cid, s, e, total, discount, promo_code if discount > 0 else None), commit=True
        )
        
        query("UPDATE cars SET available=FALSE WHERE id=%s", (cid,), commit=True)
        
        flash('Booking created! Please complete payment.', 'success')
        return redirect(url_for('payment', booking_id=bid))
    
    return render_template('book.html', car=car, min_date=date.today().strftime('%Y-%m-%d'), promotions=promos)

@app.route('/my_bookings')
def my_bookings():
    if 'user_id' not in session:
        return redirect('/login')
    update_car_availability()
    bookings = query("""
        SELECT 
            b.*, 
            c.brand, c.model, c.year, c.image
        FROM bookings b 
        JOIN cars c ON b.car_id = c.id 
        WHERE b.user_id = %s 
        ORDER BY b.created_at DESC
    """, (session['user_id'],), fetchall=True) or []
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/payment/<int:booking_id>')
def payment(booking_id):
    b = query("""
        SELECT b.*, c.brand, c.model 
        FROM bookings b 
        JOIN cars c ON b.car_id = c.id 
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, session['user_id']), fetchone=True)
    if not b:
        return redirect('/my_bookings')
    return render_template('payment.html', booking=b)

@app.route('/confirm_payment/<int:booking_id>')
def confirm_payment(booking_id):
    query("UPDATE bookings SET status='confirmed' WHERE id=%s AND user_id=%s", (booking_id, session['user_id']), commit=True)
    flash('Payment confirmed!', 'success')
    return redirect('/my_bookings')

@app.route('/invoice/<int:booking_id>')
def invoice(booking_id):
    if 'user_id' not in session:
        flash('Please login to view invoice', 'warning')
        return redirect('/login')

    booking = query("""
        SELECT 
            b.*, 
            c.brand, c.model, c.year, c.price_day, c.image,
            u.name AS customer_name, u.email
        FROM bookings b
        JOIN cars c ON b.car_id = c.id
        JOIN users u ON b.user_id = u.id
        WHERE b.id = %s AND b.user_id = %s
    """, (booking_id, session['user_id']), fetchone=True)

    if not booking:
        flash('Invoice not found or access denied', 'danger')
        return redirect('/my_bookings')

    start = booking['start_date']
    end = booking['end_date']
    booking['rental_days'] = (end - start).days + 1
    booking['subtotal'] = booking['price_day'] * booking['rental_days']
    booking['total_price'] = booking['subtotal'] - booking['discount']

    return render_template('invoice.html', booking=booking)

@app.route('/promotions')
def promotions():
    update_car_availability()
    promos = query(
        "SELECT * FROM promotions WHERE valid_from <= %s AND valid_to >= %s",
        (date.today(), date.today()), fetchall=True
    ) or []
    return render_template('promotions.html', promos=promos)

@app.route('/subscribe_promo', methods=['POST'])
def subscribe_promo():
    email = request.form.get('email', '').strip()
    if email and '@' in email:
        flash(f'Subscribed {email} to exclusive promotions!', 'success')
    else:
        flash('Please enter a valid email', 'danger')
    return redirect(url_for('promotions'))

# ------------------- PROFILE -------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect('/login')
    
    user = query("SELECT * FROM users WHERE id=%s", (session['user_id'],), fetchone=True)
    if not user:
        flash('User not found', 'danger')
        return redirect('/logout')
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        
        new_password = request.form.get('password', '').strip()
        password = new_password if new_password else user['password']
        
        filename = user['profile_pic']
        if 'profile_pic' in request.files and request.files['profile_pic'].filename:
            file = request.files['profile_pic']
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"user_{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                file.save(os.path.join(app.config['PROFILE_FOLDER'], filename))
                if user['profile_pic'] != 'default.png' and user['profile_pic'] != filename:
                    old_path = os.path.join(app.config['PROFILE_FOLDER'], user['profile_pic'])
                    if os.path.exists(old_path):
                        os.remove(old_path)
        
        query(
            "UPDATE users SET name=%s, phone=%s, password=%s, profile_pic=%s WHERE id=%s",
            (name, phone, password, filename, session['user_id']), commit=True
        )
        
        session['user_name'] = name
        session['profile_pic'] = filename
        
        flash('Profile updated successfully!', 'success')
        return redirect('/profile')
    
    return render_template('profile.html', user=user)

# ------------------- ADMIN -------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/')
    update_car_availability()
    
    users_count = query("SELECT COUNT(*) AS count FROM users", fetchone=True)['count']
    cars_count = query("SELECT COUNT(*) AS count FROM cars", fetchone=True)['count']
    bookings_count = query("SELECT COUNT(*) AS count FROM bookings", fetchone=True)['count']
    revenue_result = query("SELECT COALESCE(SUM(total-discount),0) AS revenue FROM bookings WHERE status IN ('confirmed','completed')", fetchone=True)
    revenue = revenue_result['revenue'] if revenue_result else 0

    recent_bookings = query(
        "SELECT b.id,b.start_date,b.end_date,b.total,b.status,u.name,c.brand,c.model FROM bookings b JOIN users u ON b.user_id=u.id JOIN cars c ON b.car_id=c.id ORDER BY b.created_at DESC LIMIT 5",
        fetchall=True
    ) or []
    
    return render_template(
        'admin/admin_dashboard.html',
        users_count=users_count, cars_count=cars_count,
        bookings_count=bookings_count, revenue=revenue,
        recent_bookings=recent_bookings
    )

@app.route('/admin/manage_cars', methods=['GET', 'POST'])
def admin_manage_cars():
    if session.get('role') != 'admin':
        flash('Admin access only', 'danger')
        return redirect('/')

    update_car_availability()

    if request.method == 'POST':
        action = request.form.get('action')
        car_id = request.form.get('car_id')

        if action == 'add':
            filename = 'default_car.png'
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                if allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = secure_filename(f"car_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            query(
                "INSERT INTO cars (brand,model,year,price_day,seats,image) VALUES (%s,%s,%s,%s,%s,%s)",
                (request.form['brand'],
                 request.form['model'],
                 request.form['year'],
                 request.form['price_day'],
                 request.form['seats'],
                 filename), commit=True
            )
            flash('Car added successfully!', 'success')

        elif action == 'edit' and car_id:
            car = query("SELECT * FROM cars WHERE id=%s", (car_id,), fetchone=True)
            if not car:
                flash('Car not found', 'danger')
                return redirect(url_for('admin_manage_cars'))

            filename = car['image']
            if 'image' in request.files and request.files['image'].filename:
                file = request.files['image']
                if allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = secure_filename(f"car_{car_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    if car['image'] != 'default_car.png':
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'], car['image'])
                        if os.path.exists(old_path):
                            os.remove(old_path)

            query("""
                UPDATE cars SET 
                    brand=%s, model=%s, year=%s, price_day=%s, seats=%s, image=%s
                WHERE id=%s
            """, (
                request.form['brand'],
                request.form['model'],
                request.form['year'],
                request.form['price_day'],
                request.form['seats'],
                filename,
                car_id
            ), commit=True)
            flash('Car updated successfully!', 'success')

        elif action == 'delete' and car_id:
            car = query("SELECT image FROM cars WHERE id=%s", (car_id,), fetchone=True)
            if car and car['image'] != 'default_car.png':
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], car['image'])
                if os.path.exists(img_path):
                    os.remove(img_path)
            query("DELETE FROM cars WHERE id=%s", (car_id,), commit=True)
            flash('Car deleted permanently', 'success')

        return redirect(url_for('admin_manage_cars'))

    cars = query("SELECT * FROM cars ORDER BY id DESC", fetchall=True) or []
    return render_template('admin/manage_cars.html', cars=cars)

# ------------------- ADMIN – PROMOTIONS -------------------
@app.route('/admin/manage_promotions', methods=['GET', 'POST'])
def admin_manage_promotions():
    if session.get('role') != 'admin':
        flash('Admin access only', 'danger')
        return redirect('/')

    if request.method == 'POST':
        action = request.form.get('action')
        promo_id = request.form.get('promo_id')

        if action == 'add':
            code = request.form['code'].strip().upper()
            if query("SELECT id FROM promotions WHERE code=%s", (code,), fetchone=True):
                flash('Promo code already exists', 'danger')
            else:
                query(
                    "INSERT INTO promotions (code,discount_pct,valid_from,valid_to) VALUES (%s,%s,%s,%s)",
                    (code,
                     request.form['discount_pct'],
                     request.form['valid_from'],
                     request.form['valid_to']), commit=True)
                flash('Promotion added', 'success')

        elif action == 'edit' and promo_id:
            query(
                "UPDATE promotions SET code=%s, discount_pct=%s, valid_from=%s, valid_to=%s WHERE id=%s",
                (request.form['code'].strip().upper(),
                 request.form['discount_pct'],
                 request.form['valid_from'],
                 request.form['valid_to'],
                 promo_id), commit=True)
            flash('Promotion updated', 'success')

        elif action == 'delete' and promo_id:
            query("DELETE FROM promotions WHERE id=%s", (promo_id,), commit=True)
            flash('Promotion deleted', 'success')

        return redirect(url_for('admin_manage_promotions'))

    promos = query("SELECT * FROM promotions ORDER BY id DESC", fetchall=True) or []
    return render_template('admin/manage_promotions.html', promotions=promos)

# ------------------- ADMIN – USERS -------------------
@app.route('/admin/manage_users', methods=['GET', 'POST'])
def admin_manage_users():
    if session.get('role') != 'admin':
        flash('Admin access only', 'danger')
        return redirect('/')

    if request.method == 'POST':
        action = request.form.get('action')
        user_id = request.form.get('user_id')

        if action == 'role' and user_id:
            new_role = request.form['new_role']
            if new_role in ('customer', 'staff'):
                query("UPDATE users SET role=%s WHERE id=%s", (new_role, user_id), commit=True)
                flash('User role updated', 'success')
            else:
                flash('Invalid role', 'danger')

        elif action == 'delete' and user_id:
            if int(user_id) == session['user_id']:
                flash('You cannot delete yourself', 'danger')
            else:
                user = query("SELECT profile_pic FROM users WHERE id=%s", (user_id,), fetchone=True)
                if user and user['profile_pic'] != 'default.png':
                    pic_path = os.path.join(app.config['PROFILE_FOLDER'], user['profile_pic'])
                    if os.path.exists(pic_path):
                        os.remove(pic_path)
                query("DELETE FROM users WHERE id=%s", (user_id,), commit=True)
                flash('User deleted', 'success')

        return redirect(url_for('admin_manage_users'))

    users = query("SELECT * FROM users ORDER BY id DESC", fetchall=True) or []
    return render_template('admin/manage_users.html', users=users)

# ------------------- ADMIN – BOOKINGS -------------------
@app.route('/admin/manage_bookings')
def admin_manage_bookings():
    if session.get('role') != 'admin':
        flash('Admin access only', 'danger')
        return redirect('/')

    bookings = query("""
        SELECT 
            b.*, 
            u.name, 
            c.brand, c.model
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN cars c ON b.car_id = c.id
        ORDER BY b.created_at DESC
    """, fetchall=True) or []

    return render_template('admin/manage_bookings.html', bookings=bookings)

# ------------------- ADMIN – DAMAGE REPORTS -------------------
@app.route('/admin/damage_reports')
def damage_reports():
    if session.get('role') != 'admin':
        flash('Admin access only', 'danger')
        return redirect('/')
    
    reports = query("""
        SELECT dr.*, c.brand, c.model, u.name AS staff_name
        FROM damage_reports dr
        JOIN cars c ON dr.car_id = c.id
        JOIN users u ON dr.staff_id = u.id
        ORDER BY dr.reported_at DESC
    """, fetchall=True) or []
    
    return render_template('admin/damage_reports.html', reports=reports)

@app.route('/admin/review_damage/<int:report_id>/<action>', methods=['POST'])
def review_damage(report_id, action):
    if session.get('role') != 'admin':
        flash('Admin access only', 'danger')
        return redirect('/')
    
    if action not in ['approve', 'reject']:
        flash('Invalid action', 'danger')
        return redirect('/admin/damage_reports')
    
    new_status = 'approved' if action == 'approve' else 'rejected'
    query(
        "UPDATE damage_reports SET status=%s WHERE id=%s",
        (new_status, report_id), commit=True
    )
    flash(f'Damage report #{report_id} {new_status}!', 'success')
    return redirect('/admin/damage_reports')

# ------------------- STAFF -------------------
@app.route('/staff_dashboard')
def staff_dashboard():
    if session.get('role') != 'staff':
        return redirect('/')
    update_car_availability()
    cars = query("SELECT * FROM cars", fetchall=True) or []
    recent_reports = query("""
        SELECT dr.*, c.brand, c.model
        FROM damage_reports dr
        JOIN cars c ON dr.car_id = c.id
        WHERE dr.staff_id = %s
        ORDER BY dr.reported_at DESC
        LIMIT 5
    """, (session['user_id'],), fetchall=True) or []
    return render_template(
        'staff/staff_dashboard.html',
        cars=cars,
        recent_reports=recent_reports
    )

@app.route('/my_damage_reports')
def my_damage_reports():
    if session.get('role') != 'staff':
        flash('Staff access only', 'danger')
        return redirect('/')
    reports = query("""
        SELECT dr.*, c.brand, c.model
        FROM damage_reports dr
        JOIN cars c ON dr.car_id = c.id
        WHERE dr.staff_id = %s
        ORDER BY dr.reported_at DESC
    """, (session['user_id'],), fetchall=True) or []
    return render_template('staff/my_damage_reports.html', reports=reports)

@app.route('/report_damage/<int:car_id>', methods=['GET', 'POST'])
def report_damage(car_id):
    if session.get('role') != 'staff':
        return redirect('/')
    car = query("SELECT * FROM cars WHERE id=%s", (car_id,), fetchone=True)
    if not car:
        return redirect('/cars')
    if request.method == 'POST':
        desc = request.form['description']
        filename = None
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = secure_filename(f"damage_{car_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
                file.save(os.path.join(app.config['DAMAGE_FOLDER'], filename))
        query(
            "INSERT INTO damage_reports (car_id,staff_id,description,image,status) VALUES (%s,%s,%s,%s,'pending')",
            (car_id, session['user_id'], desc, filename), commit=True
        )
        flash('Damage reported', 'success')
        return redirect('/my_damage_reports')
    return render_template('staff/report_damage.html', car=car)

@app.route('/rental_history')
def rental_history():
    if session.get('role') != 'staff':
        return redirect('/')
    update_car_availability()

    start = request.args.get('start')
    end = request.args.get('end')
    car = request.args.get('car', '').strip()
    page = max(int(request.args.get('page', 1)), 1)
    per_page = 10

    sql = """
        SELECT b.*, c.brand, c.model, u.name AS customer_name
        FROM bookings b
        JOIN cars c ON b.car_id = c.id
        JOIN users u ON b.user_id = u.id
        WHERE 1=1
    """
    params = []

    if start:
        sql += " AND b.start_date >= %s"
        params.append(start)
    if end:
        sql += " AND b.end_date <= %s"
        params.append(end)
    if car:
        sql += " AND (c.brand LIKE %s OR c.model LIKE %s)"
        params.extend([f"%{car}%", f"%{car}%"])

    count_sql = sql.replace(
        "SELECT b.*, c.brand, c.model, u.name AS customer_name",
        "SELECT COUNT(*) AS total_count"
    )
    count_result = query(count_sql, params, fetchone=True)
    total = count_result['total_count'] if count_result else 0
    total_pages = (total + per_page - 1) // per_page

    sql += " ORDER BY b.start_date DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    bookings = query(sql, params, fetchall=True) or []

    return render_template(
        'staff/rental_history.html',
        bookings=bookings,
        page=page,
        total_pages=total_pages,
        request=request
    )

@app.route('/check_in/<int:booking_id>')
def check_in(booking_id):
    if session.get('role') != 'staff':
        flash('Staff only', 'danger')
        return redirect('/')
    booking = query("SELECT * FROM bookings WHERE id=%s AND status='confirmed'", (booking_id,), fetchone=True)
    if not booking:
        flash('Invalid booking', 'danger')
        return redirect('/rental_history')
    query("UPDATE bookings SET status='active' WHERE id=%s", (booking_id,), commit=True)
    flash(f'Checked in: #{booking_id}', 'success')
    return redirect('/rental_history')

@app.route('/check_out/<int:booking_id>')
def check_out(booking_id):
    if session.get('role') != 'staff':
        flash('Staff only', 'danger')
        return redirect('/')
    booking = query("SELECT * FROM bookings WHERE id=%s AND status='active'", (booking_id,), fetchone=True)
    if not booking:
        flash('Invalid booking', 'danger')
        return redirect('/rental_history')
    query("UPDATE bookings SET status='completed' WHERE id=%s", (booking_id,), commit=True)
    query("UPDATE cars SET available=TRUE WHERE id=%s", (booking['car_id'],), commit=True)
    flash(f'Checked out: #{booking_id}', 'success')
    return redirect('/rental_history')

# ------------------- SITEMAP (FIXED!) -------------------
@app.route('/sitemap')
def sitemap():
    total_pages = 8
    if session.get('user_id'):
        total_pages += 2
        if session['role'] == 'customer':
            total_pages += 1
        elif session['role'] == 'staff':
            total_pages += 3
        elif session['role'] == 'admin':
            total_pages += 6

    first_car = query("SELECT id FROM cars LIMIT 1", fetchone=True)
    first_car_id = first_car['id'] if first_car else None

    return render_template(
        'sitemap.html',
        total_pages=total_pages,
        first_car_id=first_car_id
    )

# ------------------- STATIC PAGES -------------------
@app.route('/privacy_policy')
def privacy_policy():
    return render_template('privacy_policy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)