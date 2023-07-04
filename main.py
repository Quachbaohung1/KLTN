from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from core import core
import numpy as np
import cv2

service=core.create_service()


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
                return render_template('index.html', msg='Your account has been locked in 1 minute!')
            else:
                # Get the stored hashed password from the account data
                stored_password = account['Password_reset_token']
                # Get the failed login attempts count from the account data
                failed_login_attempts = account['Failed_login_attempts']
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
                    failed_login_attempts += 1
                    cursor.execute(
                        'UPDATE Auth_user SET Failed_login_attempts = Auth_user.Failed_login_attempts + 1 WHERE id = %s',
                        (account['id'],))
                    mysql.connection.commit()
                    # Check if the account should be locked
                    if failed_login_attempts >= 4:
                        # Lock the account
                        cursor.execute('UPDATE Auth_user SET Is_active = 0 WHERE id = %s', (account['id'],))
                        mysql.connection.commit()
                        return render_template('index.html', msg='Your account has been locked!')
                    else:
                        return render_template('index.html', msg='Incorrect username/password!')
        else:
            return render_template('index.html', msg='Incorrect username or password!')
    return render_template('index.html', msg='')


@app.route('/login/home')
def home():
    username = session.get('username')  # Lấy tên người dùng từ session
    user_id = session.get('id')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Auth_user WHERE id = %s AND username = %s', (user_id, username,))
    auth_user = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

    cursor.execute('SELECT * FROM Employee WHERE id = %s', (user_id,))
    employee = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

    cursor.close()

    if auth_user:
        role_id = session.get('RoleID')
        if role_id == 3:
            # Người dùng đã đăng nhập và có vai trò admin
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của admin
            return render_template('admin_home.html', Auth_user=auth_user, Employee=employee)
        elif role_id == 1:
            # Người dùng đã đăng nhập và có vai trò user
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của user
            return render_template('user_home.html', Auth_user=auth_user, Employee=employee)
        elif role_id == 2:
            # Người dùng đã đăng nhập và có vai trò manager
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của manager
            return render_template('manager_home.html', Auth_user=auth_user, Employee=employee)

    # Người dùng không có quyền truy cập vào màn hình này hoặc chưa đăng nhập
    abort(403)

@app.route('/login/profile', methods=['GET', 'POST'])
def profile():
    # Check if user is logged-in
    if 'loggedin' in session:
        # We need all the account info for the user, so we can display it on the profile page
        username = session.get('username')  # Lấy tên người dùng từ session
        user_id = session.get('id')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Auth_user WHERE id = %s AND username = %s', (user_id, username,))
        auth_user = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

        if request.method == 'POST':
            # Retrieve the form data
            full_name = request.form.get('fullName')
            age = request.form.get('age')
            department_id = request.form.get('Dept')
            address = request.form.get('address')
            phone = request.form.get('phone')
            email = request.form.get('email')

            # Split the full name into first name and last name
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            else:
                first_name = full_name
                last_name = ''

            # Update the user's profile in the database
            cursor.execute('UPDATE Employee SET FirstName = %s, LastName = %s, Age = %s, Department_ID = %s, Address = %s, Phone_no = %s, Email_Address = %s WHERE id = %s',
                           (first_name, last_name, age, department_id, address, phone, email, user_id))
            mysql.connection.commit()

        cursor.execute('SELECT * FROM Employee WHERE id = %s', (user_id,))
        employee = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

        cursor.execute('SELECT * FROM Department')
        departments = cursor.fetchall()

        cursor.close()

        if employee:
            role_id = session.get('RoleID')
            if role_id == 3:
                # Người dùng đã đăng nhập và có vai trò admin
                # Thực hiện các tác vụ tương ứng với màn hình dashboard của admin
                return render_template('profile.html', Auth_user=auth_user, Employee=employee, departments=departments)
            elif role_id == 1:
                # Người dùng đã đăng nhập và có vai trò user
                # Thực hiện các tác vụ tương ứng với màn hình dashboard của user
                return render_template('profile_user.html', Auth_user=auth_user, Employee=employee, departments=departments)
            elif role_id == 2:
                # Người dùng đã đăng nhập và có vai trò manager
                # Thực hiện các tác vụ tương ứng với màn hình dashboard của manager
                return render_template('profile_manager.html', Auth_user=auth_user, Employee=employee, departments=departments)

        # Employee not found in the database
        abort(403)

    # User is not logged-in redirect to login page
    return redirect(url_for('login'))

@app.route('/login/profile/change_password', methods=['GET', 'POST'])
def change_password():
    # Check if user is logged-in
    if 'loggedin' in session:
        user_id = session.get('id')

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Auth_user WHERE id = %s', (user_id,))
        user = cursor.fetchone()

        if user:
            if request.method == 'POST':
                current_password = request.form.get('currentPassword')
                new_password = request.form.get('newPassword')
                confirm_password = request.form.get('confirmPassword')

                if current_password == user['password']:
                    if new_password == confirm_password:
                        # Hash the new password
                        hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
                        # Update the user's password and Password_reset_token in the database
                        cursor.execute('UPDATE Auth_user SET password = %s, Password_reset_token = %s WHERE id = %s',
                                       (new_password, hashed_password, user_id))
                        mysql.connection.commit()

                        flash('Password changed successfully!', 'success')
                    else:
                        flash('New password and confirm password do not match.', 'error')
                else:
                    flash('Incorrect current password.', 'error')
            cursor.execute('SELECT * FROM Employee WHERE id = %s', (user_id,))
            employee = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn
            cursor.close()
            return redirect(url_for('profile'))

    # User is not logged-in, redirect to login page
    return redirect(url_for('login'))



