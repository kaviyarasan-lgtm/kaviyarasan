from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'college_secret_key_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///college_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ------------------ DATABASE MODELS ------------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    reg_no = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False) # student, staff, hod, principal

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student_name = db.Column(db.String(100))
    request_type = db.Column(db.String(50))
    reason = db.Column(db.String(200))
    # Workflow Status: Pending -> Staff Approved -> HOD Approved -> Approved
    status = db.Column(db.String(30), default="Pending")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ ROUTES ------------------

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        name = request.form.get('name')
        reg_no = request.form.get('reg_no')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        user_exists = User.query.filter((User.email == email) | (User.reg_no == reg_no)).first()
        if user_exists:
            flash("User already exists!")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, reg_no=reg_no, email=email, password=hashed_pw, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration Successful! Please Login.")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Invalid Credentials!")
    return render_template("login.html")

@app.route('/dashboard')
@login_required
def dashboard():
    # Filtering based on Role and Status
    if current_user.role == "student":
        apps = Application.query.filter_by(student_id=current_user.id).all()
    elif current_user.role == "staff":
        apps = Application.query.filter_by(status="Pending").all()
    elif current_user.role == "hod":
        apps = Application.query.filter_by(status="Staff Approved").all()
    elif current_user.role == "principal":
        apps = Application.query.filter_by(status="HOD Approved").all()
    else:
        apps = []
    
    return render_template("dashboard.html", apps=apps)

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        new_app = Application(
            student_id=current_user.id,
            student_name=current_user.name,
            request_type=request.form.get('request_type'),
            reason=request.form.get('reason')
        )
        db.session.add(new_app)
        db.session.commit()
        flash("Application submitted to Staff!")
        return redirect(url_for('dashboard'))
    return render_template("apply.html")

@app.route('/action/<int:id>/<string:action_type>')
@login_required
def action(id, action_type):
    app_req = Application.query.get_or_404(id)

    if action_type == 'approve':
        if current_user.role == 'staff' and app_req.status == 'Pending':
            app_req.status = 'Staff Approved'
        elif current_user.role == 'hod' and app_req.status == 'Staff Approved':
            app_req.status = 'HOD Approved'
        elif current_user.role == 'principal' and app_req.status == 'HOD Approved':
            app_req.status = 'Approved'
        else:
            flash("You don't have permission for this step!")
            return redirect(url_for('dashboard'))
    
    elif action_type == 'reject':
        app_req.status = 'Rejected'
    
    db.session.commit()
    flash(f"Status Updated: {app_req.status}")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)