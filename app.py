from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
import sqlite3
from recognize_web import recognize_faces
from db_utils import init_db
import subprocess
import sys
import csv
import io
from datetime import datetime, timedelta
import os

# ----------------------------
# Flask Configuration
# ----------------------------
app = Flask(__name__)
app.secret_key = "smart_attendance_secret"
init_db()  # Ensure DB tables exist


# ----------------------------
# Helper Function
# ----------------------------
def get_db_connection():
    conn = sqlite3.connect('attendance.db')
    conn.row_factory = sqlite3.Row
    return conn


# ----------------------------
# ROUTES (existing ones unchanged)
# ----------------------------

@app.route('/')
def home():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = get_db_connection()
        teacher = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (uname, pwd)).fetchone()
        conn.close()

        if teacher:
            session['teacher'] = uname
            flash("✅ Login successful!", "success")
            return redirect('/dashboard')
        else:
            flash("❌ Invalid username or password!", "error")

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uname = request.form['username']
        pwd = request.form['password']

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (uname, pwd))
            conn.commit()
            flash("✅ Registration successful! You can now log in.", "success")
            return redirect('/login')
        except:
            flash("⚠️ Username already exists!", "error")
        conn.close()

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'teacher' not in session:
        return redirect('/login')
    return render_template('dashboard.html', teacher_name=session['teacher'])


@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'teacher' not in session:
        return redirect('/login')

    if request.method == 'POST':
        student_id = request.form['student_id']
        student_name = request.form['student_name']

        try:
            subprocess.run(
                [sys.executable, "capture_images.py", student_id, student_name],
                check=True
            )
            flash(f"✅ Images captured successfully for {student_name}", "success")
        except Exception as e:
            flash(f"⚠️ Error capturing images: {e}", "error")

        return redirect('/add_student')

    return render_template('add_student.html')


@app.route('/start_attendance', methods=['POST'])
def start_attendance():
    if 'teacher' not in session:
        return redirect('/login')

    lecture_name = request.form['lecture_name']
    recognize_faces(lecture_name)
    flash(f"✅ Attendance completed for {lecture_name}!", "success")
    return redirect('/view_records')


# upload_attendance route from earlier conversations
@app.route('/upload_attendance', methods=['GET', 'POST'])
def upload_attendance():
    if 'teacher' not in session:
        return redirect('/login')

    if request.method == 'POST':
        lecture_name = request.form['lecture_name']
        image = request.files['photo']

        if image:
            upload_dir = os.path.join(app.root_path, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            upload_path = os.path.join(upload_dir, image.filename)
            image.save(upload_path)

            try:
                from recognize_web import recognize_faces_from_image
                recognize_faces_from_image(upload_path, lecture_name)
                flash(f"✅ Attendance marked from uploaded photo for {lecture_name}!", "success")
            except Exception as e:
                flash(f"⚠️ Error processing image: {e}", "error")

            return redirect('/view_records')

    return render_template('upload_attendance.html')


# ---------- VIEW ATTENDANCE WITH FILTERS ----------
@app.route('/view_records', methods=['GET', 'POST'])
def view_records():
    if 'teacher' not in session:
        return redirect('/login')

    conn = get_db_connection()
    lecture_filter = request.form.get('lecture')
    date_filter = request.form.get('date')

    query = 'SELECT user_id, name, lecture, date, timestamp FROM attendance WHERE 1=1'
    params = []

    if lecture_filter:
        query += ' AND lecture = ?'
        params.append(lecture_filter)
    if date_filter:
        query += ' AND date = ?'
        params.append(date_filter)

    query += ' ORDER BY date DESC, timestamp DESC'
    records = conn.execute(query, params).fetchall()
    lectures = [row['lecture'] for row in conn.execute('SELECT DISTINCT lecture FROM attendance WHERE lecture IS NOT NULL').fetchall()]
    conn.close()

    total_records = len(records)

    return render_template('view_records.html',
                           records=records,
                           lectures=lectures,
                           total_records=total_records,
                           lecture_filter=lecture_filter,
                           date_filter=date_filter)


# ---------- DOWNLOAD ATTENDANCE CSV (WITH FILTERS) ----------
@app.route('/download_csv', methods=['GET'])
def download_csv():
    if 'teacher' not in session:
        return redirect('/login')

    lecture_filter = request.args.get('lecture')
    date_filter = request.args.get('date')

    conn = get_db_connection()
    query = 'SELECT * FROM attendance WHERE 1=1'
    params = []

    if lecture_filter:
        query += ' AND lecture = ?'
        params.append(lecture_filter)
    if date_filter:
        query += ' AND date = ?'
        params.append(date_filter)

    query += ' ORDER BY date DESC, timestamp DESC'
    records = conn.execute(query, params).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "User ID", "Name", "Lecture", "Date", "Timestamp"])

    for row in records:
        writer.writerow([row["id"], row["user_id"], row["name"], row["lecture"], row["date"], row["timestamp"]])

    output.seek(0)
    filename = f"attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


