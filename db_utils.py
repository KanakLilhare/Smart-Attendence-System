import sqlite3

def init_db():
    conn = sqlite3.connect("attendance.db")
    c = conn.cursor()

    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    # Attendance table
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            lecture TEXT,
            date TEXT,
            timestamp TEXT
        )
    ''')

    conn.commit()
    conn.close()
