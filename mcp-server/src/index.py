#!/usr/bin/env python3
"""
src/index.py
Python translation of the MCP server for dementia aid tools with integrated face recognition
"""

import asyncio
import base64
import io
import json
import logging
import os
import signal
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import cv2
import numpy as np
from PIL import Image
import modal
from mcp import ClientSession, StdioServerParameters
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
)


class PythonFaceRecognitionService:
    """Integrated face recognition service directly in MCP server"""

    def __init__(self):
        # Load OpenCV face cascade classifier
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        # Face tracking state
        self.previous_faces = []
        self.face_tracking_threshold = 0.3  # IoU threshold for face tracking
        self.min_face_confidence = 0.6  # Minimum confidence for face acceptance
        self.max_faces = 5  # Maximum number of faces to track

        # Face detection only - database operations handled by MCP server
        self.similarity_threshold = 0.7  # Threshold for person matching

        logger.info("Face detection service initialized with OpenCV and face tracking")

    def decode_image(self, base64_image: str) -> np.ndarray:
        """Decode base64 image to numpy array"""
        try:
            # Remove data URL prefix if present
            if "," in base64_image:
                base64_image = base64_image.split(",")[1]

            # Decode base64
            image_data = base64.b64decode(base64_image)

            # Convert to PIL Image
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Convert to numpy array
            image_array = np.array(image)

            return image_array

        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            raise Exception(f"Invalid image data: {e}")

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
                scaleFactor=1.05,  # More conservative scaling
                minNeighbors=8,  # Higher threshold to reduce false positives
                minSize=(50, 50),  # Larger minimum size for better quality
                maxSize=(300, 300),  # Maximum size to avoid false positives
                flags=cv2.CASCADE_SCALE_IMAGE,
            )

            if len(faces) == 0:
                # No faces detected, but still update tracking state
                self.previous_faces = []
                return []

            detected_faces = []
            for i, (x, y, w, h) in enumerate(faces):
                # Calculate face quality metrics
                face_region = gray[y : y + h, x : x + w]

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
                    logger.debug(
                        f"Face {i} rejected due to low quality: {quality_score:.2f}"
                    )
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
                        "left": int(x),
                    },
                    "confidence": quality_score,
                    "name": "Unknown",
                    "relationship": "Unknown",
                    "color": "gray",
                    "quality_score": quality_score,
                }
                detected_faces.append(face_data)

            # Apply face tracking to reduce fluctuation
            tracked_faces = self._track_faces(detected_faces)

            # Filter faces by tracking confidence
            stable_faces = []
            for face in tracked_faces:
                track_confidence = face.get("track_confidence", 0.5)
                if track_confidence >= 0.3:  # Only show faces with stable tracking
                    stable_faces.append(face)

            logger.info(
                f"Detected {len(faces)} raw faces, {len(detected_faces)} quality-filtered, {len(stable_faces)} stable"
            )
            return stable_faces

        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            raise Exception(f"Face detection failed: {e}")

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
                patch = face_region[i : i + 8, j : j + 8]
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
        x1_1, y1_1, w1, h1 = (
            box1["left"],
            box1["top"],
            box1["right"] - box1["left"],
            box1["bottom"] - box1["top"],
        )
        x1_2, y1_2, w2, h2 = (
            box2["left"],
            box2["top"],
            box2["right"] - box2["left"],
            box2["bottom"] - box2["top"],
        )

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
                    iou = self._calculate_iou(
                        current_face["location"], prev_face["location"]
                    )
                    if iou > self.face_tracking_threshold and iou > best_iou:
                        best_iou = iou
                        best_match = prev_face

                if best_match:
                    # Update face with tracking info
                    current_face["track_id"] = best_match.get(
                        "track_id", f"face_{len(tracked_faces)}"
                    )
                    current_face["track_confidence"] = min(
                        1.0, best_match.get("track_confidence", 0.5) + 0.1
                    )
                    tracked_faces.append(current_face)
                else:
                    # New face
                    current_face["track_id"] = f"face_{len(tracked_faces)}"
                    current_face["track_confidence"] = 0.5
                    tracked_faces.append(current_face)

        # Update previous faces for next frame
        self.previous_faces = tracked_faces[: self.max_faces]

        return tracked_faces

    async def recognize_face(
        self,
        image_data: str,
        person_name: Optional[str] = None,
        person_relationship: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recognize faces in an image and optionally add new person"""
        try:
            # Decode image
            image_array = self.decode_image(image_data)

            # Detect faces
            faces = self.detect_faces(image_array)

            if len(faces) == 0:
                return {
                    "success": False,
                    "person": "Unknown",
                    "relationship": "Unknown",
                    "message": "No faces detected in the image",
                }

            # Use the first detected face
            face = faces[0]
            face_embedding = face.get("encoding", [])

            if not face_embedding:
                return {
                    "success": False,
                    "person": "Unknown",
                    "relationship": "Unknown",
                    "message": "Could not generate face embedding",
                }

            # Search for existing person in database
            existing_person = await self.search_face(face_embedding)

            if existing_person:
                # Person found in database
                return {
                    "success": True,
                    "person": existing_person["name"],
                    "relationship": existing_person["relationship"],
                    "confidence": 0.8,  # Default confidence for database matches
                    "color": existing_person.get("color", "blue"),
                    "is_new_person": False,
                    "message": f"Found existing person: {existing_person['name']} ({existing_person['relationship']})",
                }
            else:
                # Person not found, add new person if name/relationship provided
                if person_name and person_relationship:
                    new_face = await self.add_face(
                        {
                            "name": person_name,
                            "relationship": person_relationship,
                            "face_embedding": face_embedding,
                            "color": self._get_random_color(),
                        }
                    )

                    if new_face:
                        return {
                            "success": True,
                            "person": new_face["name"],
                            "relationship": new_face["relationship"],
                            "confidence": 1.0,
                            "color": new_face["color"],
                            "is_new_person": True,
                            "message": f"Added new person: {new_face['name']} ({new_face['relationship']})",
                        }

                return {
                    "success": False,
                    "person": "Unknown",
                    "relationship": "Unknown",
                    "confidence": face.get("confidence", 0.0),
                    "message": "Face detected but not recognized. Provide name and relationship to add new person.",
                }

        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return {
                "success": False,
                "person": "Unknown",
                "relationship": "Unknown",
                "message": "Face recognition failed",
                "error": str(e),
            }

    def _get_random_color(self) -> str:
        """Get a random color for new faces"""
        colors = ["red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"]
        import random

        return random.choice(colors)

    async def process_image(self, image_data: str) -> np.ndarray:
        """Process image and return numpy array"""
        return self.decode_image(image_data)

    async def add_face(self, face_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Add a face to the database"""
        try:
            # Insert face data into Supabase
            result = supabase.table("faces").insert(face_data).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return None

        except Exception as e:
            logger.error(f"Error adding face to database: {e}")
            return None

    async def get_all_faces(self) -> List[Dict[str, Any]]:
        """Get all faces from the database"""
        try:
            result = supabase.table("faces").select("*").execute()
            return result.data if result.data else []

        except Exception as e:
            logger.error(f"Error getting faces from database: {e}")
            return []

    async def search_face(
        self, face_embedding: List[float], threshold: float = 0.7
    ) -> Optional[Dict[str, Any]]:
        """Search for a face in the database using cosine similarity"""
        try:
            # Get all faces from database
            all_faces = await self.get_all_faces()

            if not all_faces:
                return None

            best_match = None
            best_similarity = 0.0

            for face in all_faces:
                if face.get("face_embedding"):
                    # Calculate cosine similarity
                    similarity = self._cosine_similarity(
                        face_embedding, face["face_embedding"]
                    )

                    if similarity > threshold and similarity > best_similarity:
                        best_similarity = similarity
                        best_match = face

            return best_match

        except Exception as e:
            logger.error(f"Error searching face in database: {e}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return dot_product / (norm1 * norm2)
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0


from supabase import create_client, Client


load_dotenv()


url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize face recognition service
python_face_recognition_service = PythonFaceRecognitionService()

# Server initialization - creates core MCP server instance
server = Server("dementia-aid-mcp-server")

# Tool definitions - defines the tools that the server can call

ping_tool = Tool(
    name="ping",
    description="Simple ping tool to test MCP connection",
    inputSchema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Message to echo back",
                "default": "Hello from MCP!",
            },
        },
        "required": [],
    },
)