# ---------- ANALYTICS ROUTES ----------
@app.route('/analytics')
def analytics():
    # page that loads the dashboard and charts
    if 'teacher' not in session:
        return redirect('/login')
    return render_template('analytics.html', project_title="Smart Attendance System")


# JSON endpoints for charts

@app.route('/api/analytics/summary')
def analytics_summary():
    if 'teacher' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    total_students = conn.execute('SELECT COUNT(DISTINCT user_id) as cnt FROM attendance').fetchone()['cnt']
    total_lectures = conn.execute('SELECT COUNT(DISTINCT lecture) as cnt FROM attendance').fetchone()['cnt']
    total_records = conn.execute('SELECT COUNT(*) as cnt FROM attendance').fetchone()['cnt']
    # average attendance per lecture (approx)
    avg_attendance = 0
    if total_lectures and total_lectures > 0:
        avg_attendance = round(total_records / total_lectures, 2)
    conn.close()

    return jsonify({
        'total_students': total_students,
        'total_lectures': total_lectures,
        'total_records': total_records,
        'avg_attendance': avg_attendance
    })


@app.route('/api/analytics/monthly')
def analytics_monthly():
    if 'teacher' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    # last 12 months counts
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT strftime('%Y-%m', date) AS month, COUNT(*) as cnt
        FROM attendance
        WHERE date >= date('now','-11 months')
        GROUP BY month
        ORDER BY month
    """).fetchall()
    conn.close()

    # build continuous 12-month list (even if some months missing)
    months = []
    counts = []
    today = datetime.now()
    for i in reversed(range(0, 12)):
        m = (today - timedelta(days=30*i)).strftime('%Y-%m')
        months.append(m)
    # map rows
    row_map = {r['month']: r['cnt'] for r in rows}
    for m in months:
        counts.append(row_map.get(m, 0))

    return jsonify({'months': months, 'counts': counts})


@app.route('/api/analytics/student')
def analytics_student():
    if 'teacher' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT name, COUNT(*) as cnt
        FROM attendance
        GROUP BY name
        ORDER BY cnt DESC
        LIMIT 100
    """).fetchall()
    conn.close()

    labels = [r['name'] for r in rows]
    data = [r['cnt'] for r in rows]
    return jsonify({'labels': labels, 'data': data})


@app.route('/api/analytics/lecture')
def analytics_lecture():
    if 'teacher' not in session:
        return jsonify({'error': 'unauthorized'}), 401

    conn = get_db_connection()
    rows = conn.execute("""
        SELECT lecture, COUNT(*) as cnt
        FROM attendance
        GROUP BY lecture
        ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    labels = [r['lecture'] if r['lecture'] else 'Unknown' for r in rows]
    data = [r['cnt'] for r in rows]
    return jsonify({'labels': labels, 'data': data})


@app.route('/api/analytics/daily')
def analytics_daily():
    if 'teacher' not in session():
        return jsonify({'error': 'unauthorized'}), 401

    # daily counts for last 30 days
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT date, COUNT(*) as cnt
        FROM attendance
        WHERE date >= date('now','-29 days')
        GROUP BY date
        ORDER BY date
    """).fetchall()
    conn.close()

    dates = []
    counts = []
    # build last 30 day labels
    today = datetime.now().date()
    for i in range(29, -1, -1):
        d = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        dates.append(d)
    row_map = {r['date']: r['cnt'] for r in rows}
    for d in dates:
        counts.append(row_map.get(d, 0))

    return jsonify({'dates': dates, 'counts': counts})


# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.pop('teacher', None)
    flash("👋 Logged out successfully.", "success")
    return redirect('/login')


# ----------------------------
# Run the Flask App
# ----------------------------
if __name__ == '__main__':
    app.run(debug=True)