# Get the maximum employee_id in the database
def get_max_employee_id(cursor):
    cursor.execute('SELECT MAX(employee_id) FROM Auth_user')
    result = cursor.fetchone()
    max_employee_id = result['MAX(employee_id)'] if result['MAX(employee_id)'] is not None else 0
    return max_employee_id

def get_max_id(cursor):
    cursor.execute('SELECT MAX(id) FROM Auth_user')
    result = cursor.fetchone()
    max_id = result['MAX(id)'] if result['MAX(id)'] is not None else 0
    return max_id

@app.route('/login/register', methods=["GET", "POST"])
def register():
    # Output message if something goes wrong...
    msg = ''

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Role')
    roles = cursor.fetchall()
    cursor.execute('SELECT * FROM Department')
    departments = cursor.fetchall()

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        RoleID = request.form['role']
        Department_ID = request.form['Dept']
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']

        # Get the maximum employee_id in the database
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        max_employee_id = get_max_employee_id(cursor)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        max_id = get_max_id(cursor)

        # Generate a new employee_id
        id = max_id + 1
        is_active = 1
        employee_id = max_employee_id + 1
        failed_login_attempts = 0
        last_login_time = 0
        password_reset_token = hashlib.sha256(request.form['password'].encode()).hexdigest() # Hash password using SHA256
        created_at = datetime.now()
        updated_at = datetime.now()

        # Check if account exists using MySQL
        cursor.execute('SELECT * FROM Auth_user WHERE username = %s', (username,))
        account = cursor.fetchone()

        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
            return render_template('register.html', roles=roles, departments=departments, msg=msg)
        else:
            # Insert data into employee table
            cursor.execute('INSERT INTO Employee VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                           (employee_id, first_name, last_name, RoleID, Department_ID, None, None, None, email, created_at, updated_at))
            # Account doesn't exist and the form data is valid, now insert new account into accounts table
            cursor.execute('INSERT INTO Auth_user VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
                           (id, username, password, employee_id, is_active, failed_login_attempts, last_login_time, password_reset_token, created_at, updated_at, RoleID))
            mysql.connection.commit()
            msg = 'You have successfully registered!'
            return render_template('register.html', roles=roles, departments=departments, msg=msg)
    elif request.method == 'GET':
        # Form is empty... (no POST data)
        pass
    # Show registration form with message (if any)
    return render_template('register.html', roles=roles, departments=departments, msg=msg)

# Upload employee image to employee image database
@app.route('/api/uploadimg', methods=['POST'])
def uploadimg():
    file = request.files['image']
    eid=str(request.form['eid'])
    # Read the image via file.stream
    image = np.asarray(bytearray(file.read()), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    height, width, channels = image.shape
    out=core.upload_image(eid,image,service)
    return jsonify({'msg': 'success', 'size': [width, height],'eid':eid,'drive_id':out})

@app.route('/login/users')
def load_users():
    username = session.get('username')  # Lấy tên người dùng từ session
    user_id = session.get('id')

    # Check if user is logged-in
    if 'loggedin' in session:
        role_id = session.get('RoleID')
        if role_id == 3:
            # Người dùng đã đăng nhập và có vai trò admin
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của admin
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM Auth_user WHERE id = %s AND username = %s', (user_id, username,))
            auth_user = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

            cursor.execute('SELECT * FROM Employee WHERE id = %s', (user_id,))
            employee = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

            cursor.execute("SELECT Employee.* FROM Employee")
            employee1 = cursor.fetchall()

            cursor.execute('SELECT * FROM Department')
            departments = cursor.fetchall()

            cursor.execute('SELECT * FROM Auth_user')
            auth_user1 = cursor.fetchall()  # Lấy dòng đầu tiên từ kết quả truy vấn

            cursor.close()
            return render_template('user.html', Auth_user=auth_user, Employee=employee, departments=departments, Employee1=employee1, auth_user1=auth_user1)
    return redirect(url_for('login'))

@app.route('/login/users_manager')
def load_users_manager():
    username = session.get('username')  # Lấy tên người dùng từ session
    user_id = session.get('id')

    # Check if user is logged-in
    if 'loggedin' in session:
        role_id = session.get('RoleID')
        if role_id == 2:
            # Người dùng đã đăng nhập và có vai trò manager
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM Auth_user WHERE id = %s AND username = %s', (user_id, username,))
            auth_user2 = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

            cursor.execute('SELECT * FROM Employee WHERE id = %s', (user_id,))
            employee2 = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

            department_id = employee2['Department_ID']

            cursor.execute('SELECT Employee.* FROM Employee where Department_ID = %s', (department_id,))
            employee3 = cursor.fetchall()

            cursor.execute('SELECT * FROM Department')
            departments1 = cursor.fetchall()

            cursor.execute('SELECT * FROM Auth_user')
            auth_user3 = cursor.fetchall()  # Lấy dòng đầu tiên từ kết quả truy vấn

            cursor.close()
            return render_template('user_manager.html', Auth_user2=auth_user2, Employee2=employee2, departments1=departments1, Employee3=employee3, auth_user3=auth_user3)
    return redirect(url_for('login'))

# Các hàm hỗ trợ
def get_managed_employees(manager_id):
    # Hàm này để lấy danh sách nhân viên do manager quản lý
    # Thực hiện truy vấn vào cơ sở dữ liệu hoặc xử lý logic tương ứng
    # và trả về danh sách nhân viên
    pass


def max_length(list1, list2):
    return max(len(list1), len(list2))
@app.route('/login/time')
def calendar():
    username = session.get('username')  # Lấy tên người dùng từ session
    user_id = session.get('id')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Auth_user WHERE id = %s AND username = %s', (user_id, username,))
    auth_user = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

    cursor.execute('SELECT * FROM Employee WHERE id = %s', (user_id,))
    employee = cursor.fetchone()  # Lấy dòng đầu tiên từ kết quả truy vấn

    cursor.execute('SELECT * FROM Employee')
    employee1 = cursor.fetchall()

    cursor.execute('SELECT * FROM Department')
    departments = cursor.fetchall()

    cursor.execute('SELECT * FROM Event')
    events = cursor.fetchall()

    cursor.close()

    employee_check_ins = {}
    employee_check_outs = {}

    for employee in employee1:
        employee_id = employee['id']
        employee_check_ins[employee_id] = []
        employee_check_outs[employee_id] = []

    for event in events:
        employee_id = event['Employee_ID']
        event_type_id = event['Event_Type_ID']
        if event_type_id == 1:
            employee_check_ins[employee_id].append(event)
        elif event_type_id == 2:
            employee_check_outs[employee_id].append(event)
        elif event_type_id == 3:
            employee_check_outs[employee_id].append(event)

    late_count = 0
    for employee_id, check_ins in employee_check_ins.items():
        for check_in in check_ins:
            if check_in['Event_Time'].hour > 8:
                late_count += 1
    ontime_count = 0
    for employee_id, check_ins in employee_check_ins.items():
        for check_in in check_ins:
            if check_in['Event_Time'].hour <= 8:
                ontime_count += 1
    na_count = 0
    for employee_id, check_ins in employee_check_ins.items():
        check_outs = employee_check_outs.get(employee_id, [])
        max_length = max(len(check_ins), len(check_outs))
        for i in range(max_length):
            if i >= len(check_ins) or i >= len(check_outs):
                na_count += 1
    total_contact = 0
    for employee_id, check_ins in employee_check_ins.items():
        total_contact += len(check_ins)

    # Check if user is logged-in
    if 'loggedin' in session:
        role_id = session.get('RoleID')
        if role_id == 3:
            # Người dùng đã đăng nhập và có vai trò admin
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của admin
            return render_template('Time.html', Auth_user=auth_user, Employee=employee, Employee1=employee1, departments=departments, events=events, employee_check_ins=employee_check_ins, employee_check_outs=employee_check_outs, late_count=late_count, na_count=na_count, ontime_count=ontime_count, total_contact=total_contact)
        elif role_id == 1:
            # Người dùng đã đăng nhập và có vai trò user
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của user
            return render_template('Time_user.html', Auth_user=auth_user, Employee=employee, Employee1=employee1, departments=departments, events=events, employee_check_ins=employee_check_ins, employee_check_outs=employee_check_outs, late_count=late_count, na_count=na_count, ontime_count=ontime_count, total_contact=total_contact)
        elif role_id == 2:
            # Người dùng đã đăng nhập và có vai trò manager
            # Thực hiện các tác vụ tương ứng với màn hình dashboard của manager
            return render_template('Time_manager.html', Auth_user=auth_user, Employee=employee, Employee1=employee1, departments=departments, events=events, employee_check_ins=employee_check_ins, employee_check_outs=employee_check_outs, late_count=late_count, na_count=na_count, ontime_count=ontime_count, total_contact=total_contact)

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
        file.save(os.path.join('static/img', 'holder.jpeg'))
        new_image_url = f"/static/img/holder.jpeg"
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

@app.route('/update-status', methods=['POST'])
def update_status():
    data = request.get_json()
    employee_id = data.get('employeeId')
    current_status = data.get('currentStatus')

    # Thực hiện cập nhật trạng thái trong cơ sở dữ liệu tại đây
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Auth_user SET Is_active = %s WHERE Employee_id = %s", (current_status, employee_id))
    mysql.connection.commit()

    # Trả về phản hồi thành công
    return jsonify({'message': 'Status updated successfully'})


if __name__ == "__main__":
    app.run(debug=True)