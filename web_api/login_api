from flask import Flask, request, jsonify, session
import pymysql
import hashlib
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

db = pymysql.connect(host='khoaluandb.cx4dxwmzciis.ap-southeast-1.rds.amazonaws.com', user='admin', password='1709hung2000', database='khoaluan')
cur = db.cursor(pymysql.cursors.DictCursor)

@app.route('/api/login', methods=["GET"])
def login():
    # Output message if something goes wrong...
    msg = ''
    # Check if "account" and "password" query parameters exist
    if 'account' in request.args and 'password' in request.args:
        # Create variables for easy access
        username = request.args.get('account')
        password = request.args.get('password')
        # Hash the password input by the user
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        # Check if account exists using MySQL
        cur.execute('SELECT * FROM Auth_user WHERE username = %s ', (username,))
        # Fetch one record and return result
        account = cur.fetchone()
        # If account exists in accounts table in our database
        if account:
            # Check if the account is locked
            if account['Is_active'] == 0 and (datetime.now() - account['Last_login_time']) < timedelta(minutes=1):
                msg = 'Your account has been locked!'
                return jsonify({"msg": msg}), 403
            else:
                # Get the stored hashed password from the account data
                stored_password = account['password']
                # Get the failed login attempts count from the account data
                Failed_login_attempts = account['Failed_login_attempts']
                # Compare the hashed password input by the user with the stored hashed password
                if password == stored_password:
                    # Reset failed login attempts and update last login time
                    cur.execute(
                        'UPDATE Auth_user SET Failed_login_attempts = 0, Last_login_time = %s, Is_active = 1 WHERE id = %s',
                        (datetime.now(), account['id'],))
                    db.commit()
                    # Create session data, we can access this data in other routes
                    session['loggedin'] = True
                    session['id'] = account['id']
                    session['username'] = account['username']

                    # Redirect to home page
                    return jsonify({"msg": "Logged in successfully", "username": account['username'], "id": account['id']}), 200
                else:
                    # Increment failed login attempts
                    Failed_login_attempts += 1
                    cur.execute('UPDATE Auth_user SET Failed_login_attempts = Failed_login_attempts + 1 WHERE id = %s',
                                   (account['id'],))
                    db.commit()
                    # Check if the account should be locked
                    if account['Failed_login_attempts'] >= 4:
                        # Lock the account
                        cur.execute('UPDATE Auth_user SET Is_active = 0 WHERE id = %s', (account['id'],))
                        db.commit()
                        msg = 'Your account has been locked!'
                        return jsonify({"msg": msg}), 403
                    else:
                        msg = f'Incorrect username/password! Failed login attempts: {Failed_login_attempts} and password is : {account["password"]} hash pass : {hashed_password} store pass:{stored_password}'
                        return jsonify({"msg": msg}), 401
        else:
            msg = 'Invalid username or password!'
            return jsonify({"msg": msg}), 401

    # Show the login form with message (if any)
        return jsonify({"msg": "Provide username and password"})

if __name__ == '__main__':
    app.run(debug=True)