# Face recognition tool
face_recognition_tool = Tool(
    name="recognize_face",
    description="Identify a person from camera input using facial recognition. If person not found and name/relationship provided, adds new person to database.",
    inputSchema={
        "type": "object",
        "properties": {
            "image_data": {
                "type": "string",
                "description": "Base64 encoded image data",
            },
            "person_name": {
                "type": "string",
                "description": "Name of the person (optional - if provided, will be used for new person creation)",
            },
            "person_relationship": {
                "type": "string",
                "description": "Relationship to the person (optional - if provided, will be used for new person creation)",
            },
        },
        "required": ["image_data"],
    },
)

timer_tool = Tool(
    name="manage_timer",
    description="Timer management for time-sensitive events",
    inputSchema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["set"],
                "description": "Timer action",
            },
            "duration_minutes": {
                "type": "number",
                "description": "Duration in minutes",
            },
        },
        "required": ["action"],
    },
)

location_tool = Tool(
    name="monitor_location",
    description="Location monitoring and safety checks",
    inputSchema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_safety"],
                "description": "Location action",
            },
        },
        "required": ["action"],
    },
)

list_tools_tool = Tool(
    name="list_tools",
    description="List all available tools with their descriptions, arguments, and Modal endpoint URLs",
    inputSchema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

# Tool handlers - contains the logic for each tool


async def handle_ping(args: Dict[str, Any]) -> CallToolResult:
    """Handle ping tool requests"""
    message = args.get("message", "Hello from MCP!")
    logger.info(f"Ping received: {message}")

    response_data = {
        "success": True,
        "echo": message,
        "timestamp": datetime.now().isoformat(),
        "server": "dementia-aid-mcp-server",
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data))]
    )


