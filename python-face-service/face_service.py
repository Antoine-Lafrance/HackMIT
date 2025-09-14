#!/usr/bin/env python3
"""
Python Facial Recognition Microservice
Provides face detection and recognition capabilities for the MCP server
Uses OpenCV for face detection (simpler than face_recognition)
"""

import base64
import io
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from PIL import Image
import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Face Recognition Service",
    description="Facial recognition microservice for MCP server",
    version="1.0.0"
)

# Pydantic models for request/response
class FaceDetectionRequest(BaseModel):
    image_data: str  # Base64 encoded image
    operation: str   # "detect", "recognize", "add_face"

class FaceDetectionResponse(BaseModel):
    success: bool
    faces: List[Dict[str, Any]]
    message: str
    error: Optional[str] = None

class FaceRecognitionRequest(BaseModel):
    image_data: str
    known_faces: List[Dict[str, Any]]  # List of known face encodings

class FaceRecognitionResponse(BaseModel):
    success: bool
    person: Optional[str] = None
    relationship: Optional[str] = None
    confidence: Optional[float] = None
    color: Optional[str] = None
    message: str
    error: Optional[str] = None

class FaceService:
    """Main face recognition service class"""
    
    def __init__(self):
        self.known_faces = {}  # In-memory storage for demo
        # Load OpenCV face cascade classifier
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        logger.info("Face recognition service initialized with OpenCV")
    
    def decode_image(self, base64_image: str) -> np.ndarray:
        """Decode base64 image to numpy array"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]
            
            # Decode base64
            image_data = base64.b64decode(base64_image)
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to numpy array
            image_array = np.array(image)
            
            return image_array
            
        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid image data: {e}")
    
    def detect_faces(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces in image and return face encodings"""
        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            
            # Detect faces using OpenCV
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            if len(faces) == 0:
                return []
            
            detected_faces = []
            for i, (x, y, w, h) in enumerate(faces):
                # Create a simple "embedding" based on face region hash
                face_region = gray[y:y+h, x:x+w]
                face_hash = hashlib.md5(face_region.tobytes()).hexdigest()
                
                # Create a simple 128-dimensional embedding from hash
                embedding = self._create_embedding_from_hash(face_hash)
                
                face_data = {
                    "face_id": f"face_{i}",
                    "encoding": embedding,
                    "location": {
                        "top": int(y),
                        "right": int(x + w),
                        "bottom": int(y + h),
                        "left": int(x)
                    },
                    "confidence": 0.85,  # OpenCV doesn't provide confidence scores
                    "name": "Unknown",
                    "relationship": "Unknown",
                    "color": "gray"
                }
                detected_faces.append(face_data)
            
            logger.info(f"Detected {len(detected_faces)} faces using OpenCV")
            return detected_faces
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            raise HTTPException(status_code=500, detail=f"Face detection failed: {e}")
    
    def _create_embedding_from_hash(self, face_hash: str) -> List[float]:
        """Create a 128-dimensional embedding from face hash"""
        # Use the hash to create a deterministic embedding
        embedding = []
        for i in range(128):
            # Use different parts of the hash to create the embedding
            hash_part = face_hash[i % len(face_hash):(i % len(face_hash)) + 2]
            value = int(hash_part, 16) / 255.0  # Normalize to 0-1
            embedding.append(value)
        return embedding
    
    def recognize_faces(self, image_array: np.ndarray, known_faces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Recognize faces against known faces"""
        try:
            # Detect faces in the image using OpenCV
            detected_faces = self.detect_faces(image_array)
            
            if not detected_faces:
                return []
            
            recognized_faces = []
            
            for face in detected_faces:
                # Compare with known faces using simple distance
                best_match = None
                best_distance = float('inf')
                
                for known_face in known_faces:
                    if 'encoding' in known_face:
                        known_encoding = np.array(known_face['encoding'])
                        current_encoding = np.array(face['encoding'])
                        
                        # Calculate simple Euclidean distance
                        distance = np.linalg.norm(known_encoding - current_encoding)
                        
                        # Threshold for recognition (adjust as needed)
                        if distance < 0.5 and distance < best_distance:
                            best_distance = distance
                            best_match = known_face
                
                # Update face data with recognition results
                face['confidence'] = max(0, 1 - best_distance) if best_match else face['confidence']
                face['name'] = best_match.get('name', 'Unknown') if best_match else 'Unknown'
                face['relationship'] = best_match.get('relationship', 'Unknown') if best_match else 'Unknown'
                face['color'] = best_match.get('color', 'gray') if best_match else 'gray'
                
                recognized_faces.append(face)
            
            logger.info(f"Recognized {len(recognized_faces)} faces")
            return recognized_faces
            
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            raise HTTPException(status_code=500, detail=f"Face recognition failed: {e}")

# Initialize the service
face_service = FaceService()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Face Recognition Service is running", "status": "healthy"}

@app.post("/detect", response_model=FaceDetectionResponse)
async def detect_faces(request: FaceDetectionRequest):
    """Detect faces in an image"""
    try:
        logger.info("Face detection request received")
        
        # Decode image
        image_array = face_service.decode_image(request.image_data)
        
        # Detect faces
        faces = face_service.detect_faces(image_array)
        
        return FaceDetectionResponse(
            success=True,
            faces=faces,
            message=f"Detected {len(faces)} faces"
        )
        
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        return FaceDetectionResponse(
            success=False,
            faces=[],
            message="Face detection failed",
            error=str(e)
        )

@app.post("/recognize", response_model=FaceRecognitionResponse)
async def recognize_faces(request: FaceRecognitionRequest):
    """Recognize faces in an image against known faces"""
    try:
        logger.info("Face recognition request received")
        
        # Decode image
        image_array = face_service.decode_image(request.image_data)
        
        # Recognize faces
        faces = face_service.recognize_faces(image_array, request.known_faces)
        
        if not faces:
            return FaceRecognitionResponse(
                success=False,
                message="No faces detected in the image"
            )
        
        # Return the first recognized face (for simplicity)
        face = faces[0]
        
        if face['name'] != 'Unknown':
            return FaceRecognitionResponse(
                success=True,
                person=face['name'],
                relationship=face['relationship'],
                confidence=face['confidence'],
                color=face['color'],
                message=f"Recognized {face['name']} ({face['relationship']})"
            )
        else:
            return FaceRecognitionResponse(
                success=False,
                person='Unknown',
                relationship='Unknown',
                confidence=face['confidence'],
                message="Face detected but not recognized. Consider adding this person to the database."
            )
        
    except Exception as e:
        logger.error(f"Face recognition error: {e}")
        return FaceRecognitionResponse(
            success=False,
            message="Face recognition failed",
            error=str(e)
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "face-recognition"}

if __name__ == "__main__":
    logger.info("Starting Face Recognition Service...")
    uvicorn.run(
        "face_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
