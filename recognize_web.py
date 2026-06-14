# recognize_web.py
import cv2
import numpy as np
import os
import sqlite3
import json
from datetime import datetime

# Haar cascade
face_cascade = cv2.CascadeClassifier('haarcascades/haarcascade_frontalface_default.xml')
if face_cascade.empty():
    raise RuntimeError("Could not load haarcascade_frontalface_default.xml")

# Check model exists before importing functions that use it
TRAINER_PATH = "trainer/trainer.yml"
LABELS_PATH = "trainer/labels.json"

if not os.path.exists(TRAINER_PATH):
    print("⚠️ No trained model found! Please run train_model.py first.")
    # Do not exit here to allow import in parts that only need DB util, but functions will check later.

# Load recognizer safely
def _load_recognizer():
    if not os.path.exists(TRAINER_PATH):
        raise FileNotFoundError("trainer/trainer.yml not found. Train model first.")
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_PATH)
    return recognizer

def _load_labels():
    if not os.path.exists(LABELS_PATH):
        return {}
    with open(LABELS_PATH, "r") as f:
        return json.load(f)

# Attendance DB helper
def mark_attendance(user_id, name, lecture):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    current_date = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H:%M:%S")

    c.execute('SELECT * FROM attendance WHERE user_id=? AND date=? AND lecture=?',
              (user_id, current_date, lecture))
    result = c.fetchone()
    if result is None:
        c.execute('INSERT INTO attendance (user_id, name, lecture, date, timestamp) VALUES (?, ?, ?, ?, ?)',
                  (user_id, name, lecture, current_date, timestamp))
        conn.commit()
        print(f"✅ Attendance marked for {name} ({lecture})")
    else:
        print(f"⚠️ Attendance already marked for {name} ({lecture})")
    conn.close()

# Real-time recognition (webcam)
def recognize_faces(lecture_name="Default Lecture"):
    recognizer = _load_recognizer()
    labels = _load_labels()

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("❌ Error: Could not access camera.")
        return

    font = cv2.FONT_HERSHEY_SIMPLEX
    print(f"🎥 Starting real-time face recognition for lecture: {lecture_name}")

    while True:
        ret, frame = cam.read()
        if not ret:
            print("⚠️ Camera not detected.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80,80))

        for (x, y, w, h) in faces:
            pad = int(0.15 * w)
            x1 = max(0, x - pad); y1 = max(0, y - pad)
            x2 = min(frame.shape[1], x + w + pad); y2 = min(frame.shape[0], y + h + pad)
            face = gray[y1:y2, x1:x2]
            try:
                face_resized = cv2.resize(face, (200, 200))
            except Exception:
                face_resized = face

            user_id, confidence = recognizer.predict(face_resized)

            # LBPH: lower confidence means better match. threshold depends on data; 70 is a safe start.
            if confidence < 70:
                name = labels.get(str(user_id), labels.get(user_id, "Unknown"))
                mark_attendance(user_id, name, lecture_name)
                color = (0, 255, 0)
                text = f"{name} ({round(100 - confidence)}%)"
            else:
                name = "Unknown"
                color = (0, 0, 255)
                text = "Unknown"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, text, (x1, y1-10), font, 0.8, color, 2)

        cv2.imshow("Face Recognition - Press 'q' to Quit", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()
    print("🛑 Recognition stopped.")

# Recognition from uploaded image (used by /upload_photo)
def recognize_faces_from_image(image_path, lecture_name="Default Lecture"):
    if not os.path.exists(TRAINER_PATH):
        raise FileNotFoundError("trainer/trainer.yml not found. Train model first.")
    recognizer = _load_recognizer()
    labels = _load_labels()

    img = cv2.imread(image_path)
    if img is None:
        print("❌ Could not read image:", image_path)
        return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40,40))

    recognized = []

    for (x, y, w, h) in faces:
        pad = int(0.15 * w)
        x1 = max(0, x - pad); y1 = max(0, y - pad)
        x2 = min(img.shape[1], x + w + pad); y2 = min(img.shape[0], y + h + pad)
        face = gray[y1:y2, x1:x2]
        try:
            face_resized = cv2.resize(face, (200, 200))
        except Exception:
            face_resized = face

        user_id, confidence = recognizer.predict(face_resized)
        if confidence < 70:
            name = labels.get(str(user_id), labels.get(user_id, "Unknown"))
            mark_attendance(user_id, name, lecture_name)
            recognized.append(name)
        else:
            recognized.append("Unknown")

    print("✅ Recognized from image:", recognized)
    return recognized
