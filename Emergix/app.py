from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash  # Import hashing functions

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)  # Store the hash
    is_management = db.Column(db.Boolean, default=False)
    beds = db.relationship('Bed', backref='user', lazy=True)  # Add relationship for beds

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    city = db.Column(db.String(100), nullable=False)  # Add city
    beds = db.relationship('Bed', backref='hospital', lazy=True)

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    bed_type = db.Column(db.String(50), nullable=False)
    available = db.Column(db.Boolean, default=True)
    booked_by = db.Column(db.Integer, db.ForeignKey('user.id')) # Link to User
    booking_time = db.Column(db.DateTime)

# Create database tables (run this once)
with app.app_context():
    db.create_all()


# Routes
@app.route('/')
def index():
    return render_template('1stpage.html')

@app.route('/beds', methods=['GET', 'POST'])
def bed_availability():
    if not session.get('user_id'):
        return redirect(url_for('login'))

    hospitals = Hospital.query.all()
    cities = sorted(list(set([h.city for h in hospitals])))
    selected_city = request.form.get('city') if request.method == 'POST' else None

    if selected_city:
        hospitals = Hospital.query.filter_by(city=selected_city).all()

    return render_template('2ndpage.html', hospitals=hospitals, cities=cities, selected_city=selected_city)


@app.route('/hospital_details/<int:hospital_id>')
def hospital_details(hospital_id):
    hospital = Hospital.query.get_or_404(hospital_id)
    return render_template('hospital_details_page.html', hospital=hospital)

@app.route('/book/<int:bed_id>', methods=['POST'])
def book_bed(bed_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))

    bed = Bed.query.get_or_404(bed_id)
    if bed.available:
        bed.available = False
        bed.booked_by = session['user_id']
        bed.booking_time = datetime.now()
        db.session.commit()
        flash('Bed booked successfully!', 'success')
    else:
        flash('Bed is not available.', 'danger')
    return redirect(url_for('hospital_details', hospital_id=bed.hospital_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):  # Use check_password method
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_management'] = user.is_management
            return redirect(url_for('bed_availability'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html') 

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('is_management', None)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username)
        new_user.set_password(password) # Use set_password method
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Add Hospital (management only)

@app.route('/hospital_management', methods=['GET', 'POST'])
def hospital_management():
    if not session.get('is_management'):
        return redirect(url_for('index'))

    hospitals = Hospital.query.all()
    cities = sorted(list(set([h.city for h in hospitals]))) # Get unique cities
    selected_city = request.form.get('city') if request.method == 'POST' else None

    if selected_city:
        hospitals = Hospital.query.filter_by(city=selected_city).all()
    print(cities)  # Add this line
    return render_template('3rdpage.html', hospitals=hospitals, cities=cities, selected_city=selected_city)

@app.route('/add_hospital', methods=['GET', 'POST'])
def add_hospital():
    if not session.get('is_management'):
        return redirect(url_for('index'))

    city = request.args.get('city')
    if request.method == 'POST':
        name = request.form['name']
        new_hospital = Hospital(name=name, city=city)
        db.session.add(new_hospital)
        db.session.commit()
        return redirect(url_for('hospital_management', city=city))

    return render_template('add_hospital.html', city=city)


@app.route('/add_beds/<int:hospital_id>', methods=['GET', 'POST'])
def add_beds(hospital_id):
    if not session.get('is_management'):
        return redirect(url_for('index'))

    hospital = Hospital.query.get_or_404(hospital_id)
    if request.method == 'POST':
        bed_type = request.form['bed_type']
        num_beds = int(request.form['num_beds'])
        for _ in range(num_beds):
            new_bed = Bed(hospital_id=hospital_id, bed_type=bed_type)
            db.session.add(new_bed)
        db.session.commit()
        return redirect(url_for('hospital_details', hospital_id=hospital_id))

    return render_template('add_beds.html', hospital=hospital)

@app.route('/beds')
def redirect_to_management():
    if session.get('is_management'):
        return redirect(url_for('hospital_management'))
    else:
        return render_template('2ndpage.html')

if __name__ == '__main__':
    app.run(debug=True)