from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import hashlib
from datetime import datetime, timedelta

app = Flask(__name__)

# Change this to your secret key (can be anything, it's for extra protection)
app.secret_key = 'Baohung0303'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'khoaluandb.cx4dxwmzciis.ap-southeast-1.rds.amazonaws.com'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'admin'
app.config['MYSQL_PASSWORD'] = '1709hung2000'
app.config['MYSQL_DB'] = 'khoaluan'

# Intialize MySQL
mysql = MySQL(app)


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
def load_users():
    # Check if user is logged-in
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('select Employee.id as id, Employee.FirstName as firstname, Employee.LastName as lastname, info.jobname as job, info.departmentname as department, Employee.Age as age, Employee.Phone_no as phone_no, Employee.Email_Address as email, Employee.Address as address from Employee left join ( select Job.id as id, Job.Name as jobname, Department.Name as departmentname from Job left join Department on Job.department_id=Department.id ) as info on Employee.Job_ID=info.id')
        employee = cursor.fetchall()
        return render_template('user.html', employee=employee)
    return redirect(url_for('login'))

@app.route('/login/calendar')
def calendar():
    # Check if user is logged-in
    if 'loggedin' in session:
        return render_template('calendar.html')
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)