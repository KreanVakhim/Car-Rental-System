from flask import Flask, render_template, flash, redirect, url_for, request, jsonify, session, Blueprint
from flask_mysqldb import MySQL
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SelectField, BooleanField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email
from functools import wraps
from datetime import datetime, timedelta
import MySQLdb.cursors
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Replace with a secure key
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'demo_classa'

# Initialize MySQL
mysql = MySQL(app)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, email, role, is_active):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.is_active = is_active

# Flask-Login User Loader
@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, username, email, role, is_active FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return User(user['id'], user['username'], user['email'], user['role'], user['is_active'])
    return None

# Role-based Decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access restricted to admins.', 'danger')
            return redirect(url_for('home.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'staff']:
            flash('Access restricted to admin or staff.', 'danger')
            return redirect(url_for('home.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Template Filter for Date Formatting
@app.template_filter('datetimeformat')
def datetimeformat(value):
    return value.strftime('%Y-%m-%d') if isinstance(value, datetime) else value

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CarForm(FlaskForm):
    make = StringField('Make', validators=[DataRequired()])
    model = StringField('Model', validators=[DataRequired()])
    price_per_day = FloatField('Price per Day (USD)', validators=[DataRequired()])
    status = SelectField('Status', choices=[('Available', 'Available'), ('Rented', 'Rented'), ('Under Maintenance', 'Under Maintenance')], validators=[DataRequired()])
    image = StringField('Image File Name')
    featured = BooleanField('Featured')
    submit = SubmitField('Save')

class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('admin', 'Admin'), ('staff', 'Staff'), ('customer', 'Customer')], validators=[DataRequired()])
    is_active = BooleanField('Active')
    avatar = StringField('Avatar File Name')
    submit = SubmitField('Save')

class PenaltyForm(FlaskForm):
    penalty_amount = FloatField('Penalty Amount (USD)', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    submit = SubmitField('Record Penalty')

# Blueprints
auth_bp = Blueprint('auth', __name__)
home_bp = Blueprint('home', __name__)
cars_bp = Blueprint('cars', __name__)
users_bp = Blueprint('users', __name__)
handovers_bp = Blueprint('handovers', __name__)
lang_bp = Blueprint('lang', __name__)
bookings_bp = Blueprint('bookings', __name__)

# Create Database Tables
def init_db():
    cursor = mysql.connection.cursor()
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password VARCHAR(100) NOT NULL,
            role VARCHAR(20) DEFAULT 'customer',
            is_active BOOLEAN DEFAULT TRUE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            avatar VARCHAR(100)
        )
    ''')
    # Create cars table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cars (
            id INT AUTO_INCREMENT PRIMARY KEY,
            make VARCHAR(50) NOT NULL,
            model VARCHAR(50) NOT NULL,
            price_per_day FLOAT NOT NULL,
            status VARCHAR(20) DEFAULT 'Available',
            image VARCHAR(100),
            featured BOOLEAN DEFAULT FALSE
        )
    ''')
    # Create bookings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            car_id INT NOT NULL,
            start_date DATETIME NOT NULL,
            end_date DATETIME NOT NULL,
            status VARCHAR(20) DEFAULT 'Pending',
            penalty_amount FLOAT DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
        )
    ''')
    # Create payments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            booking_id INT NOT NULL,
            payment_method VARCHAR(50) NOT NULL,
            amount FLOAT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        )
    ''')
    # Insert default admin user if not exists
    cursor.execute('''
        INSERT IGNORE INTO users (username, email, password, role, is_active)
        VALUES (%s, %s, %s, %s, %s)
    ''', ('admin', 'admin@example.com', 'admin123', 'admin', True))
    # Insert sample car if not exists
    cursor.execute('''
        INSERT IGNORE INTO cars (make, model, price_per_day, status, image)
        VALUES (%s, %s, %s, %s, %s)
    ''', ('Toyota', 'Camry', 50.0, 'Available', 'toyota_camry.jpg'))
    mysql.connection.commit()
    cursor.close()

# Authentication Routes
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT id, username, email, role, is_active, password FROM users WHERE username = %s', (form.username.data,))
        user = cursor.fetchone()
        cursor.close()
        if user and user['password'] == form.password.data:  # Use hashing in production
            user_obj = User(user['id'], user['username'], user['email'], user['role'], user['is_active'])
            login_user(user_obj)
            session['language'] = 'en'
            session['currency'] = 'USD'
            flash('Logged in successfully.', 'success')
            return redirect(url_for('home.dashboard'))
        flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))

