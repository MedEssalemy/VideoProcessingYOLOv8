from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import cv2
import tempfile
import os

app = FastAPI()

# Allow access from FlutterFlow or localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific domain for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load YOLOv8 model (place in `models/` directory)
model = YOLO("models/yolov8n.pt")  # Replace with fine-tuned model if needed

@app.post("/detect_apples/")
async def detect_apples(video: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name

    cap = cv2.VideoCapture(tmp_path)
    apple_count = 0
    frame_skip = 5  # Process every 5th frame for performance

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % frame_skip == 0:
            results = model(frame)[0]
            for cls_id in results.boxes.cls:
                if model.names[int(cls_id)] == "apple":
                    apple_count += 1

    cap.release()
    os.remove(tmp_path)

    return {"apple_count": apple_count}
