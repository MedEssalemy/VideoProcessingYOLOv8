from fastapi import FastAPI, File, UploadFile, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from ultralytics import YOLO
import cv2
import tempfile
import os
import uuid
import time

app = FastAPI()

# Allow access from anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job status storage
jobs = {}  # In-memory storage (would use Redis in production)

# Load YOLOv8n (smallest model)
model = YOLO("models/yolov8n.pt")

@app.post("/submit_video/")
async def submit_video(background_tasks: BackgroundTasks, video: UploadFile = File(...)):
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save video temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(await video.read())
        tmp_path = tmp.name
    
    # Initialize job status
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "result": None,
        "video_path": tmp_path
    }
    
    # Process in background
    background_tasks.add_task(process_video, job_id)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/job_status/{job_id}")
async def job_status(job_id: str):
    if job_id not in jobs:
        return {"error": "Job not found"}
    
    return jobs[job_id]

def process_video(job_id: str):
    try:
        # Update status
        jobs[job_id]["status"] = "processing"
        
        # Get video path
        video_path = jobs[job_id]["video_path"]
        
        # Process video
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_skip = max(5, total_frames // 10)  # Process at most ~10 frames
        
        apple_count = 0
        processed_frames = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if int(cap.get(cv2.CAP_PROP_POS_FRAMES)) % frame_skip == 0:
                # Run inference with YOLOv8
                results = model(frame, verbose=False)[0]
                
                # Count apples
                for cls_id in results.boxes.cls:
                    if model.names[int(cls_id)] == "apple":
                        apple_count += 1
                
                processed_frames += 1
                
                # Update progress
                progress = min(99, int((processed_frames * frame_skip / total_frames) * 100))
                jobs[job_id]["progress"] = progress
        
        cap.release()
        
        # Set result
        jobs[job_id]["result"] = {
            "apple_count": apple_count,
            "frames_processed": processed_frames,
            "total_frames": total_frames
        }
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
    
    finally:
        # Clean up
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except:
            pass

# Cleanup job - remove old jobs periodically
@app.on_event("startup")
def setup_periodic_cleanup():
    # In a real app, implement a periodic cleanup task
    pass