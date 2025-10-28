from flask import Flask, request, redirect, url_for, session, send_from_directory
from flask_mysqldb import MySQL
from datetime import datetime, date
import secrets
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# ==================== Upload Config ====================
UPLOAD_FOLDER = 'static/uploads/cars'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve uploaded files
@app.route('/uploads/cars/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ==================== MySQL Configuration ====================
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'demo_classa'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

def get_db():
    return mysql.connection

# ==================== Helper Functions ====================
def login_required(role=None):
    def decorator(f):
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                session['_flashes'] = [('warning', 'សូមចូលប្រើប្រព័ន្ធជាមុន!')]
                return redirect('/login')
            if role and session.get('role') != role:
                session['_flashes'] = [('danger', 'អ្នកមិនមានសិទ្ធិចូលប្រើទំព័រនេះទេ។')]
                return redirect('/')
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

@app.before_request
def before_request():
    if 'lang' not in session:
        session['lang'] = 'km'

@app.route('/lang/<lang>')
def change_lang(lang):
    session['lang'] = 'km' if lang == 'km' else 'en'
    return redirect(request.referrer or '/')

def get_flash():
    messages = session.pop('_flashes', []) if '_flashes' in session else []
    html = ''
    for category, msg in messages:
        html += f'''
        <div class="alert alert-{category} alert-dismissible fade show mt-3">
            {msg}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        '''
    return html

def get_navbar():
    lang = session.get('lang', 'km')
    txt = {
        'home': "ទំព័រដើម" if lang == 'km' else "Home",
        'cars': "រថយន្ត" if lang == 'km' else "Cars",
        'promo': "ផ្សព្វផ្សាយ" if lang == 'km' else "Promotions",
        'login': "ចូលប្រើ" if lang == 'km' else "Login",
        'register': "ចុះឈ្មោះ" if lang == 'km' else "Register",
        'logout': "ចាកចេញ" if lang == 'km' else "Logout",
        'mybook': "ការកក់របស់ខ្ញុំ" if lang == 'km' else "My Bookings",
        'admin': "ផ្ទាំងគ្រប់គ្រង" if lang == 'km' else "Admin",
        'staff': "បុគ្គលិក" if lang == 'km' else "Staff"
    }

    user_menu = ''
    if 'user_id' in session:
        user_menu = f'''
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">{session.get('name')}</a>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="/my-bookings">{txt['mybook']}</a></li>
                    {f'<li><a class="dropdown-item" href="/admin">{txt["admin"]}</a></li>' if session.get('role') == 'admin' else ''}
                    {f'<li><a class="dropdown-item" href="/staff">{txt["staff"]}</a></li>' if session.get('role') == 'staff' else ''}
                    <li><a class="dropdown-item" href="/reset-password">កំណត់ពាក្យសម្ងាត់ឡើងវិញ</a></li>
                    <li><hr class="dropdown-divider"></li>
                    <li><a class="dropdown-item text-danger" href="/logout">{txt['logout']}</a></li>
                </ul>
            </li>
        '''
    else:
        user_menu = f'''
            <li class="nav-item"><a class="nav-link" href="/login">{txt['login']}</a></li>
            <li class="nav-item"><a class="nav-link" href="/register">{txt['register']}</a></li>
        '''

    return f'''
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary sticky-top">
        <div class="container">
            <a class="navbar-brand fw-bold" href="/">🚗 Car Rental</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="nav">
                <ul class="navbar-nav me-auto">
                    <li class="nav-item"><a class="nav-link" href="/">{txt['home']}</a></li>
                    <li class="nav-item"><a class="nav-link" href="/cars">{txt['cars']}</a></li>
                    <li class="nav-item"><a class="nav-link" href="/promotions">{txt['promo']}</a></li>
                </ul>
                <ul class="navbar-nav">
                    {user_menu}
                    <li class="nav-item dropdown ms-2">
                        <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">
                            {"ខ្មែរ" if lang == 'km' else "EN"}
                        </a>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="/lang/km">ភាសាខ្មែរ</a></li>
                            <li><a class="dropdown-item" href="/lang/en">English</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>
    '''

def base_layout(content):
    return f'''
    <!DOCTYPE html>
    <html lang="{session.get('lang', 'km')}">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Car Rental System</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" rel="stylesheet">
    </head>
    <body class="d-flex flex-column min-vh-100">
        {get_navbar()}
        <div class="container">
            {get_flash()}
        </div>
        <main class="container flex-grow-1 my-4">
            {content}
        </main>
        <footer class="bg-dark text-light py-3 mt-auto">
            <div class="container text-center">
                © {datetime.now().year} Car Rental System
                {" | " + session.get('name', '') if 'user_id' in session else ""}
            </div>
        </footer>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    '''

# ==================== Routes ====================

@app.route('/')
def index():
    lang = session.get('lang', 'km')
    txt = "ស្វាគមន៍មកកាន់ Car Rental System" if lang == 'km' else "Welcome"
    content = f'''
    <div class="text-center py-5">
        <h1 class="display-4">🚗 {txt}</h1>
        <p class="lead">ជួលរថយន្តងាយស្រួល តម្លែត្រឹមត្រូវ</p>
        <a href="/cars" class="btn btn-primary btn-lg">មើលរថយន្ត</a>
    </div>
    '''
    return base_layout(content)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cur = get_db().cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            session['_flashes'] = [('success', f"ស្វាគមន៍ {user['name']}!")]
            return redirect('/')
        session['_flashes'] = [('danger', 'អ៊ីមែល ឬ ពាក្យសម្ងាត់មិនត្រឹមត្រូវ។')]
    lang = session.get('lang', 'km')
    content = f'''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h3>ចូលប្រើ</h3></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3"><label>អ៊ីមែល</label><input type="email" name="email" class="form-control" required></div>
                        <div class="mb-3"><label>ពាក្យសម្ងាត់</label><input type="password" name="password" class="form-control" required></div>
                        <button type="submit" class="btn btn-primary w-100">ចូលប្រើ</button>
                    </form>
                    <p class="text-center mt-3">មិនទាន់មានគណនី? <a href="/register">ចុះឈ្មោះ</a></p>
                </div>
            </div>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        cur = get_db().cursor()
        try:
            cur.execute("INSERT INTO users (name, email, password, phone, role) VALUES (%s, %s, %s, %s, 'customer')",
                        (name, email, password, phone))
            get_db().commit()
            session['_flashes'] = [('success', 'ចុះឈ្មោះជោគជ័យ!')]
            return redirect('/login')
        except:
            session['_flashes'] = [('danger', 'អ៊ីមែលមានរួចហើយ។')]
        finally:
            cur.close()
    lang = session.get('lang', 'km')
    content = f'''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h3>ចុះឈ្មោះ</h3></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3"><label>ឈ្មោះ</label><input type="text" name="name" class="form-control" required></div>
                        <div class="mb-3"><label>អ៊ីមែល</label><input type="email" name="email" class="form-control" required></div>
                        <div class="mb-3"><label>ពាក្យសម្ងាត់</label><input type="password" name="password" class="form-control" required></div>
                        <div class="mb-3"><label>លេខទូរស័ព្ទ</label><input type="text" name="phone" class="form-control" required></div>
                        <button type="submit" class="btn btn-success w-100">ចុះឈ្មោះ</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/logout')
def logout():
    session.clear()
    session['_flashes'] = [('info', 'ចាកចេញជោគជ័យ។')]
    return redirect('/')

@app.route('/cars')
def cars():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM cars WHERE status = 'available'")
    cars_list = cur.fetchall()
    cur.close()
    lang = session.get('lang', 'km')
    txt_title = "រថយន្តសម្រាប់ជួល" if lang == 'km' else "Available Cars"
    txt_price = "តម្លៃ" if lang == 'km' else "Price"
    txt_day = "ថ្ងៃ" if lang == 'km' else "day"
    txt_book = "កក់" if lang == 'km' else "Book"
    cars_html = ''
    for car in cars_list:
        image = car['image'] or '/static/img/car-placeholder.jpg'
        cars_html += f'''
        <div class="col-md-4 mb-4">
            <div class="card h-100">
                <img src="{image}" class="card-img-top" style="height:200px; object-fit:cover;">
                <div class="card-body d-flex flex-column">
                    <h5 class="card-title">{car['model']}</h5>
                    <p class="card-text"><strong>{txt_price}:</strong> ${car['price_per_day']}/{txt_day}</p>
                    <a href="/book/{car['id']}" class="btn btn-primary mt-auto">{txt_book}</a>
                </div>
            </div>
        </div>
        '''
    content = f'''
    <h1>{txt_title}</h1>
    <div class="row g-4">
        {cars_html or '<p class="text-muted">មិនមានរថយន្តទេ។</p>'}
    </div>
    '''
    return base_layout(content)

@app.route('/promotions')
def promotions():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM promotions WHERE active = 1 AND (expiry_date IS NULL OR expiry_date >= CURDATE())")
    promo_list = cur.fetchall()
    cur.close()
    lang = session.get('lang', 'km')
    txt_title = "ការផ្សព្វផ្សាយ" if lang == 'km' else "Promotions"
    txt_copy = "Copy" if lang == 'km' else "Copy"
    promo_html = ''
    for p in promo_list:
        limit = p['usage_limit'] or ("គ្មានកំណត់" if lang == 'km' else "Unlimited")
        promo_html += f'''
        <div class="col-md-4 mb-4">
            <div class="card text-center h-100">
                <div class="card-body">
                    <h3 class="text-danger">- {p['discount']}%</h3>
                    <h5>{p['code']}</h5>
                    <p class="small text-muted">ប្រើ: {p['used_count']} / {limit}</p>
                    <button class="btn btn-outline-primary" onclick="navigator.clipboard.writeText('{p['code']}')">{txt_copy}</button>
                </div>
            </div>
        </div>
        '''
    content = f'''
    <h1>{txt_title}</h1>
    <div class="row g-4">
        {promo_html or '<p class="text-muted">មិនមានកូដផ្សព្វផ្សាយទេ។</p>'}
    </div>
    '''
    return base_layout(content)

@app.route('/book/<int:car_id>', methods=['GET', 'POST'])
@login_required()
def book(car_id):
    cur = get_db().cursor()
    cur.execute("SELECT * FROM cars WHERE id = %s", (car_id,))
    car = cur.fetchone()
    if not car:
        session['_flashes'] = [('danger', 'រថយន្តមិនមានទេ។')]
        cur.close()
        return redirect('/cars')
    lang = session.get('lang', 'km')
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        promo_code = request.form.get('promo_code', '').strip()
        days = (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days + 1
        subtotal = days * car['price_per_day']
        discount = 0
        promo = None
        if promo_code:
            cur.execute("SELECT * FROM promotions WHERE code = %s AND active = 1", (promo_code,))
            promo = cur.fetchone()
            if promo and (promo['expiry_date'] is None or promo['expiry_date'] >= date.today()) and (promo['usage_limit'] is None or promo['used_count'] < promo['usage_limit']):
                discount = (subtotal * promo['discount']) / 100
                cur.execute("UPDATE promotions SET used_count = used_count + 1 WHERE id = %s", (promo['id'],))
        total = subtotal - discount
        cur.execute("INSERT INTO bookings (user_id, car_id, start_date, end_date, total_amount, status, promo_id) VALUES (%s, %s, %s, %s, %s, 'pending', %s)", (session['user_id'], car_id, start_date, end_date, total, promo['id'] if promo else None))
        booking_id = cur.lastrowid
        get_db().commit()
        cur.close()
        session['_flashes'] = [('success', 'ការកក់ជោគជ័យ!')]
        return redirect(f'/payment/{booking_id}')
    cur.close()
    content = f'''
    <div class="row">
        <div class="col-md-6">
            <img src="{car['image'] or '/static/img/car-placeholder.jpg'}" class="img-fluid rounded" style="max-height:300px;">
        </div>
        <div class="col-md-6">
            <h2>កក់: {car['model']}</h2>
            <p><strong>តម្លៃ:</strong> ${car['price_per_day']}/ថ្ងៃ</p>
            <form method="POST">
                <div class="mb-3"><label>ថ្ងៃចាប់ផ្តើម</label><input type="date" name="start_date" class="form-control" required></div>
                <div class="mb-3"><label>ថ្ងៃបញ្ចប់</label><input type="date" name="end_date" class="form-control" required></div>
                <div class="mb-3"><label>កូដផ្សព្វផ្សាយ</label><input type="text" name="promo_code" class="form-control" placeholder="ABC123"></div>
                <button type="submit" class="btn btn-success">បញ្ជាក់ការកក់</button>
            </form>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required()
def payment(booking_id):
    cur = get_db().cursor()
    cur.execute("SELECT b.*, c.model FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.id = %s AND b.user_id = %s AND b.status = 'pending'", (booking_id, session['user_id']))
    booking = cur.fetchone()
    if not booking:
        session['_flashes'] = [('danger', 'ការកក់មិនមាន។')]
        cur.close()
        return redirect('/')
    if request.method == 'POST':
        method = request.form['payment_method']
        cur.execute("INSERT INTO payments (booking_id, amount, method, status) VALUES (%s, %s, %s, 'completed')", (booking_id, booking['total_amount'], method))
        cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
        get_db().commit()
        cur.close()
        session['_flashes'] = [('success', 'បង់ប្រាក់ជោគជ័យ!')]
        return redirect('/my-bookings')
    cur.close()
    content = f'''
    <div class="card">
        <div class="card-header"><h3>បង់ប្រាក់</h3></div>
        <div class="card-body">
            <p><strong>រថយន្ត:</strong> {booking['model']}</p>
            <p><strong>សរុប:</strong> ${booking['total_amount']}</p>
            <form method="POST">
                <div class="mb-3">
                    <label>វិធីបង់ប្រាក់</label>
                    <select name="payment_method" class="form-control">
                        <option value="ABA">ABA</option>
                        <option value="Wing">Wing</option>
                        <option value="Acleda">Acleda</option>
                        <option value="PayPal">PayPal</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-success w-100">បង់ប្រាក់</button>
            </form>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/my-bookings')
@login_required()
def my_bookings():
    cur = get_db().cursor()
    cur.execute("SELECT b.*, c.model FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s ORDER BY b.created_at DESC", (session['user_id'],))
    bookings = cur.fetchall()
    cur.close()
    lang = session.get('lang', 'km')
    txt_title = "ការកក់របស់ខ្ញុំ" if lang == 'km' else "My Bookings"
    booking_html = ''
    for b in bookings:
        status_badge = 'success' if b['status'] == 'confirmed' else 'warning'
        booking_html += f'''
        <div class="card mb-3">
            <div class="card-body">
                <div class="row">
                    <div class="col-md-3">
                        <img src="{b.get('image') or '/static/img/car-placeholder.jpg'}" class="img-fluid rounded" style="max-height:100px;">
                    </div>
                    <div class="col-md-9">
                        <h5>{b['model']}</h5>
                        <p><strong>ថ្ងៃ:</strong> {b['start_date']} → {b['end_date']}<br>
                        <strong>ស្ថានភាព:</strong> <span class="badge bg-{status_badge}">{b['status']}</span></p>
                    </div>
                </div>
            </div>
        </div>
        '''
    content = f'''
    <h1>{txt_title}</h1>
    {booking_html or '<p class="text-muted">មិនមានការកក់ទេ។</p>'}
    '''
    return base_layout(content)

@app.route('/reset-password', methods=['GET', 'POST'])
@login_required()
def reset_password():
    if request.method == 'POST':
        old = request.form['old_password']
        new = request.form['new_password']
        cur = get_db().cursor()
        cur.execute("SELECT password FROM users WHERE id = %s", (session['user_id'],))
        user = cur.fetchone()
        if user and user['password'] == old:
            cur.execute("UPDATE users SET password = %s WHERE id = %s", (new, session['user_id']))
            get_db().commit()
            session['_flashes'] = [('success', 'កំណត់ពាក្យសម្ងាត់ឡើងវិញជោគជ័យ!')]
        else:
            session['_flashes'] = [('danger', 'ពាក្យសម្ងាត់ចាស់មិនត្រឹមត្រូវ។')]
        cur.close()
        return redirect('/reset-password')
    content = f'''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h3>កំណត់ពាក្យសម្ងាត់ឡើងវិញ</h3></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3"><label>ពាក្យសម្ងាត់ចាស់</label><input type="password" name="old_password" class="form-control" required></div>
                        <div class="mb-3"><label>ពាក្យសម្ងាត់ថ្មី</label><input type="password" name="new_password" class="form-control" required></div>
                        <button type="submit" class="btn btn-primary w-100">កំណត់ឡើងវិញ</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    '''
    return base_layout(content)

# ==================== Admin Routes ====================

@app.route('/admin')
@login_required('admin')
def admin():
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'customer'"); cust = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM bookings"); book = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM cars"); car = cur.fetchone()['total']
    cur.close()
    content = f'''
    <h1 class="mb-4">ផ្ទាំងគ្រប់គ្រង (Admin)</h1>
    <div class="row g-4 mb-5">
        <div class="col-md-4">
            <div class="card text-center bg-primary text-white">
                <div class="card-body"><h3>{cust}</h3><p>អតិថិជន</p></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center bg-success text-white">
                <div class="card-body"><h3>{book}</h3><p>ការកក់</p></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center bg-warning text-dark">
                <div class="card-body"><h3>{car}</h3><p>រថយន្ត</p></div>
            </div>
        </div>
    </div>
    <h3>សកម្មភាពរហ័ស</h3>
    <div class="row">
        <div class="col-md-3"><a href="/admin/cars" class="btn btn-primary w-100 mb-2">គ្រប់គ្រងរថយន្ត</a></div>
        <div class="col-md-3"><a href="/admin/users" class="btn btn-info w-100 mb-2">គ្រប់គ្រងអ្នកប្រើ</a></div>
        <div class="col-md-3"><a href="/admin/bookings" class="btn btn-success w-100 mb-2">គ្រប់គ្រងការកក់</a></div>
    </div>
    '''
    return base_layout(content)

# កែតែ `admin_cars` route នេះ
@app.route('/admin/cars', methods=['GET', 'POST'])
@login_required('admin')
def admin_cars():
    cur = get_db().cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            model = request.form['model']
            price = request.form['price']
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path = f"/uploads/cars/{filename}"
            cur.execute("INSERT INTO cars (model, price_per_day, image, status) VALUES (%s, %s, %s, 'available')", (model, price, image_path))
        elif action == 'edit':
            car_id = request.form['car_id']
            model = request.form['model']
            price = request.form['price']
            cur.execute("UPDATE cars SET model = %s, price_per_day = %s WHERE id = %s", (model, price, car_id))
        elif action == 'delete':
            car_id = request.form['car_id']
            cur.execute("SELECT image FROM cars WHERE id = %s", (car_id,))
            img = cur.fetchone()['image']
            if img and os.path.exists(f".{img}"):
                os.remove(f".{img}")
            cur.execute("DELETE FROM cars WHERE id = %s", (car_id,))
        get_db().commit()
    cur.execute("SELECT * FROM cars")
    cars_list = cur.fetchall()
    cur.close()
    cars_html = ''
    for car in cars_list:
        img = car['image'] or '/static/img/car-placeholder.jpg'
        cars_html += f'''
        <tr>
            <td>{car['id']}</td>
            <td><img src="{img}" width="80" class="rounded"></td>
            <td>{car['model']}</td>
            <td>${car['price_per_day']}</td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="editCar({car['id']}, '{car['model']}', {car['price_per_day']})">កែ</button>
                <form method="POST" class="d-inline">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="car_id" value="{car['id']}">
                    <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('លុប?')">លុប</button>
                </form>
            </td>
        </tr>
        '''
    content = f'''
    <h1>គ្រប់គ្រងរថយន្ត</h1>
    <div class="card mb-4">
        <div class="card-body">
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="action" value="add">
                <div class="row g-3">
                    <div class="col-md-4"><input type="text" name="model" placeholder="ម៉ូដែល" class="form-control" required></div>
                    <div class="col-md-3"><input type="number" step="0.01" name="price" placeholder="តម្លៃ/ថ្ងៃ" class="form-control" required></div>
                    <div class="col-md-3"><input type="file" name="image" class="form-control" accept="image/*"></div>
                    <div class="col-md-2"><button type="submit" class="btn btn-success w-100">បន្ថែម</button></div>
                </div>
            </form>
        </div>
    </div>
    <table class="table table-striped">
        <thead><tr><th>ID</th><th>រូប</th><th>ម៉ូដែល</th><th>តម្លៃ</th><th>សកម្មភាព</th></tr></thead>
        <tbody>{cars_html}</tbody>
    </table>

    <script>
    function editCar(id, model, price) {{
        let newModel = prompt("កែម៉ូដែល:", model);
        let newPrice = prompt("កែតម្លៃ:", price);
        if (newModel && newPrice) {{
            let form = document.createElement('form');
            form.method = 'POST';
            form.innerHTML = `
                <input type="hidden" name="action" value="edit">
                <input type="hidden" name="car_id" value="${{id}}">
                <input type="hidden" name="model" value="${{newModel}}">
                <input type="hidden" name="price" value="${{newPrice}}">
            `;
            document.body.appendChild(form);
            form.submit();
        }}
    }}
    </script>
    '''
    return base_layout(content)

@app.route('/admin/users')
@login_required('admin')
def admin_users():
    cur = get_db().cursor()
    cur.execute("SELECT * FROM users WHERE role != 'admin'")
    users = cur.fetchall()
    cur.close()
    users_html = ''
    for u in users:
        role_text = 'អតិថិជន' if u['role'] == 'customer' else 'បុគ្គលិក'
        users_html += f'''
        <tr>
            <td>{u['id']}</td>
            <td>{u['name']}</td>
            <td>{u['email']}</td>
            <td>{role_text}</td>
            <td>
                <a href="/admin/user/role/{u['id']}" class="btn btn-sm btn-info">ប្តូរ Role</a>
                <form method="POST" action="/admin/user/delete/{u['id']}" class="d-inline">
                    <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('លុប?')">លុប</button>
                </form>
            </td>
        </tr>
        '''
    content = f'''
    <h1>គ្រប់គ្រងអ្នកប្រើ</h1>
    <table class="table table-hover">
        <thead class="table-dark"><tr><th>ID</th><th>ឈ្មោះ</th><th>អ៊ីមែល</th><th>Role</th><th>សកម្មភាព</th></tr></thead>
        <tbody>{users_html}</tbody>
    </table>
    '''
    return base_layout(content)

@app.route('/admin/user/role/<int:user_id>')
@login_required('admin')
def admin_change_role(user_id):
    cur = get_db().cursor()
    cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()
    new_role = 'staff' if user['role'] == 'customer' else 'customer'
    cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
    get_db().commit()
    cur.close()
    session['_flashes'] = [('success', 'ប្តូរ Role ជោគជ័យ!')]
    return redirect('/admin/users')

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required('admin')
def admin_delete_user(user_id):
    cur = get_db().cursor()
    cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
    get_db().commit()
    cur.close()
    session['_flashes'] = [('success', 'លុបអ្នកប្រើជោគជ័យ!')]
    return redirect('/admin/users')

@app.route('/admin/bookings')
@login_required('admin')
def admin_bookings():
    cur = get_db().cursor()
    cur.execute("SELECT b.*, u.name, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id ORDER BY b.created_at DESC")
    bookings = cur.fetchall()
    cur.close()
    booking_html = ''
    for b in bookings:
        booking_html += f'''
        <tr>
            <td>{b['id']}</td>
            <td>{b['name']}</td>
            <td>{b['model']}</td>
            <td>{b['start_date']} → {b['end_date']}</td>
            <td>${b['total_amount']}</td>
            <td>{b['status']}</td>
        </tr>
        '''
    content = f'''
    <h1>គ្រប់គ្រងការកក់</h1>
    <table class="table table-striped">
        <thead><tr><th>ID</th><th>អតិថិជន</th><th>រថយន្ត</th><th>ថ្ងៃ</th><th>សរុប</th><th>ស្ថានភាព</th></tr></thead>
        <tbody>{booking_html}</tbody>
    </table>
    '''
    return base_layout(content)

# ==================== Staff Routes ====================

@app.route('/staff')
@login_required('staff')
def staff_dashboard():
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) AS total FROM bookings WHERE status = 'pending'"); pending = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM bookings WHERE status = 'confirmed'"); active = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM cars WHERE status = 'available'"); avail = cur.fetchone()['total']
    cur.close()
    content = f'''
    <h1 class="mb-4">ផ្ទាំងបុគ្គលិក</h1>
    <div class="row g-4 mb-5">
        <div class="col-md-4">
            <div class="card text-center bg-warning text-dark">
                <div class="card-body"><h3>{pending}</h3><p>ការកក់រង់ចាំ</p></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center bg-success text-white">
                <div class="card-body"><h3>{active}</h3><p>កំពុងជួល</p></div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center bg-info text-white">
                <div class="card-body"><h3>{avail}</h3><p>រថយន្តទំនេរ</p></div>
            </div>
        </div>
    </div>
    <h3>សកម្មភាពរហ័ស</h3>
    <div class="row">
        <div class="col-md-3"><a href="/staff/cars" class="btn btn-primary w-100 mb-2">គ្រប់គ្រងរថយន្ត</a></div>
        <div class="col-md-3"><a href="/staff/bookings" class="btn btn-success w-100 mb-2">ការកក់</a></div>
        <div class="col-md-3"><a href="/staff/handover" class="btn btn-warning w-100 mb-2">ទទួលរថយន្ត</a></div>
        <div class="col-md-3"><a href="/staff/return" class="btn btn-danger w-100 mb-2">ត្រឡប់រថយន្ត</a></div>
    </div>
    '''
    return base_layout(content)