async def handle_face_recognition(args: Dict[str, Any]) -> CallToolResult:
    """Handle face recognition tool requests"""
    image_data = args.get("image_data")
    person_name = args.get("person_name")
    person_relationship = args.get("person_relationship")

    logger.info(
        f"Face recognition called with person_name: {person_name}, person_relationship: {person_relationship}"
    )

    try:
        # Use the unified recognize_face method
        recognition_result = await python_face_recognition_service.recognize_face(
            image_data, person_name, person_relationship
        )

        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(recognition_result))]
        )

    except Exception as error:
        logger.error(f"Face recognition error: {error}")
        error_response = {
            "success": False,
            "person": "Unknown",
            "relationship": "Unknown",
            "message": "Face recognition failed",
            "error": str(error),
        }
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(error_response))]
        )


async def handle_timer(args: Dict[str, Any]) -> CallToolResult:
    """Handle timer tool requests"""
    logger.info("Timer management called")

    response_data = {
        "success": True,
        "message": "Timer processing...",
        "timer_id": f"timer_{int(datetime.now().timestamp() * 1000)}",
        "duration": args.get("duration_minutes", 30),
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data))]
    )


async def handle_location(args: Dict[str, Any]) -> CallToolResult:
    """Handle location monitoring tool requests"""
    logger.info("Location monitoring called")

    response_data = {
        "success": True,
        "message": "Location processing...",
        "is_safe": True,
        "location": "Unknown",
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data))]
    )