# Home Routes
@home_bp.route('/')
@home_bp.route('/dashboard')
@login_required
def dashboard():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, make, model, price_per_day, status, image, featured FROM cars WHERE status = %s', ('Available',))
    cars = cursor.fetchall()
    cursor.close()
    form = FlaskForm()
    return render_template('dashboard.html', cars=cars, form=form)

# Car Routes
@cars_bp.route('/cars/manage')
@login_required
@admin_required
def manage():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, make, model, price_per_day, status, image, featured FROM cars ORDER BY make ASC LIMIT 10')
    cars = cursor.fetchall()
    cursor.close()
    form = FlaskForm()
    return render_template('manage_cars.html', cars=cars, exchange_rate=4100, form=form)

@cars_bp.route('/cars/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    form = CarForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO cars (make, model, price_per_day, status, image, featured)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (form.make.data, form.model.data, form.price_per_day.data, form.status.data, form.image.data, form.featured.data))
        mysql.connection.commit()
        cursor.close()
        flash('Car added successfully.', 'success')
        return redirect(url_for('cars.manage'))
    return render_template('add_car.html', form=form)

@cars_bp.route('/cars/edit/<int:car_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(car_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, make, model, price_per_day, status, image, featured FROM cars WHERE id = %s', (car_id,))
    car = cursor.fetchone()
    cursor.close()
    if not car:
        flash('Car not found.', 'danger')
        return redirect(url_for('cars.manage'))
    form = CarForm(data=car)
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        cursor.execute('''
            UPDATE cars SET make = %s, model = %s, price_per_day = %s, status = %s, image = %s, featured = %s
            WHERE id = %s
        ''', (form.make.data, form.model.data, form.price_per_day.data, form.status.data, form.image.data, form.featured.data, car_id))
        mysql.connection.commit()
        cursor.close()
        flash('Car updated successfully.', 'success')
        return redirect(url_for('cars.manage'))
    return render_template('edit_car.html', form=form, car=car)

@cars_bp.route('/cars/delete/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def delete(car_id):
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM cars WHERE id = %s', (car_id,))
    mysql.connection.commit()
    cursor.close()
    flash('Car deleted successfully.', 'success')
    return jsonify({'success': True})

@cars_bp.route('/cars/bulk_delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete():
    car_ids = request.form.getlist('car_ids')
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM cars WHERE id IN (%s)' % ','.join(['%s'] * len(car_ids)), tuple(car_ids))
    mysql.connection.commit()
    cursor.close()
    flash('Selected cars deleted successfully.', 'success')
    return jsonify({'success': True})

@cars_bp.route('/cars/toggle_featured/<int:car_id>', methods=['POST'])
@login_required
@admin_required
def toggle_featured(car_id):
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE cars SET featured = %s WHERE id = %s', (request.form.get('featured') == 'true', car_id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

@cars_bp.route('/cars/details/<int:car_id>')
@login_required
@admin_required
def details(car_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, make, model, price_per_day, status, image, featured FROM cars WHERE id = %s', (car_id,))
    car = cursor.fetchone()
    cursor.close()
    if not car:
        flash('Car not found.', 'danger')
        return redirect(url_for('cars.manage'))
    return render_template('car_details.html', car=car)

# User Routes
@users_bp.route('/users/manage')
@login_required
@admin_required
def manage():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, username, email, role, is_active, avatar FROM users ORDER BY username ASC LIMIT 10')
    users = cursor.fetchall()
    cursor.close()
    form = FlaskForm()
    return render_template('manage_users.html', users=users, form=form)

@users_bp.route('/users/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    form = UserForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        cursor.execute('''
            INSERT INTO users (username, email, password, role, is_active, avatar)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (form.username.data, form.email.data, form.password.data, form.role.data, form.is_active.data, form.avatar.data))
        mysql.connection.commit()
        cursor.close()
        flash('User added successfully.', 'success')
        return redirect(url_for('users.manage'))
    return render_template('add_user.html', form=form)

@users_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, username, email, role, is_active, avatar FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('users.manage'))
    form = UserForm(data=user)
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        cursor.execute('''
            UPDATE users SET username = %s, email = %s, password = %s, role = %s, is_active = %s, avatar = %s
            WHERE id = %s
        ''', (form.username.data, form.email.data, form.password.data or user['password'], form.role.data, form.is_active.data, form.avatar.data, user_id))
        mysql.connection.commit()
        cursor.close()
        flash('User updated successfully.', 'success')
        return redirect(url_for('users.manage'))
    return render_template('edit_user.html', form=form, user=user)

@users_bp.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete(user_id):
    if user_id == current_user.id:
        flash('Cannot delete your own account.', 'danger')
        return jsonify({'error': 'Cannot delete own account'}), 403
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
    mysql.connection.commit()
    cursor.close()
    flash('User deleted successfully.', 'success')
    return jsonify({'success': True})

@users_bp.route('/users/bulk_delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete():
    user_ids = request.form.getlist('user_ids')
    if str(current_user.id) in user_ids:
        flash('Cannot delete your own account.', 'danger')
        return jsonify({'error': 'Cannot delete own account'}), 403
    cursor = mysql.connection.cursor()
    cursor.execute('DELETE FROM users WHERE id IN (%s)' % ','.join(['%s'] * len(user_ids)), tuple(user_ids))
    mysql.connection.commit()
    cursor.close()
    flash('Selected users deleted successfully.', 'success')
    return jsonify({'success': True})

@users_bp.route('/users/toggle_status/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    if user_id == current_user.id:
        flash('Cannot modify your own account status.', 'danger')
        return jsonify({'error': 'Cannot modify own account'}), 403
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET is_active = %s WHERE id = %s', (request.form.get('action') == 'activate', user_id))
    mysql.connection.commit()
    cursor.close()
    flash(f'User {request.form.get("action")}d successfully.', 'success')
    return jsonify({'success': True})

@users_bp.route('/users/bulk_status', methods=['POST'])
@login_required
@admin_required
def bulk_status():
    user_ids = request.form.getlist('user_ids')
    if str(current_user.id) in user_ids:
        flash('Cannot modify your own account status.', 'danger')
        return jsonify({'error': 'Cannot modify own account'}), 403
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE users SET is_active = %s WHERE id IN (%s)' % ','.join(['%s'] * len(user_ids)), (request.form.get('action') == 'activate',) + tuple(user_ids))
    mysql.connection.commit()
    cursor.close()
    flash(f'Selected users {request.form.get("action")}d successfully.', 'success')
    return jsonify({'success': True})

@users_bp.route('/users/details/<int:user_id>')
@login_required
@admin_required
def details(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, username, email, role, is_active, avatar FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('users.manage'))
    return render_template('user_details.html', user=user)

# Handover Routes
@handovers_bp.route('/handovers')
@login_required
@staff_required
def manage():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT b.id, b.user_id, b.car_id, b.start_date, b.end_date, b.status, b.penalty_amount, u.username, c.make, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id ORDER BY b.start_date DESC LIMIT 10')
    handovers = cursor.fetchall()
    cursor.close()
    form = FlaskForm()
    return render_template('manage_handovers.html', handovers=handovers, form=form)

@handovers_bp.route('/handovers/process/<int:booking_id>', methods=['POST'])
@login_required
@staff_required
def process(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, user_id, car_id, status FROM bookings WHERE id = %s', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    if not booking:
        flash('Booking not found.', 'danger')
        return jsonify({'error': 'Booking not found'}), 404
    action = request.form.get('action')
    valid_transitions = {
        'Pending': ['Handed Over'],
        'Handed Over': ['Returned'],
        'Returned': ['Inspected']
    }
    if action not in valid_transitions.get(booking['status'], []):
        flash('Invalid action for current status.', 'danger')
        return jsonify({'error': 'Invalid action'}), 400
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE bookings SET status = %s WHERE id = %s', (action.replace('_', ' ').title(), booking_id))
    if action == 'handed_over':
        cursor.execute('UPDATE cars SET status = %s WHERE id = %s', ('Rented', booking['car_id']))
    elif action == 'inspected':
        cursor.execute('UPDATE cars SET status = %s WHERE id = %s', ('Available', booking['car_id']))
    mysql.connection.commit()
    cursor.close()
    flash(f'Booking marked as {action.replace("_", " ").title()}.', 'success')
    return jsonify({'success': True})

@handovers_bp.route('/handovers/bulk_action', methods=['POST'])
@login_required
@staff_required
def bulk_action():
    booking_ids = request.form.getlist('booking_ids')
    action = request.form.get('action')
    valid_status = 'Pending' if action == 'handover' else 'Handed Over' if action == 'return' else None
    if not valid_status:
        flash('Invalid bulk action.', 'danger')
        return jsonify({'error': 'Invalid action'}), 400
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, user_id, car_id, status FROM bookings WHERE id IN (%s) AND status = %s' % ','.join(['%s'] * len(booking_ids)), tuple(booking_ids) + (valid_status,))
    bookings = cursor.fetchall()
    cursor.close()
    cursor = mysql.connection.cursor()
    for booking in bookings:
        cursor.execute('UPDATE bookings SET status = %s WHERE id = %s', (action.replace('_', ' ').title(), booking['id']))
        if action == 'handover':
            cursor.execute('UPDATE cars SET status = %s WHERE id = %s', ('Rented', booking['car_id']))
        elif action == 'return':
            cursor.execute('UPDATE cars SET status = %s WHERE id = %s', ('Available', booking['car_id']))
    mysql.connection.commit()
    cursor.close()
    flash(f'Selected bookings marked as {action.replace("_", " ").title()}.', 'success')
    return jsonify({'success': True})

@handovers_bp.route('/handovers/add_penalty/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@staff_required
def add_penalty(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, user_id, car_id, status, penalty_amount FROM bookings WHERE id = %s', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    if not booking or booking['status'] != 'Returned':
        flash('Can only add penalties for returned bookings.', 'danger')
        return redirect(url_for('handovers.manage'))
    form = PenaltyForm()
    if form.validate_on_submit():
        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE bookings SET penalty_amount = %s WHERE id = %s', (form.penalty_amount.data, booking_id))
        mysql.connection.commit()
        cursor.close()
        flash('Penalty recorded successfully.', 'success')
        return redirect(url_for('handovers.manage'))
    return render_template('add_penalty.html', form=form, booking=booking)

@handovers_bp.route('/bookings/details/<int:booking_id>')
@login_required
@staff_required
def details(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT b.id, b.user_id, b.car_id, b.start_date, b.end_date, b.status, b.penalty_amount, u.username, c.make, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id WHERE b.id = %s', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('handovers.manage'))
    return render_template('booking_details.html', booking=booking)

# Booking Routes
@bookings_bp.route('/booking/after/<int:booking_id>')
@login_required
def after_booking(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT b.id, b.user_id, b.car_id, b.start_date, b.end_date, b.status, b.penalty_amount, u.username, c.make, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id WHERE b.id = %s', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('home.dashboard'))
    form = FlaskForm()
    return render_template('after_booking.html', booking=booking, form=form)

@bookings_bp.route('/payment/process/<int:booking_id>', methods=['POST'])
@login_required
def process_payment(booking_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT b.id, b.user_id, b.car_id, b.start_date, b.end_date, b.status, c.price_per_day FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.id = %s', (booking_id,))
    booking = cursor.fetchone()
    cursor.close()
    if not booking or booking['status'] != 'Pending':
        flash('Booking already processed.', 'danger')
        return jsonify({'error': 'Invalid booking status'}), 400
    payment_method = request.form.get('payment_method')
    # Calculate amount (price_per_day * days)
    start_date = booking['start_date']
    end_date = booking['end_date']
    days = (end_date - start_date).days if isinstance(start_date, datetime) else 1
    amount = booking['price_per_day'] * days
    cursor = mysql.connection.cursor()
    cursor.execute('UPDATE bookings SET status = %s WHERE id = %s', ('Handed Over', booking_id))
    cursor.execute('UPDATE cars SET status = %s WHERE id = %s', ('Rented', booking['car_id']))
    cursor.execute('INSERT INTO payments (booking_id, payment_method, amount) VALUES (%s, %s, %s)', (booking_id, payment_method, amount))
    mysql.connection.commit()
    cursor.close()
    flash('Payment processed successfully.', 'success')
    return jsonify({'success': True})

@bookings_bp.route('/booking/create', methods=['POST'])
@login_required
def create_booking():
    car_id = request.form.get('car_id')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT id, make, model, status FROM cars WHERE id = %s AND status = %s', (car_id, 'Available'))
    car = cursor.fetchone()
    cursor.close()
    if not car:
        flash('Car is not available.', 'danger')
        return redirect(url_for('home.dashboard'))
    try:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        if start_date < datetime.now() or end_date <= start_date:
            flash('Invalid date range.', 'danger')
            return redirect(url_for('home.dashboard'))
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('home.dashboard'))
    cursor = mysql.connection.cursor()
    cursor.execute('''
        INSERT INTO bookings (user_id, car_id, start_date, end_date, status)
        VALUES (%s, %s, %s, %s, %s)
    ''', (current_user.id, car_id, start_date, end_date, 'Pending'))
    mysql.connection.commit()
    cursor.close()
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT LAST_INSERT_ID() AS id')
    booking_id = cursor.fetchone()['id']
    cursor.close()
    flash('Booking created successfully.', 'success')
    return redirect(url_for('bookings.after_booking', booking_id=booking_id))

# Language Routes
@lang_bp.route('/language', methods=['GET', 'POST'])
@login_required
def language():
    if request.method == 'POST':
        session['language'] = request.form.get('language', 'en')
        session['currency'] = request.form.get('currency', 'USD')
        flash('Language and currency updated.', 'success')
        return redirect(request.referrer or url_for('home.dashboard'))
    return render_template('language.html')

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(cars_bp)
app.register_blueprint(users_bp)
app.register_blueprint(handovers_bp)
app.register_blueprint(lang_bp)
app.register_blueprint(bookings_bp)

# Initialize Database
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True)