@app.route('/staff/cars', methods=['GET', 'POST'])
@login_required('staff')
def staff_cars():
    cur = get_db().cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            model = request.form['model']
            price = request.form['price']
            cur.execute("INSERT INTO cars (model, price_per_day, status) VALUES (%s, %s, 'available')", (model, price))
        elif action == 'delete':
            car_id = request.form['car_id']
            cur.execute("DELETE FROM cars WHERE id = %s", (car_id,))
        get_db().commit()
    cur.execute("SELECT * FROM cars")
    cars_list = cur.fetchall()
    cur.close()
    cars_html = ''
    for car in cars_list:
        cars_html += f'''
        <tr>
            <td>{car['id']}</td>
            <td>{car['model']}</td>
            <td>${car['price_per_day']}</td>
            <td><span class="badge bg-success">Available</span></td>
            <td>
                <form method="POST" class="d-inline">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="car_id" value="{car['id']}">
                    <button type="submit" class="btn btn-sm btn-danger" onclick="return confirm('លុប?')">លុប</button>
                </form>
            </td>
        </tr>
        '''
    content = f'''
    <h1>គ្រប់គ្រងរថយន្ត</h1>
    <div class="card mb-4">
        <div class="card-body">
            <form method="POST">
                <input type="hidden" name="action" value="add">
                <div class="row">
                    <div class="col-md-5"><input type="text" name="model" placeholder="ម៉ូដែល" class="form-control" required></div>
                    <div class="col-md-5"><input type="number" step="0.01" name="price" placeholder="តម្លៃ/ថ្ងៃ" class="form-control" required></div>
                    <div class="col-md-2"><button type="submit" class="btn btn-success w-100">បន្ថែម</button></div>
                </div>
            </form>
        </div>
    </div>
    <table class="table table-striped">
        <thead><tr><th>ID</th><th>ម៉ូដែល</th><th>តម្លៃ</th><th>ស្ថានភាព</th><th>សកម្មភាព</th></tr></thead>
        <tbody>{cars_html}</tbody>
    </table>
    '''
    return base_layout(content)