async def handle_list_tools_info(args: Dict[str, Any]) -> CallToolResult:
    """Handle list tools info requests"""
    logger.info("Tools list info requested")

    # Define the base Modal URL (you might want to make this configurable)
    modal_base_url = ""

    tools_info = [
        {
            "name": "ping",
            "description": "Simple ping tool to test MCP connection",
            "modal_endpoint": f"{modal_base_url}ping.modal.run",
            "method": "POST",
            "arguments": {
                "message": {
                    "type": "string",
                    "description": "Message to echo back",
                    "required": False,
                    "default": "Hello from MCP!",
                }
            },
        },
        {
            "name": "recognize_face",
            "description": "Identify a person from camera input using facial recognition. If person not found and name/relationship provided, adds new person to database.",
            "modal_endpoint": f"{modal_base_url}face-recognition.modal.run",
            "method": "POST",
            "arguments": {
                "image_data": {
                    "type": "string",
                    "description": "Base64 encoded image data",
                    "required": True,
                },
                "person_name": {
                    "type": "string",
                    "description": "Name of the person (optional - if provided, will be used for new person creation)",
                    "required": False,
                },
                "person_relationship": {
                    "type": "string",
                    "description": "Relationship to the person (optional - if provided, will be used for new person creation)",
                    "required": False,
                },
            },
        },
        {
            "name": "manage_timer",
            "description": "Timer management for time-sensitive events",
            "modal_endpoint": f"{modal_base_url}timer.modal.run",
            "method": "POST",
            "arguments": {
                "action": {
                    "type": "string",
                    "enum": ["set"],
                    "description": "Timer action",
                    "required": True,
                },
                "duration_minutes": {
                    "type": "number",
                    "description": "Duration in minutes",
                    "required": False,
                },
            },
        },
        {
            "name": "monitor_location",
            "description": "Location monitoring and safety checks",
            "modal_endpoint": f"{modal_base_url}location.modal.run",
            "method": "POST",
            "arguments": {
                "action": {
                    "type": "string",
                    "enum": ["check_safety"],
                    "description": "Location action",
                    "required": True,
                }
            },
        },
        {
            "name": "list_tools",
            "description": "List all available tools with their descriptions, arguments, and Modal endpoint URLs",
            "modal_endpoint": f"{modal_base_url}list-tools.modal.run",
            "method": "GET",
            "arguments": {},
        },
    ]

    response_data = {
        "success": True,
        "tools": tools_info,
        "total_tools": len(tools_info),
        "server": "dementia-aid-mcp-server",
        "timestamp": datetime.now().isoformat(),
        "health_check_endpoint": f"{modal_base_url}health.modal.run",
    }

    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# Request handlers - handles the requests from the client


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """Handle list tools requests"""
    logger.info("Tools list requested")
    return [
        ping_tool,
        face_recognition_tool,
        timer_tool,
        location_tool,
        list_tools_tool,
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """Handle tool call requests"""
    logger.info(f"Tool called: {name}, args: {arguments}")

    try:
        if name == "ping":
            return await handle_ping(arguments)
        elif name == "recognize_face":
            return await handle_face_recognition(arguments)
        elif name == "manage_timer":
            return await handle_timer(arguments)
        elif name == "monitor_location":
            return await handle_location(arguments)
        elif name == "list_tools":
            return await handle_list_tools_info(arguments)
        else:
            from mcp.types import McpError, ErrorCode

            raise McpError(ErrorCode.METHOD_NOT_FOUND, f"Unknown tool: {name}")

    except Exception as error:
        logger.error(f"Error in tool {name}: {error}")
        from mcp.types import McpError, ErrorCode

        raise McpError(ErrorCode.INTERNAL_ERROR, f"Tool {name} failed: {str(error)}")


# Server startup - starts the server and connects to the client

# Modal app configuration
app = modal.App("dementia-aid-mcp-server")

# Modal image with required dependencies
image = (
    modal.Image.debian_slim()
    .pip_install(
        [
            "mcp",
            "supabase",
            "python-dotenv",
            "opencv-python-headless",
            "Pillow",
            "numpy",
            "fastapi",
            "uvicorn",
        ]
    )
    .apt_install(["libgl1-mesa-glx", "libglib2.0-0"])
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    keep_warm=1,
)
@modal.web_endpoint(method="POST", label="mcp-face-recognition")
async def face_recognition_endpoint(item: dict):
    """Modal web endpoint for face recognition"""
    try:
        logger.info(f"Face recognition API called: {item}")

        # Initialize services if needed
        global python_face_recognition_service, supabase
        if not python_face_recognition_service:
            python_face_recognition_service = PythonFaceRecognitionService()

        image_data = item.get("image_data")
        person_name = item.get("person_name")
        person_relationship = item.get("person_relationship")

        if not image_data:
            return {
                "success": False,
                "message": "image_data is required",
                "error": "Missing image_data parameter",
            }

        result = await python_face_recognition_service.recognize_face(
            image_data, person_name, person_relationship
        )

        return result

    except Exception as e:
        logger.error(f"Face recognition API error: {e}")
        return {"success": False, "message": "Face recognition failed", "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    keep_warm=1,
)
@modal.web_endpoint(method="POST", label="mcp-ping")
async def ping_endpoint(item: dict):
    """Modal web endpoint for ping"""
    try:
        message = item.get("message", "Hello from MCP!")

        response_data = {
            "success": True,
            "echo": message,
            "timestamp": datetime.now().isoformat(),
            "server": "dementia-aid-mcp-server",
        }

        return response_data

    except Exception as e:
        logger.error(f"Ping API error: {e}")
        return {"success": False, "message": "Ping failed", "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    keep_warm=1,
)
@modal.web_endpoint(method="POST", label="mcp-timer")
async def timer_endpoint(item: dict):
    """Modal web endpoint for timer management"""
    try:
        logger.info("Timer management API called")

        response_data = {
            "success": True,
            "message": "Timer processing...",
            "timer_id": f"timer_{int(datetime.now().timestamp() * 1000)}",
            "duration": item.get("duration_minutes", 30),
        }

        return response_data

    except Exception as e:
        logger.error(f"Timer API error: {e}")
        return {"success": False, "message": "Timer failed", "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    keep_warm=1,
)
@modal.web_endpoint(method="POST", label="mcp-location")
async def location_endpoint(item: dict):
    """Modal web endpoint for location monitoring"""
    try:
        logger.info("Location monitoring API called")

        response_data = {
            "success": True,
            "message": "Location processing...",
            "is_safe": True,
            "location": "Unknown",
        }

        return response_data

    except Exception as e:
        logger.error(f"Location API error: {e}")
        return {
            "success": False,
            "message": "Location monitoring failed",
            "error": str(e),
        }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    keep_warm=1,
)
@modal.web_endpoint(method="GET", label="mcp-list-tools")
async def list_tools_endpoint():
    """Modal web endpoint for listing all tools"""
    try:
        logger.info("List tools API called")

        # Define the base Modal URL (you might want to make this configurable)
        modal_base_url = "https://antoinedoyen--dementia-aid-mcp-server-mcp-"

        tools_info = [
            {
                "name": "ping",
                "description": "Simple ping tool to test MCP connection",
                "modal_endpoint": f"{modal_base_url}ping.modal.run",
                "method": "POST",
                "arguments": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back",
                        "required": False,
                        "default": "Hello from MCP!",
                    }
                },
            },
            {
                "name": "recognize_face",
                "description": "Identify a person from camera input using facial recognition. If person not found and name/relationship provided, adds new person to database.",
                "modal_endpoint": f"{modal_base_url}face-recognition.modal.run",
                "method": "POST",
                "arguments": {
                    "image_data": {
                        "type": "string",
                        "description": "Base64 encoded image data",
                        "required": True,
                    },
                    "person_name": {
                        "type": "string",
                        "description": "Name of the person (optional - if provided, will be used for new person creation)",
                        "required": False,
                    },
                    "person_relationship": {
                        "type": "string",
                        "description": "Relationship to the person (optional - if provided, will be used for new person creation)",
                        "required": False,
                    },
                },
            },
            {
                "name": "manage_timer",
                "description": "Timer management for time-sensitive events",
                "modal_endpoint": f"{modal_base_url}timer.modal.run",
                "method": "POST",
                "arguments": {
                    "action": {
                        "type": "string",
                        "enum": ["set"],
                        "description": "Timer action",
                        "required": True,
                    },
                    "duration_minutes": {
                        "type": "number",
                        "description": "Duration in minutes",
                        "required": False,
                    },
                },
            },
            {
                "name": "monitor_location",
                "description": "Location monitoring and safety checks",
                "modal_endpoint": f"{modal_base_url}location.modal.run",
                "method": "POST",
                "arguments": {
                    "action": {
                        "type": "string",
                        "enum": ["check_safety"],
                        "description": "Location action",
                        "required": True,
                    }
                },
            },
            {
                "name": "list_tools",
                "description": "List all available tools with their descriptions, arguments, and Modal endpoint URLs",
                "modal_endpoint": f"{modal_base_url}list-tools.modal.run",
                "method": "GET",
                "arguments": {},
            },
        ]

        response_data = {
            "success": True,
            "tools": tools_info,
            "total_tools": len(tools_info),
            "server": "dementia-aid-mcp-server",
            "timestamp": datetime.now().isoformat(),
            "health_check_endpoint": f"{modal_base_url}health.modal.run",
        }

        return response_data

    except Exception as e:
        logger.error(f"List tools API error: {e}")
        return {"success": False, "message": "List tools failed", "error": str(e)}


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    keep_warm=1,
)
@modal.web_endpoint(method="GET", label="mcp-health")
async def health_endpoint():
    """Modal web endpoint for health check"""
    try:
        # Test Supabase connection
        response = supabase.table("faces").select("count").limit(1).execute()
        db_status = "connected" if response.data is not None else "disconnected"

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "server": "dementia-aid-mcp-server",
            "database": db_status,
            "version": "1.0.0",
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "server": "dementia-aid-mcp-server",
            "error": str(e),
        }


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("supabase-credentials")],
    timeout=300,
)
async def run_mcp_server():
    """Modal function to run the traditional MCP server via stdio"""
    return await main()


