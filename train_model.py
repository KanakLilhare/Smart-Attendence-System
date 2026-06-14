# train_model.py
import cv2
import os
import numpy as np
import json

dataset_dir = "dataset"
trainer_dir = "trainer"
os.makedirs(trainer_dir, exist_ok=True)

face_cascade = cv2.CascadeClassifier("haarcascades/haarcascade_frontalface_default.xml")
if face_cascade.empty():
    print("❌ Could not load Haar cascade. Check the file exists.")
    exit()

faces = []
ids = []
labels = {}

# Expect dataset/<id>_<name>/image.jpg
if not os.path.exists(dataset_dir):
    print("❌ dataset/ not found. Capture some images first.")
    exit()

for folder_name in os.listdir(dataset_dir):
    folder_path = os.path.join(dataset_dir, folder_name)
    if not os.path.isdir(folder_path):
        continue
    # folder name format: "<id>_<name>"
    try:
        parts = folder_name.split("_", 1)
        user_id = int(parts[0])
        name = parts[1] if len(parts) > 1 else "Unknown"
    except Exception as e:
        print(f"⚠️ Skipping invalid folder name: {folder_name}")
        continue

    labels[user_id] = name

    for img_name in os.listdir(folder_path):
        if not img_name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        img_path = os.path.join(folder_path, img_name)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            print("⚠️ Could not read:", img_path)
            continue
        # Ensure consistent size
        try:
            img_resized = cv2.resize(img, (200, 200))
        except Exception:
            img_resized = img
        faces.append(img_resized)
        ids.append(user_id)

if len(faces) == 0:
    print("❌ No images found! Run capture_images.py first.")
    exit()

# Create and train LBPH recognizer
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.train(faces, np.array(ids))
recognizer.save(os.path.join(trainer_dir, "trainer.yml"))

# Save labels mapping
with open(os.path.join(trainer_dir, "labels.json"), "w") as f:
    json.dump(labels, f)

print("✅ Model trained successfully and saved in trainer/trainer.yml")
