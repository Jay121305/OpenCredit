"""Test script to check user role in database."""
import sqlite3

conn = sqlite3.connect('opencredit.db')
cursor = conn.cursor()

cursor.execute('SELECT id, email, role FROM users')
users = cursor.fetchall()

print("All users in database:")
for user in users:
    print(f"  ID={user[0]}, Email={user[1]}, Role={user[2]}")

if not users:
    print("  No users found!")

conn.close()
