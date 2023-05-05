import paramiko
import mysql.connector
from sshtunnel import SSHTunnelForwarder

ssh_host = '18.140.65.95'
ssh_port = 22
ssh_username = 'ec2-user'
private_key_file = 'D:\download\web_khoa_luan\KLTN\web_api\khoaluankey1.pem'

mysql_host = '172.31.22.123'
mysql_port = 3306

# Load the private key
private_key = paramiko.RSAKey.from_private_key_file(private_key_file)

# Set up the SSH tunnel
tunnel = SSHTunnelForwarder(
    (ssh_host, ssh_port),
    ssh_username=ssh_username,
    ssh_pkey=private_key,
    remote_bind_address=(mysql_host, mysql_port),
    local_bind_address=('127.0.0.1', 0)  # Automatically choose an available local port
)

# Start the SSH tunnel
tunnel.start()

# Get the local port number
local_port = tunnel.local_bind_port

print(local_port)

mysql_user = 'Hungqb'
mysql_password = '123456'
mysql_database = 'khoaluan'

try:
    conn = mysql.connector.connect(
        host='127.0.0.1',
        port=local_port,
        user=mysql_user,
        password=mysql_password,
        database=mysql_database,
        connection_timeout=10  # 10 seconds timeout
    )
except mysql.connector.errors.InterfaceError as e:
    print(f"Error: {e}")

if tunnel.is_active:
    print("SSH tunnel is active")
else:
    print("SSH tunnel is not active")