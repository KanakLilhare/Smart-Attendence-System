# capture_images.py
import cv2
import os
import sys
from datetime import datetime

if len(sys.argv) < 3:
    print("Usage: python capture_images.py <student_id> <student_name>")
    sys.exit(1)

student_id = sys.argv[1].strip()
student_name = sys.argv[2].strip().replace(" ", "_")  # keep folder safe

dataset_root = "dataset"
folder = os.path.join(dataset_root, f"{student_id}_{student_name}")
os.makedirs(folder, exist_ok=True)

haar_path = "haarcascades/haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(haar_path)
if face_cascade.empty():
    print("❌ Could not load Haar cascade. Check path:", haar_path)
    sys.exit(1)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Cannot open camera.")
    sys.exit(1)

count = 0
MAX_IMAGES = 40  # number of images to capture

print(f"📸 Capturing images for {student_name} into {folder}. Press 'q' to stop early.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("⚠️ Failed to read from camera.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))

    for (x, y, w, h) in faces:
        # Expand the box slightly for better coverage
        pad = int(0.15 * w)
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        x2 = min(frame.shape[1], x + w + pad)
        y2 = min(frame.shape[0], y + h + pad)

        face = gray[y1:y2, x1:x2]
        face_resized = cv2.resize(face, (200, 200))  # fixed size used for training & recognition

        count += 1
        img_path = os.path.join(folder, f"{student_id}_{student_name}_{count}.jpg")
        cv2.imwrite(img_path, face_resized)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"Captured: {count}/{MAX_IMAGES}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

    cv2.imshow(f"Capturing {student_name} - Press 'q' to stop", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if count >= MAX_IMAGES:
        break

cap.release()
cv2.destroyAllWindows()

print(f"✅ Captured {count} images for {student_name} into {folder}")
