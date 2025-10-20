from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = "secret-key"

# ========== MySQL Config ==========
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'demo_classa'

mysql = MySQL(app)

# ========== Routes ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cars')
def cars():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cars")  # Assuming table `cars`
    car_list = cur.fetchall()
    cur.close()
    return render_template('cars.html', cars=car_list)

@app.route('/car/<int:id>')
def car_details(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM cars WHERE id=%s", (id,))
    car = cur.fetchone()
    cur.close()
    return render_template('car-details.html', car=car)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form['name']
        car_id = request.form['car_id']
        date = request.form['date']
        # Save to database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO bookings(name, car_id, date) VALUES(%s, %s, %s)", (name, car_id, date))
        mysql.connection.commit()
        cur.close()
        flash("Booking successful!")
        return redirect(url_for('index'))
    return render_template('booking.html')

if __name__ == "__main__":
    app.run(debug=True)
