from flask import Flask, request, redirect, url_for, session
from flask_mysqldb import MySQL
from datetime import datetime, date
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

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

# Default Language
@app.before_request
def before_request():
    if 'lang' not in session:
        session['lang'] = 'km'

# ==================== Language Switcher ====================
@app.route('/lang/<lang>')
def change_lang(lang):
    session['lang'] = 'km' if lang == 'km' else 'en'
    return redirect(request.referrer or '/')

# ==================== Flash Messages ====================
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

# ==================== Navbar ====================
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
        'admin': "ផ្ទាំងគ្រប់គ្រង" if lang == 'km' else "Admin"
    }

    if 'user_id' in session:
        user_menu = f'''
            <li class="nav-item dropdown">
                <a class="nav-link dropdown-toggle" href="#" data-bs-toggle="dropdown">{session.get('name')}</a>
                <ul class="dropdown-menu dropdown-menu-end">
                    <li><a class="dropdown-item" href="/my-bookings">{txt['mybook']}</a></li>
                    {f'<li><a class="dropdown-item" href="/admin">{txt["admin"]}</a></li>' if session.get('role') == 'admin' else ''}
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

# ==================== Base Layout ====================
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
    txt = "ស្វាគមន៍មកកាន់ Car Rental System" if lang == 'km' else "Welcome to Car Rental System"
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
    txt = "ចូលប្រើប្រព័ន្ធ" if lang == 'km' else "Login"
    content = f'''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h3>{txt}</h3></div>
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
            session['_flashes'] = [('success', 'ចុះឈ្មោះជោគជ័យ! សូមចូលប្រើ។')]
            return redirect('/login')
        except Exception as e:
            if 'Duplicate entry' in str(e):
                session['_flashes'] = [('danger', 'អ៊ីមែលនេះមានរួចហើយ។')]
            else:
                session['_flashes'] = [('danger', 'មានបញ្ហាក្នុងការចុះឈ្មោះ។')]
        finally:
            cur.close()
    lang = session.get('lang', 'km')
    txt = "ចុះឈ្មោះ" if lang == 'km' else "Register"
    content = f'''
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header"><h3>{txt}</h3></div>
                <div class="card-body">
                    <form method="POST">
                        <div class="mb-3"><label>ឈ្មោះ</label><input type="text" name="name" class="form-control" required></div>
                        <div class="mb-3"><label>អ៊ីមែល</label><input type="email" name="email" class="form-control" required></div>
                        <div class="mb-3"><label>ពាក្យសម្ងាត់</label><input type="password" name="password" class="form-control" required></div>
                        <div class="mb-3"><label>លេខទូរស័ព្ទ</label><input type="text" name="phone" class="form-control" required></div>
                        <button type="submit" class="btn btn-success w-100">ចុះឈ្មោះ</button>
                    </form>
                    <p class="text-center mt-3">មានគណនីរួចហើយ? <a href="/login">ចូលប្រើ</a></p>
                </div>
            </div>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/logout')
def logout():
    session.clear()
    session['_flashes'] = [('info', 'អ្នកបានចាកចេញដោយជោគជ័យ។')]
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
    txt_used = "ប្រើ" if lang == 'km' else "Used"
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
                    <p class="small text-muted">{txt_used}: {p['used_count']} / {limit}</p>
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
    txt_book = "កក់" if lang == 'km' else "Book"
    txt_start = "ថ្ងៃចាប់ផ្តើម" if lang == 'km' else "Start Date"
    txt_end = "ថ្ងៃបញ្ចប់" if lang == 'km' else "End Date"
    txt_promo = "កូដផ្សព្វផ្សាយ" if lang == 'km' else "Promo Code"
    txt_confirm = "បញ្ជាក់ការកក់" if lang == 'km' else "Confirm Booking"
    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        promo_code = request.form.get('promo_code', '').strip()
        cur.execute("SELECT * FROM bookings WHERE car_id = %s AND status IN ('confirmed', 'pending') AND (%s BETWEEN start_date AND end_date OR %s BETWEEN start_date AND end_date)", (car_id, start_date, end_date))
        if cur.fetchone():
            session['_flashes'] = [('danger', 'រថយន្តនេះមានការកក់រួចហើយ។')]
            cur.close()
            return redirect(f'/book/{car_id}')
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
        session['_flashes'] = [('success', 'ការកក់ជោគជ័យ! សូមបង់ប្រាក់។')]
        return redirect(f'/payment/{booking_id}')
    cur.close()
    content = f'''
    <div class="row">
        <div class="col-md-6">
            <img src="{car['image'] or '/static/img/car-placeholder.jpg'}" class="img-fluid rounded" style="max-height:300px;">
        </div>
        <div class="col-md-6">
            <h2>{txt_book}: {car['model']}</h2>
            <p><strong>តម្លៃ:</strong> ${car['price_per_day']}/ថ្ងៃ</p>
            <form method="POST">
                <div class="mb-3"><label>{txt_start}</label><input type="date" name="start_date" class="form-control" required></div>
                <div class="mb-3"><label>{txt_end}</label><input type="date" name="end_date" class="form-control" required></div>
                <div class="mb-3"><label>{txt_promo}</label><input type="text" name="promo_code" class="form-control" placeholder="ABC123"></div>
                <button type="submit" class="btn btn-success">{txt_confirm}</button>
            </form>
        </div>
    </div>
    '''
    return base_layout(content)

@app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
@login_required()
def payment(booking_id):
    cur = get_db().cursor()
    cur.execute("SELECT b.*, c.model, c.image FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.id = %s AND b.user_id = %s AND b.status = 'pending'", (booking_id, session['user_id']))
    booking = cur.fetchone()
    if not booking:
        session['_flashes'] = [('danger', 'ការកក់មិនមាន ឬត្រូវបានបង់រួចហើយ។')]
        cur.close()
        return redirect('/')
    lang = session.get('lang', 'km')
    txt_pay = "បង់ប្រាក់" if lang == 'km' else "Pay"
    if request.method == 'POST':
        method = request.form['payment_method']
        cur.execute("INSERT INTO payments (booking_id, amount, method, status) VALUES (%s, %s, %s, 'completed')", (booking_id, booking['total_amount'], method))
        cur.execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
        get_db().commit()
        cur.close()
        session['_flashes'] = [('success', 'បង់ប្រាក់ជោគជ័យ!')]
        return redirect('/my-bookings')
    cur.close()
    days = (booking['end_date'] - booking['start_date']).days + 1
    content = f'''
    <div class="card">
        <div class="card-header"><h3>{txt_pay}</h3></div>
        <div class="card-body">
            <p><strong>រថយន្ត:</strong> {booking['model']}</p>
            <p><strong>ចំនួនថ្ងៃ:</strong> {days}</p>
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
    cur.execute("SELECT b.*, c.model, c.image FROM bookings b JOIN cars c ON b.car_id = c.id WHERE b.user_id = %s ORDER BY b.created_at DESC", (session['user_id'],))
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
                        <img src="{b['image'] or '/static/img/car-placeholder.jpg'}" class="img-fluid rounded" style="max-height:100px;">
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

@app.route('/admin')
@login_required('admin')
def admin():
    cur = get_db().cursor()
    cur.execute("SELECT COUNT(*) AS total FROM users WHERE role = 'customer'"); cust = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM bookings"); book = cur.fetchone()['total']
    cur.execute("SELECT COUNT(*) AS total FROM cars WHERE status = 'available'"); car = cur.fetchone()['total']
    cur.close()
    content = f'''
    <h1>ផ្ទាំងគ្រប់គ្រង</h1>
    <div class="row g-4">
        <div class="col-md-4">
            <div class="card text-center bg-primary text-white">
                <div class="card-body">
                    <h3>{cust}</h3>
                    <p>អតិថិជន</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center bg-success text-white">
                <div class="card-body">
                    <h3>{book}</h3>
                    <p>ការកក់</p>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card text-center bg-warning text-dark">
                <div class="card-body">
                    <h3>{car}</h3>
                    <p>រថយន្ត</p>
                </div>
            </div>
        </div>
    </div>
    '''
    return base_layout(content)

# ==================== Run App ====================
if __name__ == '__main__':
    app.run(debug=True)