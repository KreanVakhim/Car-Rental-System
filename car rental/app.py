from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
import bcrypt
from datetime import datetime
import os
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(24).hex()  # Secure random key
logging.basicConfig(level=logging.DEBUG)  # Enable debugging logs

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'demo_classa'

# File Upload Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

mysql = MySQL(app)

# Define is_logged_in globally
def is_logged_in():
    return 'user_id' in session

# Register is_logged_in as a global function for Jinja2 templates
@app.context_processor
def utility_processor():
    return dict(is_logged_in=is_logged_in)

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Home route: Display available cars with filters and sorting
@app.route('/')
def index():
    cursor = mysql.connection.cursor()
    
    # Get filter and sort parameters
    brand = request.args.get('brand', '').strip()
    model = request.args.get('model', '').strip()
    min_price = request.args.get('min_price', '0')
    max_price = request.args.get('max_price', '200')
    status = request.args.get('status', '')
    sort = request.args.get('sort', 'price_asc')  # Default sort
    min_year = request.args.get('min_year', '')
    max_year = request.args.get('max_year', '')
    fuel_type = request.args.get('fuel_type', '')
    transmission = request.args.get('transmission', '')
    only_available = request.args.get('only_available', False)
    view = request.args.get('view', 'grid')

    # Convert price strings to integers, with fallback for invalid values
    try:
        min_price = int(float(min_price)) if min_price else 0
    except (ValueError, TypeError):
        min_price = 0
        flash('Invalid minimum price! Defaulting to $0.', 'danger')
    try:
        max_price = int(float(max_price)) if max_price else 200
    except (ValueError, TypeError):
        max_price = 200
        flash('Invalid maximum price! Defaulting to $200.', 'danger')

    # Build dynamic SQL query
    query = "SELECT * FROM cars WHERE 1=1"
    params = []
    
    if brand:
        query += " AND brand LIKE %s"
        params.append(f'%{brand}%')
    if model:
        query += " AND model LIKE %s"
        params.append(f'%{model}%')
    if min_price:
        query += " AND price_per_day >= %s"
        params.append(min_price)
    if max_price:
        query += " AND price_per_day <= %s"
        params.append(max_price)
    if status:
        query += " AND status = %s"
        params.append(status)
    if min_year:
        query += " AND year >= %s"
        params.append(int(min_year))
    if max_year:
        query += " AND year <= %s"
        params.append(int(max_year))
    if fuel_type:
        query += " AND fuel_type = %s"
        params.append(fuel_type)
    if transmission:
        query += " AND transmission = %s"
        params.append(transmission)
    if only_available:
        query += " AND status = 'Available'"

    # Add sorting
    if sort == 'price_asc':
        query += " ORDER BY price_per_day ASC"
    elif sort == 'price_desc':
        query += " ORDER BY price_per_day DESC"
    elif sort == 'brand_asc':
        query += " ORDER BY brand ASC"
    elif sort == 'brand_desc':
        query += " ORDER BY brand DESC"
    elif sort == 'year_desc':
        query += " ORDER BY year DESC"

    cursor.execute(query, params)
    cars = cursor.fetchall()
    cursor.close()
    
    return render_template('index.html', cars=cars, brand=brand, model=model, min_price=min_price, max_price=max_price, status=status, min_year=min_year, max_year=max_year, fuel_type=fuel_type, transmission=transmission, only_available=only_available, view=view, sort=sort)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            logging.debug(f"Attempting login for {username}, Hash: {user[2]}")
            try:
                if bcrypt.checkpw(password, user[2].encode('utf-8')):
                    session['user_id'] = user[0]
                    session['username'] = user[1]
                    session['role'] = user[3]
                    flash('Login successful!', 'success')
                    if user[3] == 'admin':
                        return redirect(url_for('admin_dashboard'))
                    elif user[3] == 'staff':
                        return redirect(url_for('staff_check'))
                    else:
                        return redirect(url_for('index'))
                else:
                    logging.debug(f"Password mismatch for {username}")
                    flash('Invalid credentials!', 'danger')
            except ValueError as e:
                logging.error(f"bcrypt error: {e} for user {username}")
                flash('Invalid password hash in database. Contact admin to reset.', 'danger')
        else:
            logging.debug(f"User {username} not found")
            flash('Invalid credentials!', 'danger')
    return render_template('login.html')

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
        email = request.form['email']
        role = 'customer'  # Default role
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, email, role) VALUES (%s, %s, %s, %s)",
                           (username, password, email, role))
            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Registration error: {e}")
            flash('Username or email already exists!', 'danger')
        finally:
            cursor.close()
    return render_template('register.html')

