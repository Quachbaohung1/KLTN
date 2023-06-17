from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, send_from_directory
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'khoaluandb.cx4dxwmzciis.ap-southeast-1.rds.amazonaws.com'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = '1709hung2000'
app.config['MYSQL_DB'] = 'khoaluan'
app.config['SECRET_KEY'] = 'Baohung0303'

app.config['UPLOAD_FOLDER'] = 'static/img'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'xlsx', 'xls'}

# Intialize MySQL
mysql = MySQL(app)

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
                    session['RoleID'] = account['RoleID']  # Lưu trữ vai trò của người dùng
                    # Redirect to home page
                    return redirect(url_for('home'))
                else:
                    # Increment failed login attempts
                    Failed_login_attempts += 1
                    cursor.execute('UPDATE Auth_user SET Failed_login_attempts = Auth_user.Failed_login_attempts + 1 WHERE id = %s',
                                   (account['id'],))
                    mysql.connection.commit()
                    # Check if the account should be locked
                    if account['Failed_login_attempts'] >= 4:
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
    if 'loggedin' in session and session['RoleID'] == 3:
        # Người dùng đã đăng nhập và có vai trò admin
        # Thực hiện các tác vụ tương ứng với màn hình dashboard của admin
        return render_template('admin_home.html')
    elif 'loggedin' in session and session['RoleID'] == 1:
        # Người dùng đã đăng nhập và có vai trò user
        # Thực hiện các tác vụ tương ứng với màn hình dashboard của user
        return render_template('user_home.html')
    elif 'loggedin' in session and session['RoleID'] == 2:
        # Người dùng đã đăng nhập và có vai trò user
        # Thực hiện các tác vụ tương ứng với màn hình dashboard của user
        return render_template('manage_home.html')
    else:
        # Người dùng không có quyền truy cập vào màn hình này
        abort(403)


@app.route('/login/profile')
def profile():
    # Check if user is logged-in
    if 'loggedin' in session:
        # We need all the account info for the user, so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Employee WHERE Employee.id = %s', (session['id'],))
        employee = cursor.fetchone()
        if employee:
            # Show the profile page with account info
            return render_template('profile.html', Employee=employee)
        else:
            # Employee not found in the database
            abort(403)
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
        RoleID = request.form['RoleID']
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
        else:
            # Account doesn't exist and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO Auth_user VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s)',
                (username, password, employee_id, is_active, failed_login_attempts, last_login_time, password_reset_token, RoleID,))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
    elif request.method == "POST":
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg=msg)

@app.route('/login/users')
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

@app.route('/login/time')
def calendar():
    # Check if user is logged-in
    if 'loggedin' in session:
        return render_template('Time.html')
    return redirect(url_for('login'))

@app.route('/login/chart')
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


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/login/users/upload_contacts', methods=['POST'])
def upload_contacts():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif filename.endswith('.xlsx') or filename.endswith('.xls'):
            df = pd.read_excel(file_path)
        return jsonify({'success': True, 'message': 'File uploaded and processed successfully.'})
    else:
        return jsonify({'success': False, 'message': 'Invalid file or file format.'})




if __name__ == "__main__":
    app.run(debug=True)