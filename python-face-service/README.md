# Python Face Recognition Microservice

A high-accuracy facial recognition microservice built with Python, FastAPI, and the `face_recognition` library.

## Features

- **High Accuracy**: Uses the `face_recognition` library (99.38% accuracy)
- **Fast Performance**: Optimized for real-time face detection and recognition
- **RESTful API**: Easy integration with any client
- **Face Detection**: Detect faces in images and return face encodings
- **Face Recognition**: Match faces against known faces
- **Base64 Support**: Accepts base64-encoded images

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Install system dependencies:**
   ```bash
   # On macOS
   brew install cmake
   
   # On Ubuntu/Debian
   sudo apt-get install cmake
   
   # On Windows
   # Install Visual Studio Build Tools
   ```

## Usage

### Start the Service

```bash
python face_service.py
```

The service will start on `http://localhost:8001`

### API Endpoints

#### Health Check
```bash
GET /health
```

#### Face Detection
```bash
POST /detect
Content-Type: application/json

{
  "image_data": "base64_encoded_image",
  "operation": "detect"
}
```

#### Face Recognition
```bash
POST /recognize
Content-Type: application/json

{
  "image_data": "base64_encoded_image",
  "known_faces": [
    {
      "name": "John Doe",
      "relationship": "son",
      "color": "blue",
      "encoding": [0.1, 0.2, ...]  // 128-dimensional vector
    }
  ]
}
```

### Test the Service

```bash
python test_service.py
```

## Integration with MCP Server

This Python service is designed to work with the Node.js MCP server:

1. **MCP Server** receives face recognition requests
2. **MCP Server** calls this Python service via HTTP
3. **Python Service** processes the image and returns results
4. **MCP Server** returns results to the client

## Response Format

### Face Detection Response
```json
{
  "success": true,
  "faces": [
    {
      "face_id": "face_0",
      "encoding": [0.1, 0.2, ...],  // 128-dimensional vector
      "location": {
        "top": 100,
        "right": 200,
        "bottom": 300,
        "left": 50
      },
      "confidence": 0.95,
      "name": "Unknown",
      "relationship": "Unknown",
      "color": "gray"
    }
  ],
  "message": "Detected 1 faces"
}
```

### Face Recognition Response
```json
{
  "success": true,
  "person": "John Doe",
  "relationship": "son",
  "confidence": 0.95,
  "color": "blue",
  "message": "Recognized John Doe (son)"
}
```

## Performance

- **Face Detection**: ~100-500ms per image
- **Face Recognition**: ~200-800ms per image
- **Memory Usage**: ~200-500MB (includes ML models)
- **Accuracy**: 99.38% (face_recognition library)

## Troubleshooting

### Common Issues

1. **Installation fails**: Make sure you have cmake installed
2. **Slow performance**: The first run loads ML models, subsequent runs are faster
3. **Memory issues**: The service loads ML models into memory (~200MB)

### Logs

The service logs all operations. Check the console output for debugging information.

## Development

### Adding New Features

1. Modify `face_service.py`
2. Update the API endpoints
3. Test with `test_service.py`
4. Update this README

### Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `face_recognition`: Face detection and recognition
- `Pillow`: Image processing
- `numpy`: Numerical operations