# Car detail route
@app.route('/car/<int:car_id>')
def car_detail(car_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = cursor.fetchone()
    cursor.close()
    return render_template('car_detail.html', car=car)

# Booking route: Supports new bookings table fields
@app.route('/book/<int:car_id>', methods=['GET', 'POST'])
def book(car_id):
    if not is_logged_in():
        flash('Please login to book a car!', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        location_pickup = request.form.get('location_pickup', 'Default Location')
        location_return = request.form.get('location_return', 'Default Location')
        notes = request.form.get('notes', '')
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT price_per_day FROM cars WHERE id = %s AND status = 'Available'", (car_id,))
        car = cursor.fetchone()
        if car:
            try:
                days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days
                if days <= 0:
                    flash('End date must be after start date!', 'danger')
                    return redirect(url_for('book', car_id=car_id))
                total_cost = car[0] * days
                cursor.execute("""
                    INSERT INTO bookings (user_id, car_id, start_date, end_date, status, total_cost, location_pickup, location_return, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (session['user_id'], car_id, start_date, end_date, 'Pending', total_cost, location_pickup, location_return, notes))
                cursor.execute("UPDATE cars SET status = 'Rented' WHERE id = %s", (car_id,))
                mysql.connection.commit()
                flash('Booking request submitted!', 'success')
                return redirect(url_for('bookings'))
            except ValueError:
                flash('Invalid date format!', 'danger')
        else:
            flash('Car is not available!', 'danger')
        cursor.close()
    return render_template('bookings.html', car_id=car_id)

# Bookings route: Display user's bookings
@app.route('/bookings')
def bookings():
    if not is_logged_in():
        flash('Please login to view bookings!', 'danger')
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT b.id, c.brand, c.model, b.start_date, b.end_date, b.status, b.total_cost, b.location_pickup, b.location_return, b.notes
        FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s
    """, (session['user_id'],))
    bookings = cursor.fetchall()
    cursor.close()
    return render_template('bookings.html', bookings=bookings)

# Checkout route
@app.route('/checkout/<int:booking_id>', methods=['GET', 'POST'])
def checkout(booking_id):
    if not is_logged_in():
        flash('Please login to proceed with payment!', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        payment_method = request.form['payment_method']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT b.id, b.total_cost FROM bookings b WHERE b.id = %s", (booking_id,))
        booking = cursor.fetchone()
        if booking:
            amount = booking[1]
            cursor.execute("INSERT INTO payments (booking_id, amount, payment_method, payment_date) VALUES (%s, %s, %s, %s)",
                           (booking_id, amount, payment_method, datetime.now()))
            cursor.execute("INSERT INTO invoices (booking_id, amount, issue_date) VALUES (%s, %s, %s)",
                           (booking_id, amount, datetime.now()))
            cursor.execute("UPDATE bookings SET status = 'Confirmed' WHERE id = %s", (booking_id,))
            mysql.connection.commit()
            flash('Payment successful! Invoice generated.', 'success')
            return redirect(url_for('invoice', booking_id=booking_id))
        cursor.close()
    return render_template('checkout.html', booking_id=booking_id)

# Invoice route
@app.route('/invoice/<int:booking_id>')
def invoice(booking_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT i.id, i.amount, i.penalty, i.issue_date, c.brand, c.model
        FROM invoices i JOIN bookings b ON i.booking_id = b.id JOIN cars c ON b.car_id = c.id
        WHERE i.booking_id = %s
    """, (booking_id,))
    invoice = cursor.fetchone()
    cursor.close()
    return render_template('invoice.html', invoice=invoice)

# Admin dashboard route
@app.route('/admin_dashboard')
def admin_dashboard():
    if not is_logged_in():
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    if session['role'] != 'admin':
        flash('Access denied! Admin only.', 'danger')
        return redirect(url_for('index'))
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM cars")
    cars = cursor.fetchall()
    cursor.execute("""
        SELECT b.id, u.username, c.brand, c.model, b.start_date, b.end_date, b.status
        FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id
    """)
    bookings = cursor.fetchall()
    cursor.close()
    return render_template('admin_dashboard.html', cars=cars, bookings=bookings)

# Add car route (admin only) - Enhanced for single image upload
@app.route('/admin/add_car', methods=['GET', 'POST'])
def add_car():
    if not is_logged_in():
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    if session['role'] != 'admin':
        flash('Access denied! Admin only.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        brand = request.form['brand']
        model = request.form['model']
        price_per_day = float(request.form['price_per_day'])
        status = request.form['status']
        year = request.form.get('year', '')
        fuel_type = request.form.get('fuel_type', '')
        transmission = request.form.get('transmission', '')
        featured = 1 if 'featured' in request.form else 0
        image = None

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image = filename
            else:
                flash('Invalid file type! Use png, jpg, jpeg, or gif.', 'danger')

        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO cars (brand, model, price_per_day, status, image, year, fuel_type, transmission, featured)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (brand, model, price_per_day, status, image, year, fuel_type, transmission, featured))
        mysql.connection.commit()
        cursor.close()
        flash('Car added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_car.html')

# Update car image route (admin only)
@app.route('/admin/update_car_image/<int:car_id>', methods=['GET', 'POST'])
def update_car_image(car_id):
    if not is_logged_in():
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    if session['role'] != 'admin':
        flash('Access denied! Admin only.', 'danger')
        return redirect(url_for('index'))
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = cursor.fetchone()
    if request.method == 'POST':
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cursor.execute("UPDATE cars SET image = %s WHERE id = %s", (filename, car_id))
                mysql.connection.commit()
                flash('Image updated successfully!', 'success')
            else:
                flash('Invalid file type! Use png, jpg, jpeg, or gif.', 'danger')
        return redirect(url_for('admin_dashboard'))
    cursor.close()
    return render_template('update_car_image.html', car=car)

# Add review route
@app.route('/add_review/<int:car_id>', methods=['POST'])
def add_review(car_id):
    if not is_logged_in():
        flash('Please login to leave a review!', 'danger')
        return redirect(url_for('login'))
    if request.method == 'POST':
        rating = request.form['rating']
        comment = request.form['comment']
        user_id = session['user_id']
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO reviews (car_id, user_id, rating, comment, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (car_id, user_id, rating, comment, datetime.now()))
            mysql.connection.commit()
            flash('Review submitted successfully!', 'success')
        except Exception as e:
            logging.error(f"Review submission error: {e}")
            flash('Failed to submit review. Try again.', 'danger')
            mysql.connection.rollback()
        finally:
            cursor.close()
        return redirect(url_for('car_detail', car_id=car_id))

# Staff check route
@app.route('/staff_check', methods=['GET', 'POST'])
def staff_check():
    if not is_logged_in():
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    if session['role'] != 'staff':
        flash('Access denied! Staff only.', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        booking_id = request.form['booking_id']
        penalty = float(request.form.get('penalty', 0))
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE bookings SET status = 'Completed' WHERE id = %s", (booking_id,))
        if penalty > 0:
            cursor.execute("UPDATE invoices SET penalty = %s WHERE booking_id = %s", (penalty, booking_id))
        cursor.execute("UPDATE cars SET status = 'Available' WHERE id = (SELECT car_id FROM bookings WHERE id = %s)", (booking_id,))
        mysql.connection.commit()
        flash('Car return processed!', 'success')
        cursor.close()
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT b.id, u.username, c.brand, c.model
        FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id
        WHERE b.status = 'Confirmed'
    """)
    bookings = cursor.fetchall()
    cursor.close()
    return render_template('staff_check.html', bookings=bookings)

# Reset password route (admin only)
@app.route('/admin/reset_password/<username>', methods=['POST'])
def reset_password(username):
    if not is_logged_in():
        flash('Access denied!', 'danger')
        return redirect(url_for('login'))
    if session['role'] != 'admin':
        flash('Access denied! Admin only.', 'danger')
        return redirect(url_for('index'))
    new_password = 'password123'  # Default reset password
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (hashed, username))
        mysql.connection.commit()
        flash(f'Password for {username} reset to {new_password}.', 'success')
    except Exception as e:
        logging.error(f"Reset password error: {e}")
        flash('Failed to reset password. Contact support.', 'danger')
        mysql.connection.rollback()
    finally:
        cursor.close()
    return redirect(url_for('admin_dashboard'))

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)