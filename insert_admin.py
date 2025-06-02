from werkzeug.security import generate_password_hash
import mysql.connector

# Hash the password
hashed_password = generate_password_hash('rUsHi@2416')

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",  # change if needed
    password="Rushi@2001",  # put your actual MySQL root password or leave blank if it's empty
    database="flightdb"
)

cursor = db.cursor()

# Insert admin user
cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", ('RRushi', hashed_password))
db.commit()

print("✅ Admin user inserted successfully.")

from werkzeug.security import generate_password_hash
import mysql.connector

# Hash the password
hashed_password = generate_password_hash('rUsHi@2416')

# Connect to MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",  # change if needed
    password="Rushi@2001",  # put your actual MySQL root password or leave blank if it's empty
    database="flightdb"
)

cursor = db.cursor()

# Insert admin user
cursor.execute("INSERT INTO admin (username, password) VALUES (%s, %s)", ('RRushi', hashed_password))
db.commit()

print("✅ Admin user inserted successfully.")