@app.route('/staff/bookings')
@login_required('staff')
def staff_bookings():
    cur = get_db().cursor()
    cur.execute("SELECT b.*, u.name, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id ORDER BY b.created_at DESC")
    bookings = cur.fetchall()
    cur.close()
    booking_html = ''
    for b in bookings:
        status = 'រង់ចាំ' if b['status'] == 'pending' else 'បញ្ជាក់'
        badge = 'warning' if b['status'] == 'pending' else 'success'
        confirm_btn = f'<form method="POST" action="/staff/confirm-payment/{b["id"]}" class="d-inline"><button type="submit" class="btn btn-sm btn-success">បញ្ជាក់</button></form>' if b['status'] == 'pending' else ''
        booking_html += f'''
        <tr>
            <td>{b['id']}</td>
            <td>{b['name']}</td>
            <td>{b['model']}</td>
            <td>{b['start_date']} → {b['end_date']}</td>
            <td>${b['total_amount']}</td>
            <td><span class="badge bg-{badge}">{status}</span></td>
            <td>{confirm_btn}</td>
        </tr>
        '''
    content = f'''
    <h1>ការកក់ទាំងអស់</h1>
    <table class="table table-hover">
        <thead class="table-dark"><tr><th>ID</th><th>អតិថិជន</th><th>រថយន្ត</th><th>ថ្ងៃ</th><th>សរុប</th><th>ស្ថានភាព</th><th>សកម្មភាព</th></tr></thead>
        <tbody>{booking_html}</tbody>
    </table>
    '''
    return base_layout(content)

