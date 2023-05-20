from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
import re
import hashlib
from datetime import datetime, timedelta
from flask_login import LoginManager, UserMixin, login_user, current_user, login_required
from flask_principal import Principal, Permission, identity_loaded, UserNeed, RoleNeed

app = Flask(__name__)

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'khoaluandb.cx4dxwmzciis.ap-southeast-1.rds.amazonaws.com'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = '1709hung2000'
app.config['MYSQL_DB'] = 'khoaluan'
app.config['SECRET_KEY'] = 'Baohung0303'

# Intialize MySQL
mysql = MySQL(app)

# Khởi tạo Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Đường dẫn đến trang đăng nhập

# Khởi tạo Flask-Principal
principal = Principal(app)

# Định nghĩa model User (implements UserMixin) và hàm load_user
class User(UserMixin):
    def __init__(self, id, username, password, is_admin=False, is_manager=False):
        self.id = id
        self.username = username
        self.password = password
        self.is_admin = is_admin
        self.is_manager = is_manager

# Giả định có danh sách người dùng
users = [
    User(1, 'admin', 'admin', is_admin=True),
    User(2, 'manager', 'manager', is_manager=True),
    User(3, 'user', 'user')
]

@login_manager.user_loader
def load_user(user_id):
    # Hàm load_user để tải đối tượng User tương ứng với user_id
    for user in users:
        if user.id == int(user_id):
            return user
    return None

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Xác định vai trò của người dùng trong identity
    if current_user.is_authenticated:
        if current_user.is_admin:
            identity.provides.add(RoleNeed('Admin'))
        if current_user.is_manager:
            identity.provides.add(RoleNeed('Quản lý'))
        if not current_user.is_admin and not current_user.is_manager:
            identity.provides.add(RoleNeed('Người dùng'))

# Định nghĩa các tuyến đường và phân quyền
@app.route('/login/', methods=["GET", "POST"])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        # Hash the password input by the user
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Auth_user WHERE username = %s ', (username,))
        # Fetch one record and return result
        account = cursor.fetchone()
        # If account exists in accounts table in our database
        if account:
            # Check if the account is locked
            if account['Is_active'] == 0 and (datetime.now() - account['Last_login_time']) < timedelta(minutes=1):
                msg = 'Your account has been locked!'
                return redirect(url_for('login'))
            else:
                # Get the stored hashed password from the account data
                stored_password = account['Password_reset_token']
                # Get the failed login attempts count from the account data
                Failed_login_attempts = account['Failed_login_attempts']
                # Compare the hashed password input by the user with the stored hashed password
                if hashed_password == stored_password:
                    # Reset failed login attempts and update last login time
                    cursor.execute(
                        'UPDATE Auth_user SET Failed_login_attempts = 0, Last_login_time = %s, is_active = 1 WHERE id = %s',
                        (datetime.now(), account['id'],))
                    mysql.connection.commit()
                    # Create session data, we can access this data in other routes
                    session['loggedin'] = True
                    session['id'] = account['id']
                    session['username'] = account['username']
                    # Redirect to home page
                    return redirect(url_for('home'))
                else:
                    # Increment failed login attempts
                    Failed_login_attempts += 1
                    cursor.execute('UPDATE Auth_user SET Failed_login_attempts = Auth_user.Failed_login_attempts + 1 WHERE id = %s',
                                   (account['id'],))
                    mysql.connection.commit()
                    # Check if the account should be locked
                    if account['Failed_login_attemps'] >= 4:
                        # Lock the account
                        cursor.execute('UPDATE Auth_user SET Is_active = 0 WHERE id = %s', (account['id'],))
                        mysql.connection.commit()
                        msg = 'Your account has been locked!'
                        return redirect(url_for('login'))
                    else:
                        msg = f'Incorrect username/password! Failed login attempts: {Failed_login_attempts}'
                        return redirect(url_for('login'))
        else:
            msg = 'Invalid username or password!'
            return redirect(url_for('login'))

    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

@app.route('/login/home')
def home():
# Check if user is logged-in
    if 'loggedin' in session:
        return render_template('home.html')
    return redirect(url_for('login'))

@app.route('/login/profile')
@login_required
def profile():
    # Check if user is logged-in
    if 'loggedin' in session:
        # We need all the account info for the user, so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Employee WHERE Employee.id = %s', (session['id'],))
        employee = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', Employee=employee)
    # User is not logged-in redirect to login page
    return redirect(url_for('login'))

# Get the maximum employee_id in the database
def get_max_employee_id(cursor):
    cursor.execute('SELECT MAX(employee_id) FROM Auth_user')
    result = cursor.fetchone()
    max_employee_id = result['MAX(employee_id)'] if result['MAX(employee_id)'] else 0
    return max_employee_id
@app.route('/login/register', methods=["GET", "POST"])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password", "confirm-password" POST requests exist (user submitted form)
    if request.method == 'POST':
        # Create variables for easy access
        username = request.form['username']
        # Hash password using SHA256
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        is_active = 1
        # Get the maximum employee_id in the database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        max_employee_id = get_max_employee_id(cursor)
        # Generate a new employee_id
        employee_id = max_employee_id + 1
        failed_login_attempts = 0
        last_login_time = datetime.now()
        password_reset_token = hashlib.sha256(request.form['password'].encode()).hexdigest()
        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Auth_user WHERE username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password:
            msg = 'Please fill out the form!'
        elif password != confirm_password:
            msg = 'Passwords do not match!'
        elif len(password) < 8:
            msg = 'Password must be at least 8 characters long!'
        elif not any(char.isdigit() for char in password):
            msg = 'Password must contain at least one number!'
        elif not any(char.isupper() for char in password):
            msg = 'Password must contain at least one uppercase letter!'
        elif not any(char.islower() for char in password):
            msg = 'Password must contain at least one lowercase letter!'
        else:
            # Account doesn't exist and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO Auth_user VALUES (NULL, %s, %s, %s, %s, %s, %s, %s)',
                (username, password, employee_id, is_active, failed_login_attempts, last_login_time, password_reset_token,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == "POST":
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/login/users')
@login_required
def load_users():
    # Check if user is logged-in
    if 'loggedin' in session:
        return render_template('user.html')
    return redirect(url_for('login'))

# Các hàm hỗ trợ
def get_managed_employees(manager_id):
    # Hàm này để lấy danh sách nhân viên do manager quản lý
    # Thực hiện truy vấn vào cơ sở dữ liệu hoặc xử lý logic tương ứng
    # và trả về danh sách nhân viên
    pass

@app.route('/login/calendar')
@login_required
def calendar():
    # Check if user is logged-in
    if 'loggedin' in session:
        return render_template('calendar.html')
    return redirect(url_for('login'))

@app.route('/login/chart')
@login_required
def chart():
    # Check if user is logged-in
    if 'loggedin' in session:
        return render_template('charts-apexcharts.html')
    return redirect(url_for('login'))


@app.route('/login/profile/upload-image', methods=['POST'])
def upload_image():
    file = request.files['file']
    if file:
        filename = file.filename
        file.save(os.path.join('static/img', filename))
        new_image_url = f"/static/img/{filename}"
        return jsonify({'success': True, 'file_url': new_image_url})
    else:
        return jsonify({'success': False, 'message': 'No file selected.'})

if __name__ == "__main__":
    app.run(debug=True)