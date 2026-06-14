import sqlite3
from tabulate import tabulate

conn = sqlite3.connect("attendance.db")
c = conn.cursor()
c.execute("SELECT user_id, name, timestamp, date FROM attendance ORDER BY timestamp DESC")
rows = c.fetchall()
conn.close()

print(tabulate(rows, headers=["User ID", "Name", "Timestamp", "Date"], tablefmt="grid"))
