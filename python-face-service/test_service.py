#!/usr/bin/env python3
"""
Test script for the Python Face Recognition Service
"""

import requests
import base64
import json
from PIL import Image
import io

# Test image (small placeholder)
def create_test_image():
    """Create a simple test image"""
    # Create a simple 100x100 RGB image
    img = Image.new('RGB', (100, 100), color='red')
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG')
    img_data = buffer.getvalue()
    
    return base64.b64encode(img_data).decode('utf-8')

def test_face_service():
    """Test the face recognition service"""
    base_url = "http://localhost:8001"
    
    print("🧪 Testing Python Face Recognition Service...\n")
    
    # Test 1: Health check
    print("1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Face detection
    print("\n2. Testing face detection...")
    try:
        test_image = create_test_image()
        
        response = requests.post(f"{base_url}/detect", json={
            "image_data": test_image,
            "operation": "detect"
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Face detection successful: {result['message']}")
            print(f"   Detected {len(result['faces'])} faces")
        else:
            print(f"❌ Face detection failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Face detection failed: {e}")
    
    # Test 3: Face recognition
    print("\n3. Testing face recognition...")
    try:
        test_image = create_test_image()
        
        response = requests.post(f"{base_url}/recognize", json={
            "image_data": test_image,
            "known_faces": []  # Empty list for now
        })
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Face recognition successful: {result['message']}")
        else:
            print(f"❌ Face recognition failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Face recognition failed: {e}")
    
    print("\n🎉 Python Face Recognition Service test completed!")
    return True

if __name__ == "__main__":
    test_face_service()