@app.route('/staff/confirm-payment/<int:booking_id>', methods=['POST'])
@login_required('staff')
def staff_confirm_payment(booking_id):
    cur = get_db().cursor()
    cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s AND status = 'pending'", (booking_id,))
    if cur.rowcount:
        get_db().commit()
        session['_flashes'] = [('success', 'បញ្ជាក់ការបង់ប្រាក់ជោគជ័យ!')]
    cur.close()
    return redirect('/staff/bookings')

@app.route('/staff/handover/<int:booking_id>', methods=['GET', 'POST'])
@login_required('staff')
def staff_handover(booking_id):
    cur = get_db().cursor()
    cur.execute("SELECT b.*, u.name, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id WHERE b.id = %s AND b.status = 'confirmed'", (booking_id,))
    booking = cur.fetchone()
    if not booking:
        session['_flashes'] = [('danger', 'មិនមានការកក់នេះទេ។')]
        return redirect('/staff/bookings')
    if request.method == 'POST':
        notes = request.form['notes']
        cur.execute("UPDATE bookings SET handover_notes = %s, status = 'active' WHERE id = %s", (notes, booking_id))
        get_db().commit()
        session['_flashes'] = [('success', 'ទទួលរថយន្តជោគជ័យ!')]
        return redirect('/staff/bookings')
    cur.close()
    content = f'''
    <h1>ទទួលរថយន្ត</h1>
    <div class="card">
        <div class="card-body">
            <p><strong>អតិថិជន:</strong> {booking['name']}</p>
            <p><strong>រថយន្ត:</strong> {booking['model']}</p>
            <form method="POST">
                <div class="mb-3"><label>កំណត់ចំណាំ</label><textarea name="notes" class="form-control" rows="3"></textarea></div>
                <button type="submit" class="btn btn-success">បញ្ជាក់</button>
            </form>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/staff/return/<int:booking_id>', methods=['GET', 'POST'])
@login_required('staff')
def staff_return(booking_id):
    cur = get_db().cursor()
    cur.execute("SELECT b.*, u.name, c.model FROM bookings b JOIN users u ON b.user_id = u.id JOIN cars c ON b.car_id = c.id WHERE b.id = %s AND b.status = 'active'", (booking_id,))
    booking = cur.fetchone()
    if not booking:
        session['_flashes'] = [('danger', 'មិនមានការជួលនេះទេ។')]
        return redirect('/staff/bookings')
    if request.method == 'POST':
        damage = request.form.get('damage', '')
        penalty = request.form.get('penalty', '0')
        cur.execute("UPDATE bookings SET return_notes = %s, penalty = %s, status = 'returned' WHERE id = %s", (damage, penalty, booking_id))
        cur.execute("UPDATE cars SET status = 'available' WHERE id = %s", (booking['car_id'],))
        get_db().commit()
        session['_flashes'] = [('success', 'ត្រឡប់រថយន្តជោគជ័យ!')]
        return redirect('/staff/bookings')
    cur.close()
    content = f'''
    <h1>ត្រឡប់រថយន្ត</h1>
    <div class="card">
        <div class="card-body">
            <p><strong>អតិថិជន:</strong> {booking['name']}</p>
            <p><strong>រថយន្ត:</strong> {booking['model']}</p>
            <form method="POST">
                <div class="mb-3"><label>ខូចខាត</label><textarea name="damage" class="form-control" rows="3"></textarea></div>
                <div class="mb-3"><label>ប្រាក់ពិន័យ ($)</label><input type="number" step="0.01" name="penalty" class="form-control" value="0"></div>
                <button type="submit" class="btn btn-danger">បញ្ជាក់</button>
            </form>
        </div>
    </div>
    '''
    return base_layout(content)

# ==================== Run App ====================
if __name__ == '__main__':
    app.run(debug=True)