async def main():
    """Main function to start the MCP server"""
    logger.info("Starting Dementia Aid MCP Server...")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    try:
        # Initialize Python face recognition service
        logger.info("Initializing Python face recognition service...")
        # await python_face_recognition_service.initialize()

        # Test Supabase connection
        logger.info("Testing Supabase connection...")
        try:
            # Test basic connection
            response = supabase.table("faces").select("count").limit(1).execute()
            if response.data is None:
                logger.warning("Supabase connection warning")
                logger.warning(
                    "Face recognition database features may not work properly"
                )
            else:
                logger.info("✅ Supabase connection successful")

            # Test if faces table exists and is accessible
            table_test = supabase.table("faces").select("id").limit(1).execute()
            if table_test.data is None:
                logger.warning("⚠️  Faces table issue")
                logger.warning("You may need to run the database schema setup")
            else:
                logger.info("✅ Faces table accessible")

            # Test vector extension (if available)
            try:
                dummy_vector = [0.0] * 512  # Dummy vector
                vector_test = supabase.rpc(
                    "match_faces",
                    {
                        "query_embedding": dummy_vector,
                        "match_threshold": 0.1,
                        "match_count": 1,
                    },
                ).execute()

                if vector_test.data is None:
                    logger.warning("⚠️  Vector functions issue")
                    logger.warning(
                        "You may need to run the supabase-functions.sql setup"
                    )
                else:
                    logger.info("✅ Vector functions accessible")
            except Exception as vector_error:
                logger.warning(f"⚠️  Vector functions issue: {vector_error}")
                logger.warning("You may need to run the supabase-functions.sql setup")

        except Exception as connection_error:
            logger.error(f"❌ Supabase connection failed: {connection_error}")
            logger.error("Check your environment variables and network connection")

        # Start the server
        try:
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream, write_stream, server.create_initialization_options()
                )
        except Exception as server_error:
            logger.error(f"Server runtime error: {server_error}")
            import traceback

            traceback.print_exc()
            raise

        logger.info("MCP Server connected and ready!")
        logger.info("Available tools:")
        logger.info("   - ping (test connectivity)")
        logger.info(
            "   - recognize_face (face identification, adding faces, listing faces)"
        )
        logger.info("   - manage_timer (timer management)")
        logger.info("   - monitor_location (location monitoring)")
        logger.info("")
        logger.info("Face recognition usage:")
        logger.info("   - Call recognize_face with image_data (required)")
        logger.info("   - Optionally provide person_name and person_relationship")
        logger.info("   - If person exists in database, returns match")
        logger.info(
            "   - If person doesn't exist and name/relationship provided, adds new person"
        )

    except Exception as error:
        logger.error(f"Failed to start MCP server: {error}")
        sys.exit(1)


# Graceful shutdown handlers
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("\nShutting down MCP server gracefully...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Start server if this is the main module
if __name__ == "__main__":
    asyncio.run(main())
