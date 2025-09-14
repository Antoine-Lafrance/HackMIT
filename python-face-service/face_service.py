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

# Configure logging with more detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

# Face recognition models removed - handled by MCP server

# Person search models removed - handled by MCP server

class FaceService:
    """Main face recognition service class"""
    
    def __init__(self):
        # Load OpenCV face cascade classifier
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Face tracking state
        self.previous_faces = []
        self.face_tracking_threshold = 0.3  # IoU threshold for face tracking
        self.min_face_confidence = 0.6      # Minimum confidence for face acceptance
        self.max_faces = 5                  # Maximum number of faces to track
        
        # Face detection only - database operations handled by MCP server
        self.similarity_threshold = 0.7  # Threshold for person matching
        
        logger.info("Face detection service initialized with OpenCV and face tracking")
    
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
            
            # Apply histogram equalization for better contrast
            gray = cv2.equalizeHist(gray)
            
            # Detect faces using OpenCV with more conservative parameters
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.05,      # More conservative scaling
                minNeighbors=8,         # Higher threshold to reduce false positives
                minSize=(50, 50),       # Larger minimum size for better quality
                maxSize=(300, 300),     # Maximum size to avoid false positives
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            if len(faces) == 0:
                # No faces detected, but still update tracking state
                self.previous_faces = []
                return []
            
            detected_faces = []
            for i, (x, y, w, h) in enumerate(faces):
                # Calculate face quality metrics
                face_region = gray[y:y+h, x:x+w]
                
                # Calculate face size and aspect ratio
                face_area = w * h
                aspect_ratio = w / h if h > 0 else 1.0
                
                # Calculate face quality based on size and aspect ratio
                # Optimal face size is around 80x100 (typical face proportions)
                optimal_area = 80 * 100
                size_quality = min(1.0, face_area / optimal_area)
                
                # Optimal aspect ratio for faces is around 0.8 (width/height)
                optimal_ratio = 0.8
                aspect_quality = 1.0 - abs(aspect_ratio - optimal_ratio) / optimal_ratio
                aspect_quality = max(0.0, min(1.0, aspect_quality))  # Clamp to [0,1]
                
                # Combine size and aspect ratio with equal weight
                quality_score = (size_quality + aspect_quality) / 2.0
                
                # Only process faces above minimum quality threshold
                if quality_score < self.min_face_confidence:
                    logger.debug(f"Face {i} rejected due to low quality: {quality_score:.2f}")
                    continue
                
                # Create face embedding from actual face features
                embedding = self._create_embedding_from_face(face_region)
                
                face_data = {
                    "face_id": f"face_{i}",
                    "encoding": embedding,
                    "location": {
                        "top": int(y),
                        "right": int(x + w),
                        "bottom": int(y + h),
                        "left": int(x)
                    },
                    "confidence": quality_score,
                    "name": "Unknown",
                    "relationship": "Unknown",
                    "color": "gray",
                    "quality_score": quality_score
                }
                detected_faces.append(face_data)
            
            # Apply face tracking to reduce fluctuation
            tracked_faces = self._track_faces(detected_faces)
            
            # Filter faces by tracking confidence
            stable_faces = []
            for face in tracked_faces:
                track_confidence = face.get('track_confidence', 0.5)
                if track_confidence >= 0.3:  # Only show faces with stable tracking
                    stable_faces.append(face)
            
            logger.info(f"Detected {len(faces)} raw faces, {len(detected_faces)} quality-filtered, {len(stable_faces)} stable")
            return stable_faces
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            raise HTTPException(status_code=500, detail=f"Face detection failed: {e}")
    
    def _create_embedding_from_face(self, face_region: np.ndarray) -> List[float]:
        """Create a 512-dimensional embedding from face region"""
        # Create a more meaningful embedding based on face features
        # This is a simplified approach - in production, use a proper face recognition model
        
        # Resize face to standard size
        face_resized = cv2.resize(face_region, (64, 64))
        
        # Extract features: histogram, gradients, and texture
        features = []
        
        # 1. Histogram features (64 values)
        hist = cv2.calcHist([face_resized], [0], None, [64], [0, 256])
        features.extend(hist.flatten() / 255.0)
        
        # 2. Gradient features (64 values)
        grad_x = cv2.Sobel(face_resized, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(face_resized, cv2.CV_64F, 0, 1, ksize=3)
        grad_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        # Normalize gradient magnitude properly
        grad_normalized = grad_magnitude / (np.max(grad_magnitude) + 1e-8)
        features.extend(grad_normalized.flatten())
        
        # 3. Texture features using LBP-like approach (64 values)
        texture = self._extract_texture_features(face_resized)
        features.extend(texture)
        
        # 4. Spatial features (320 values to reach 512)
        spatial_features = self._extract_spatial_features(face_resized)
        features.extend(spatial_features)
        
        # Ensure we have exactly 512 dimensions
        while len(features) < 512:
            features.append(0.0)
        
        return features[:512]
    
    def _extract_texture_features(self, face_region: np.ndarray) -> List[float]:
        """Extract texture features using local binary patterns"""
        # Simplified LBP implementation
        features = []
        for i in range(0, face_region.shape[0], 8):
            for j in range(0, face_region.shape[1], 8):
                patch = face_region[i:i+8, j:j+8]
                if patch.shape == (8, 8):
                    # Calculate local variance as texture measure
                    variance = np.var(patch)
                    features.append(variance / 255.0)
        return features[:64]  # Return exactly 64 features
    
    def _extract_spatial_features(self, face_region: np.ndarray) -> List[float]:
        """Extract spatial features from face region"""
        features = []
        
        # Divide face into regions and extract features
        h, w = face_region.shape
        for i in range(4):  # 4x4 grid
            for j in range(4):
                y1, y2 = i * h // 4, (i + 1) * h // 4
                x1, x2 = j * w // 4, (j + 1) * w // 4
                region = face_region[y1:y2, x1:x2]
                
                if region.size > 0:
                    # Mean and std of each region
                    features.append(np.mean(region) / 255.0)
                    features.append(np.std(region) / 255.0)
        
        # Pad to 320 features
        while len(features) < 320:
            features.append(0.0)
        
        return features[:320]
    
    def _calculate_iou(self, box1: Dict, box2: Dict) -> float:
        """Calculate Intersection over Union (IoU) between two face boxes"""
        # Extract coordinates
        x1_1, y1_1, w1, h1 = box1['left'], box1['top'], box1['right'] - box1['left'], box1['bottom'] - box1['top']
        x1_2, y1_2, w2, h2 = box2['left'], box2['top'], box2['right'] - box2['left'], box2['bottom'] - box2['top']
        
        # Calculate intersection
        x2_1, y2_1 = x1_1 + w1, y1_1 + h1
        x2_2, y2_2 = x1_2 + w2, y1_2 + h2
        
        xi1 = max(x1_1, x1_2)
        yi1 = max(y1_1, y1_2)
        xi2 = min(x2_1, x2_2)
        yi2 = min(y2_1, y2_2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        intersection = (xi2 - xi1) * (yi2 - yi1)
        union = w1 * h1 + w2 * h2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _track_faces(self, current_faces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Track faces across frames to reduce fluctuation"""
        if not self.previous_faces:
            # First frame, accept all faces
            tracked_faces = current_faces.copy()
        else:
            tracked_faces = []
            
            for current_face in current_faces:
                best_match = None
                best_iou = 0.0
                
                # Find best matching previous face
                for prev_face in self.previous_faces:
                    iou = self._calculate_iou(current_face['location'], prev_face['location'])
                    if iou > self.face_tracking_threshold and iou > best_iou:
                        best_iou = iou
                        best_match = prev_face
                
                if best_match:
                    # Update face with tracking info
                    current_face['track_id'] = best_match.get('track_id', f"face_{len(tracked_faces)}")
                    current_face['track_confidence'] = min(1.0, best_match.get('track_confidence', 0.5) + 0.1)
                    tracked_faces.append(current_face)
                else:
                    # New face
                    current_face['track_id'] = f"face_{len(tracked_faces)}"
                    current_face['track_confidence'] = 0.5
                    tracked_faces.append(current_face)
        
        # Update previous faces for next frame
        self.previous_faces = tracked_faces[:self.max_faces]
        
        return tracked_faces
    
    # Database operations removed - handled by MCP server
    
    # recognize_faces method removed - handled by MCP server

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
